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


# `Butcher` is gone (#2378). An NPC is a `LLMNpc` whose
# capabilities come from the POST it stands and the SOUL it
# carries — the typeclass says what a body IS, never what it
# can do (NPC_PLATFORM_SPEC §3, law 5).

#: Back-compat alias — live objects created before the cart redesign carry
#: ``typeclasses.butcher.ButcherBlock`` as their stored typeclass path.
ButcherBlock = FoodCart
