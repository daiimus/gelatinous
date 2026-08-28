"""The Butcher — the first gig NPC (GIG_PROTOTYPE_BUTCHER_SPEC).

The prototype fetch-quest loop: a player hands over an ANIMAL corpse (``give
corpse to butcher``), and the Butcher deterministically breaks it down via a
per-species butchery table — named cuts gated by each part's real condition on
the corpse, the remainder ground to mystery meat — destroys the carcass, and
pays the supplier by yield value. The LLM brain (``LLMNpcMixin``) provides
voice and memory ON TOP of the transaction, never inside it: a real payout
never rides a model tool-roll (LLM_GAMEMASTER_SPEC tool-reliability note).

Human / synthetic / robot corpses are REFUSED — sapient bodies are the future
Ripper's trade, and chrome isn't food.
"""

from evennia.prototypes.spawner import spawn
from evennia.utils.utils import delay

from typeclasses.characters import Character
from typeclasses.llm_npc import LLMNpcMixin
from typeclasses.furniture import Seating
from typeclasses.shopkeeper import ShopContainer
from world.grammar import with_article

#: Species the block buys. Everything else is refused (see _refuse_species).
ACCEPTED_BUTCHER_SPECIES = frozenset({"rat"})

#: Decay factor (0.0 fresh → 1.0 a week gone) beyond which a carcass is
#: refused outright — past even her standards.
BUTCHER_DECAY_REFUSAL = 0.6

#: Register floor: below this the till can't cover a carcass and she stops
#: buying until it's fed (finite till — the economy hook).
BUTCHER_TILL_FLOOR = 5

#: The rat butchery BUY values (spec §3.4): what the block pays a supplier
#: per unit yielded. The SELL side is cooked — dish prices live in
#: ``world.food.FOOD_RECIPES``; raw-cut prose/tags on the prototypes.
RAT_PRODUCTS = {
    "rat_tail":            {"name": "rat tail", "buy": 5},
    "rat_chops":           {"name": "rat chops", "buy": 3},
    "rat_haunch":          {"name": "rat haunch", "buy": 3},
    "rat_offal":           {"name": "rat offal", "buy": 3},
    "ground_mystery_meat": {"name": "ground mystery meat", "buy": 1},
}

#: Trunk organs whose average condition gates the chops yield — a
#: shotgun-shredded torso yields few or no center cuts.
_RAT_TRUNK_ORGANS = ("heart", "left_lung", "right_lung", "liver", "stomach",
                     "left_kidney", "right_kidney")

#: Organs that make the offal twist (need at least half sound).
_RAT_OFFAL_ORGANS = ("heart", "liver", "left_kidney", "right_kidney")


class FoodCart(Seating, ShopContainer):
    """The butcher's food cart — a parked scrap-built cart that is her SHOP,
    and its own SEATING (the BarCounter pattern: the plastic stools are part
    of the cart, so ``sit at cart`` takes one of its slots).

    A ``ShopContainer`` in **limited-inventory** mode selling COOKED DISHES:
    the grind's cuts run through ``world.food`` recipes (``stock_cuts`` cooks
    them 1:1) and the menu is stew, chops, and skewers — never spawned from
    thin air, so the gig economy stays real. ``buy stew from cart`` works
    like any shop, and the override below credits sale proceeds to
    ``db.register``, closing the till loop: payouts to hunters drain the
    till, dish sales refill it.

    A FIXTURE with wheels only in the fiction (``get:false``; the desc shows
    them chocked) — if roaming vendors ever become a mechanic, the cart is
    already the right object for it. ``db.integrate`` folds it into the room
    via the short ``db.integration_desc`` line (the full desc stays on
    ``look cart`` — the jukebox lesson)."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_infinite = False
        self.db.shop_name = "the food cart"
        self.db.container_type = "cart"
        self.db.register = 0
        self.db.owner = None
        self.db.integrate = True
        self.db.integration_priority = 8
        self.db.purchase_msg_buyer = ("You count out {price}, and the butcher "
                                      "sets {item} on the board.")
        self.db.purchase_msg_room = ("{buyer} counts chits onto the cart, and "
                                     "the butcher sets {item} on the board.")
        # Seating: the stools ARE the cart (BarCounter pattern) — `sit at
        # cart` takes one of these slots.
        self.db.postures = ("sitting",)
        self.db.capacity = 4
        self.db.preposition = "at"

    def stock_cuts(self, counts):
        """COOK the ground produce and stock the DISHES: raw ingredient counts
        (``{catalog_id: count}``) run through ``world.food.cook_yields`` — the
        cuts are consumed as recipe ingredients, and what the shop sells is the
        cooked menu (rat tail stew, grilled chops…) at recipe prices. The raw
        cuts stay real in ``FOOD_INGREDIENT_CATALOG`` for the future grocery /
        player-kitchen layer; today the butcher IS the whole chain."""
        from world.food import FOOD_RECIPES, cook_yields
        dishes = cook_yields(counts)
        inventory = dict(self.db.prototype_inventory or {})
        stock = dict(self.db.item_inventory or {})
        for recipe_id, count in dishes.items():
            recipe = FOOD_RECIPES.get(recipe_id)
            if not recipe or count <= 0:
                continue
            proto_key = recipe["prototype"]
            inventory[proto_key] = recipe["price"]
            stock[proto_key] = int(stock.get(proto_key, 0)) + int(count)
        self.db.prototype_inventory = inventory
        self.db.item_inventory = stock
        self.db.is_infinite = False

    def purchase_item(self, buyer, prototype_key):
        """The dish lands ON THE BOARD — the bar's physicality: the base
        class hands the item to the buyer (and credits the till, since the
        base credits any register now); we re-place it on the cart instead
        (``get <dish> from cart``), clearing any hand slot the base put it
        in so no ghost grip survives."""
        success, result = super().purchase_item(buyer, prototype_key)
        if success:
            try:
                result.move_to(self, quiet=True, move_hooks=False)
                hands = dict(getattr(buyer, "hands", None) or {})
                changed = {k: (None if v == result else v)
                           for k, v in hands.items()}
                if changed != hands:
                    buyer.hands = changed
            except Exception:  # noqa: BLE001 — a failed re-place leaves it with the buyer
                pass
        return success, result

    def return_appearance(self, looker, **kwargs):
        """The menu board, plus whatever's physically resting on it — served
        dishes sit on the cart until their buyer takes them."""
        appearance = super().return_appearance(looker, **kwargs)
        resting = [obj for obj in self.contents if not obj.destination]
        if resting:
            from world.grammar import with_article
            names = ", ".join(with_article(o.key) for o in resting)
            appearance += f"\nResting on the board: {names}."
        return appearance


class Butcher(LLMNpcMixin, Character):
    """An LLM-voiced butcher whose buy-and-break-down transaction is pure code."""

    def at_object_creation(self):
        super().at_object_creation()
        if not self.height:
            self.height = "average"
        if not self.build:
            self.build = "average"
        self.db.llm_driven = False
        self.db.is_butcher_npc = True   # loop-guard marker (cf. is_bartender_npc)

    def _name_aliases(self):
        return ["butcher", "meatcutter", "grinder"]

    # --- deterministic dish orders (the bartender pattern, #1235) --------
    # The intercept and the gratitude nod moved off this class (#2350) —
    # they are the shape of the job, and the job lives on the post. The
    # cart's own serve is `world/shop/service.serve_from_board_cart`.

    def _match_dish_order(self, speech):
        """Resolve spoken words to a dish the CART actually sells, using the
        recipe system's keywords (world.food.FOOD_RECIPES) — conservative:
        a clear order cue ("gimme/can i get/let me get…") OR a bare order
        ("a skewer."); a question without a cue ("is the stew any good?")
        is conversation, not an order. Returns the dish prototype key."""
        import re
        from world.bar import ORDER_CUES, ORDER_FILLER
        from world.food import FOOD_RECIPES
        low = " ".join((speech or "").lower().split())
        if not low:
            return None
        words = re.findall(r"[a-z']+", low)
        matched = None
        matched_words = set()
        for recipe_id, recipe in FOOD_RECIPES.items():
            kws = set()
            for kw in recipe.get("keywords") or ():
                kws.update(kw.lower().split())
            kws.update(recipe["name"].lower().split())
            if any(w in kws for w in words):
                matched = recipe["prototype"]
                matched_words = kws
                break
        if not matched:
            return None
        has_cue = any(cue in low for cue in ORDER_CUES)
        if "?" in low:
            # a question is only an order when it carries a request cue
            # ("can i get a skewer?"); "you got skewers?" is conversation
            return matched if has_cue else None
        if has_cue:
            return matched
        remainder = [w for w in words
                     if w not in matched_words and w not in ORDER_FILLER]
        return matched if not remainder else None

    def _fulfil_dish_order(self, order_text, patron):
        """Serve immediately, no delay — the named entry point for a
        butcher asked directly. Stock, tokens and the till all ride the
        cart's own purchase path; non-orders fall through to talk."""
        from world.shop.service import _fulfil_from_shelf
        cart = self._find_block()
        proto = self._match_dish_order(order_text)
        if not proto or cart is None:
            if not self._try_llm_reply(order_text, patron, "directed",
                                       on_fail=self._llm_fallback):
                self.execute_cmd("say Board's behind me. It says what I sell.")
            return False
        _fulfil_from_shelf(cart, proto, patron, self, style="board")
        return True

    def _llm_fallback(self):
        """Sidecar down on an addressed non-order: the curt scripted line."""
        self.execute_cmd("say Board's behind me. It says what I sell.")

    def _find_block(self):
        """The cart she works from (name kept for the give-flow history)."""
        if not self.location:
            return None
        for obj in self.location.contents:
            if isinstance(obj, FoodCart):
                return obj
        return None

    # --- the hand-over: give corpse to butcher ---------------------------
    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """A corpse handed over starts the deterministic buy — after a beat,
        so the hand-over renders before the cleaver does."""
        super().at_object_receive(moved_obj, source_location, **kwargs)
        from typeclasses.corpse import Corpse
        if isinstance(moved_obj, Corpse):
            giver = source_location if isinstance(source_location, Character) else None
            delay(1.5, self._process_corpse, moved_obj, giver)

    # --- the deterministic core ------------------------------------------
    def _process_corpse(self, corpse, giver):
        """Break a carcass down: species guard → freshness → till → yields →
        produce → pay → destroy. All code; the model never decides a payout."""
        if not self.location or not corpse or not corpse.pk:
            return
        species = (corpse.db.species or "human").lower()
        if species not in ACCEPTED_BUTCHER_SPECIES:
            self._refuse(corpse, self._refusal_line(species))
            return
        try:
            decay = float(corpse.get_decay_factor() or 0.0)
        except Exception:  # noqa: BLE001 — a corpse without decay data is fresh enough
            decay = 0.0
        if decay >= BUTCHER_DECAY_REFUSAL:
            self._refuse(corpse, "That's past even my standards. Bury it.")
            return
        block = self._find_block()
        till = int(block.db.register or 0) if block else 0
        if block and till < BUTCHER_TILL_FLOOR:
            self._refuse(corpse, "Till's dry. Come back when it's been fed.")
            return

        yields = self._butcher_yields(corpse, decay)
        payout = sum(RAT_PRODUCTS[key]["buy"] * count for key, count in yields)
        if block:
            payout = min(payout, till)
            block.db.register = till - payout
            # the produce becomes SHOP STOCK — buyable, finite, real
            block.stock_cuts(dict(yields))
        else:
            # blockless butcher: spawn the cuts loose where she stands
            for key, count in yields:
                for _ in range(count):
                    for cut in spawn(key):
                        cut.move_to(self.location, quiet=True, move_hooks=False)

        self._drop_from_hands(corpse)
        corpse.delete()
        if giver and giver.pk:
            giver.tokens = int(getattr(giver, "tokens", 0) or 0) + payout

        cuts_text = self._render_cuts(yields)
        pay_text = (f"counts {payout} across the steel"
                    if payout else "doesn't reach for the till")
        self.execute_cmd(
            f"emote breaks the carcass down with a few practiced strokes — "
            f"{cuts_text} to the cook-pot — and {pay_text}."
        )

    def _butcher_yields(self, corpse, decay):
        """Walk the rat butchery table against the corpse's real condition.

        Each named cut is gated by its part: severed location or harvested
        organ = that cut is gone; trunk-organ damage scales the chops; decay
        scales the meat-mass cuts (chops + mystery meat). Returns a list of
        ``(product_key, count)`` with zero-count entries dropped."""
        snapshot = corpse.get_medical_snapshot() or {}
        organs = snapshot.get("organs") or {}
        severed = set(corpse.db.severed_locations or [])
        removed = set(corpse.db.removed_organs or [])
        freshness = 1.0 - decay

        def organ_ok(name):
            organ = organs.get(name)
            if not organ or name in removed:
                return False
            container = (organ.get("data") or {}).get("container")
            if container and container in severed:
                return False
            return (organ.get("current_hp") or 0) > 0

        def hp_frac(name):
            organ = organs.get(name) or {}
            max_hp = organ.get("max_hp") or 0
            if not max_hp:
                return 0.0
            return max(0.0, (organ.get("current_hp") or 0) / max_hp)

        tail = 1 if organ_ok("tail_vertebrae") else 0

        trunk = [n for n in _RAT_TRUNK_ORGANS
                 if n in organs and n not in removed
                 and (organs[n].get("data") or {}).get("container") not in severed]
        trunk_frac = (sum(hp_frac(n) for n in trunk) / len(trunk)) if trunk else 0.0
        chops = round(3 * trunk_frac * freshness)

        haunch = sum(1 for n in ("left_hindleg_bone", "right_hindleg_bone")
                     if organ_ok(n))

        offal_sound = sum(1 for n in _RAT_OFFAL_ORGANS if organ_ok(n))
        offal = 1 if offal_sound >= 2 else 0

        meat = max(1, round(3 * freshness))

        return [(key, count) for key, count in (
            ("rat_tail", tail), ("rat_chops", chops), ("rat_haunch", haunch),
            ("rat_offal", offal), ("ground_mystery_meat", meat)) if count > 0]

    # --- refusals + rendering helpers ------------------------------------
    @staticmethod
    def _refusal_line(species):
        if species in ("human", "synthetic_humanoid"):
            return "I don't grind people. Ripper trade's not mine — take it elsewhere."
        if species == "robot":
            return "That's chrome and coolant, not meat."
        return "I don't know what that is, and I don't grind what I can't name."

    def _refuse(self, corpse, line):
        """Refuse a carcass: hand it back onto the floor (never destroyed)."""
        self._drop_from_hands(corpse)
        if corpse and corpse.pk and self.location:
            corpse.move_to(self.location, quiet=True, move_hooks=False)
        self.execute_cmd(f"say {line}")

    def _drop_from_hands(self, obj):
        """Clear ``obj`` from Mr. Hands (give places items IN hand) so no
        stale held-item entry survives the corpse's destruction."""
        try:
            hands = dict(self.hands or {})
            changed = {k: (None if v == obj else v) for k, v in hands.items()}
            if changed != hands:
                self.hands = changed
        except Exception:  # noqa: BLE001 — hand cleanup must never block the buy
            pass

    @staticmethod
    def _render_cuts(yields):
        parts = []
        for key, count in yields:
            name = RAT_PRODUCTS.get(key, {}).get("name", key)
            parts.append(f"{count} {name}" if count > 1 else with_article(name))
        if len(parts) > 1:
            return ", ".join(parts[:-1]) + ", and " + parts[-1]
        return parts[0] if parts else "nothing worth wrapping"


#: Back-compat alias — live objects created before the cart redesign carry
#: ``typeclasses.butcher.ButcherBlock`` as their stored typeclass path.
ButcherBlock = FoodCart
