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

from evennia import create_object
from evennia.utils.utils import delay

from typeclasses.characters import Character
from typeclasses.items import Item
from typeclasses.llm_npc import LLMNpcMixin
from world.grammar import with_article

#: Species the block buys. Everything else is refused (see _refuse_species).
ACCEPTED_BUTCHER_SPECIES = frozenset({"rat"})

#: Decay factor (0.0 fresh → 1.0 a week gone) beyond which a carcass is
#: refused outright — past even her standards.
BUTCHER_DECAY_REFUSAL = 0.6

#: Register floor: below this the till can't cover a carcass and she stops
#: buying until it's fed (finite till — the economy hook).
BUTCHER_TILL_FLOOR = 5

#: The rat butchery table (spec §3.4): per-product value and flavour. Yields
#: are computed against the corpse's REAL condition in `_butcher_yields`.
RAT_PRODUCTS = {
    "rat tail": {
        "value": 5, "aliases": ["tail"],
        "desc": "A skinned rat tail, long as a forearm, coiled and tied off "
                "with butcher's twine. The classic stew base of the colony's "
                "cheaper kitchens.",
        "taste": "Gelatinous and faintly sweet, all cartilage and slow-cooked "
                 "promise — wasted eaten raw.",
    },
    "rat chops": {
        "value": 3, "aliases": ["chops", "chop"],
        "desc": "Center-cut rat chops, pale and lean, trimmed square on a "
                "bone. The good cut — the one the stall signs mean when they "
                "say MEAT in capitals.",
        "taste": "Lean and springy with a mineral edge; it wants a grill and "
                 "gets teeth instead.",
    },
    "rat haunch": {
        "value": 3, "aliases": ["haunch"],
        "desc": "A rat hindquarter, skinned and hock-tied — dense dark meat "
                "around a stout little femur. Roast weight for one.",
        "taste": "Dark, rich, and chewy, closer to game than anything the "
                 "ration lines admit exists.",
    },
    "rat offal": {
        "value": 3, "aliases": ["offal"],
        "desc": "A twist of waxed paper holding the sound organs — heart, "
                "liver, kidneys — glistening and neatly sorted. Delicacy or "
                "dare, depending on the kitchen.",
        "taste": "Iron and velvet; the liver coats the tongue and the heart "
                 "pushes back.",
    },
    "ground mystery meat": {
        "value": 1, "aliases": ["meat", "mystery meat"],
        "desc": "A dense brick of pale ground meat in a printed wrapper that "
                "says only MEAT. Whatever didn't make the cut, made this.",
        "taste": "Salt, fat, and deliberate ambiguity. It is probably best "
                 "not to chew thoughtfully.",
    },
}

#: Trunk organs whose average condition gates the chops yield — a
#: shotgun-shredded torso yields few or no center cuts.
_RAT_TRUNK_ORGANS = ("heart", "left_lung", "right_lung", "liver", "stomach",
                     "left_kidney", "right_kidney")

#: Organs that make the offal twist (need at least half sound).
_RAT_OFFAL_ORGANS = ("heart", "liver", "left_kidney", "right_kidney")


class ButcherBlock(Item):
    """The butcher's block — a fixed plate-steel counter holding the till.

    Sibling of ``BarCounter``: an ``Item`` (so @integrate folds it into the
    room description) but a fixture — ``get:false()`` keeps it planted. Cuts
    land in its ``contents`` (the counter surface); ``db.register`` is the
    finite till the payouts draw down (seed it; when it runs dry she stops
    buying — the economy hook)."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.register = 0
        self.db.owner = None
        self.db.integrate = True
        self.locks.add("get:false()")


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

    def _find_block(self):
        if not self.location:
            return None
        for obj in self.location.contents:
            if isinstance(obj, ButcherBlock):
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
        payout = sum(RAT_PRODUCTS[key]["value"] * count for key, count in yields)
        if block:
            payout = min(payout, till)
            block.db.register = till - payout

        surface = block if block else self.location
        for key, count in yields:
            spec = RAT_PRODUCTS[key]
            for _ in range(count):
                cut = create_object(Item, key=key, location=surface,
                                    home=surface, aliases=spec["aliases"])
                cut.db.desc = spec["desc"]
                cut.db.drink_taste = spec["taste"]
                cut.db.drink_effects = {}   # ingredient-grade slot (spec §7)
                cut.db.uses_left = 1
                cut.tags.add("eat", category="delivery_method")
                cut.tags.add("food", category="item_type")

        self._drop_from_hands(corpse)
        corpse.delete()
        if giver and giver.pk:
            giver.tokens = int(getattr(giver, "tokens", 0) or 0) + payout

        cuts_text = self._render_cuts(yields)
        pay_text = (f"counts {payout} across the steel"
                    if payout else "doesn't reach for the till")
        self.execute_cmd(
            f"emote breaks the carcass down with a few practiced strokes — "
            f"{cuts_text} onto the block — and {pay_text}."
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
            ("rat tail", tail), ("rat chops", chops), ("rat haunch", haunch),
            ("rat offal", offal), ("ground mystery meat", meat)) if count > 0]

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
        parts = [f"{count} {key}" if count > 1 else with_article(key)
                 for key, count in yields]
        if len(parts) > 1:
            return ", ".join(parts[:-1]) + ", and " + parts[-1]
        return parts[0] if parts else "nothing worth wrapping"
