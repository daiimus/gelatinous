"""Butchery — breaking a carcass down (GIG_PROTOTYPE_BUTCHER_SPEC).

The deterministic core of the butcher gig, moved off the `Butcher`
typeclass so the JOB owns it and whoever stands the block can do it
(#2378). A real payout never rides a model tool-roll; the LLM provides
voice and memory ON TOP of this transaction, never inside it.

Reached through the service registry's `on_receive` hook: handing a
corpse to whoever is working the block starts the buy. That hook exists
because receiving something is the one venue act that happens to a
PERSON rather than at a counter — you put the carcass in their hands.
"""

import re

from evennia.prototypes.spawner import spawn
from evennia.utils.utils import delay

from typeclasses.characters import Character
from world.grammar import with_article


#: Species the block buys. Everything else is refused (see _refuse_species).
#:
#: THE definition. This block was pasted five times down this module,
#: growing on each paste, while `typeclasses/butcher.py` carried a sixth
#: copy that nothing there even used. Python keeps the LAST definition,
#: so the earlier copies were dead text that would have misled the next
#: edit -- and a tuning change made in the typeclass would have moved the
#: tests and nothing in the game, or the reverse (#2632).
ACCEPTED_BUTCHER_SPECIES = frozenset({"rat"})

#: Decay factor (0.0 fresh -> 1.0 a week gone) beyond which a carcass is
#: refused outright -- past even her standards.
BUTCHER_DECAY_REFUSAL = 0.6

#: Register floor: below this the till can't cover a carcass and she stops
#: buying until it's fed (finite till -- the economy hook).
BUTCHER_TILL_FLOOR = 5

#: The rat butchery BUY values (spec 3.4): what the block pays a supplier
#: per unit yielded. The SELL side is cooked -- dish prices live in
#: ``world.food.FOOD_RECIPES``; raw-cut prose/tags on the prototypes.
RAT_PRODUCTS = {
    "rat_tail":            {"name": "rat tail", "buy": 5},
    "rat_chops":           {"name": "rat chops", "buy": 3},
    "rat_haunch":          {"name": "rat haunch", "buy": 3},
    "rat_offal":           {"name": "rat offal", "buy": 3},
    "ground_mystery_meat": {"name": "ground mystery meat", "buy": 1},
}

#: Trunk organs whose average condition gates the chops yield -- a
#: shotgun-shredded torso yields few or no center cuts.
_RAT_TRUNK_ORGANS = ("heart", "left_lung", "right_lung", "liver", "stomach",
                     "left_kidney", "right_kidney")

#: Organs that make the offal twist (need at least half sound).
_RAT_OFFAL_ORGANS = ("heart", "liver", "left_kidney", "right_kidney")


def on_receive(post, obj, giver, by):
    """A corpse handed to the keeper starts the deterministic buy —
    after a beat, so the hand-over renders before the cleaver does."""
    from typeclasses.corpse import Corpse
    if not isinstance(obj, Corpse):
        return False
    who = giver if isinstance(giver, Character) else None
    delay(1.5, process_corpse, post, by, obj, who)
    return True


# --- the deterministic core ------------------------------------------
def process_corpse(post, by, corpse, giver):
    """Break a carcass down: species guard → freshness → till → yields →
    produce → pay → destroy. All code; the model never decides a payout."""
    if not by.location or not corpse or not corpse.pk:
        return
    species = (corpse.db.species or "human").lower()
    if species not in ACCEPTED_BUTCHER_SPECIES:
        _refuse(by, corpse, _refusal_line(species))
        return
    try:
        decay = float(corpse.get_decay_factor() or 0.0)
    except Exception:  # noqa: BLE001 — a corpse without decay data is fresh enough
        decay = 0.0
    if decay >= BUTCHER_DECAY_REFUSAL:
        _refuse(by, corpse, "That's past even my standards. Bury it.")
        return
    block = post
    till = int(block.db.register or 0) if block else 0
    if block and till < BUTCHER_TILL_FLOOR:
        _refuse(by, corpse, "Till's dry. Come back when it's been fed.")
        return

    yields = _butcher_yields(by, corpse, decay)
    payout = sum(RAT_PRODUCTS[key]["buy"] * count for key, count in yields)
    # Debit and credit must sit under the SAME condition. The register was
    # decremented whenever a block existed, while the payout was credited
    # only `if giver and giver.pk` — with `_drop_from_hands` and
    # `corpse.delete()` in between — so a giverless or mid-transaction
    # deleted giver left the money nowhere (#2814).
    if not (giver and giver.pk):
        payout = 0
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
                    cut.move_to(by.location, quiet=True, move_hooks=False)

    _drop_from_hands(by, corpse)
    corpse.delete()
    if giver and giver.pk:
        giver.tokens = int(getattr(giver, "tokens", 0) or 0) + payout

    cuts_text = _render_cuts(yields)
    pay_text = (f"counts {payout} across the steel"
                if payout else "doesn't reach for the till")
    by.execute_cmd(
        f"emote breaks the carcass down with a few practiced strokes — "
        f"{cuts_text} to the cook-pot — and {pay_text}."
    )

def _butcher_yields(by, corpse, decay):
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
def _refusal_line(species):
    if species in ("human", "synthetic_humanoid"):
        return "I don't grind people. Ripper trade's not mine — take it elsewhere."
    if species == "robot":
        return "That's chrome and coolant, not meat."
    return "I don't know what that is, and I don't grind what I can't name."

def _refuse(by, corpse, line):
    """Refuse a carcass: hand it back onto the floor (never destroyed)."""
    _drop_from_hands(by, corpse)
    if corpse and corpse.pk and by.location:
        corpse.move_to(by.location, quiet=True, move_hooks=False)
    by.execute_cmd(f"say {line}")

def _drop_from_hands(by, obj):
    """Clear ``obj`` from Mr. Hands (give places items IN hand) so no
    stale held-item entry survives the corpse's destruction."""
    try:
        hands = dict(by.hands or {})
        changed = {k: (None if v == obj else v) for k, v in hands.items()}
        if changed != hands:
            by.hands = changed
    except Exception:  # noqa: BLE001 — hand cleanup must never block the buy
        pass

def _render_cuts(yields):
    parts = []
    for key, count in yields:
        name = RAT_PRODUCTS.get(key, {}).get("name", key)
        parts.append(f"{count} {name}" if count > 1 else with_article(name))
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + ", and " + parts[-1]
    return parts[0] if parts else "nothing worth wrapping"


