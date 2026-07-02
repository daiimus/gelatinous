"""Witnesses — crowd-gated, spawned, and interdictable.

Crime slice 3 (``NPC_DISPATCH_AND_SIMULATION_SPEC`` §5.1): whether a crime
*has* a witness derives from the room's **crowd** level — no crowd, no
witness, **no report** (crime in an empty alley is free). When the roll
passes, the witness **materializes as a real NPC** at the scene, visibly
marked (edging away, hand on a walkie) — and the report only goes out if
they are still **alive and conscious** when the window closes. Silence
them first and the force never learns.

This replaces slice 2's bare timer with a *person*: the interdiction
window is now a target, not a clock. (The walkie is flavor until
``RADIO_COMMS_SPEC`` ships a real device — then it becomes snatchable.)

The witness is the game's first true **flash-temp ephemeral** (§3): it
exists for the report, lingers briefly, and despawns. Per §5.2 it carries
**100–500 tokens** — a bystander is also a mugging target, which is
exactly the kind of loop this world wants.
"""

from __future__ import annotations

from random import choice, randint, random
from typing import Any

from evennia import create_object
from evennia.utils import delay

from world.crowd import crowd_system
from world.identity import BUILDS, HEIGHTS

#: Seconds between the crime and the witness calling it in — the
#: interdiction window (silence them before it closes).
WITNESS_REPORT_DELAY = 40.0
#: Seconds after reporting before the witness slips away and despawns.
WITNESS_DESPAWN_DELAY = 90.0
#: §5.2: civilians carry pockets worth mugging, not farming.
WITNESS_TOKENS = (100, 500)

_WITNESS_ADJECTIVES = (
    "rattled", "shaken", "wide-eyed", "nervous", "pale",
    "stunned", "jumpy",
)

#: crowd level -> chance someone actually saw it. 0 = empty room = free.
def witness_chance(location: Any) -> float:
    try:
        level = crowd_system.calculate_crowd_level(location) or 0
    except Exception:  # noqa: BLE001 — no crowd model, no witness
        return 0.0
    if level <= 0:
        return 0.0
    return min(0.95, 0.30 + 0.25 * float(level))


def spawn_witness(location: Any) -> Any | None:
    """Roll the crowd gate; on success materialize the witness NPC at
    *location*, visibly marked. Returns the witness or ``None``."""
    if location is None or random() >= witness_chance(location):
        return None
    try:
        witness = create_object(
            typeclass="typeclasses.characters.Character",
            key=f"a {choice(_WITNESS_ADJECTIVES)} bystander",
            location=location,
            home=location,
        )
    except Exception:  # noqa: BLE001 — spawn failure = no witness, never a crash
        return None
    witness.height = choice(HEIGHTS)
    witness.build = choice(BUILDS)
    witness.db.tokens = randint(*WITNESS_TOKENS)          # §5.2 pockets
    witness.db.is_witness = True
    # The visible tell — this is who saw you, and what they're about to do.
    witness.look_place = ("edging away from the scene, one hand on a "
                          "battered walkie-talkie.")
    try:
        witness.execute_cmd(
            "emote flinches back from the scene, fumbling for a "
            "walkie-talkie.")
    except Exception:  # noqa: BLE001
        pass
    return witness


def can_report(witness: Any) -> bool:
    """Alive and conscious — the §5.1 interdiction check."""
    if witness is None or getattr(witness, "location", None) is None:
        return False
    try:
        if witness.is_dead() or witness.is_unconscious():
            return False
    except Exception:  # noqa: BLE001 — no medical model, assume able
        pass
    return True


def witness_report(witness: Any, event: Any) -> bool:
    """The window closes: if the witness can still report, the event goes
    to the dispatcher (magic radio until ``RADIO_COMMS_SPEC`` builds the
    transmission for real). Then the witness **flees the scene to cower**
    — real movement over the exit graph via the director's travel
    primitive, not a vanish — the proof-of-concept for the future where
    every NPC's comings and goings run on the dispatch system. Returns
    whether the report went out."""
    from world.director.dispatch import raise_event
    reported = False
    if can_report(witness):
        try:
            witness.execute_cmd(
                "emote raises the walkie-talkie and calls it in, voice "
                "shaking.")
        except Exception:  # noqa: BLE001
            pass
        try:
            raise_event(event)
            reported = True
        except Exception:  # noqa: BLE001 — a broken dispatch must not strand us
            pass
        flee_and_cower(witness)
    elif witness is not None:
        # Silenced (dead/unconscious) — cleanup only; the dead belong to
        # the corpse pipeline, the downed get hauled off eventually.
        delay(WITNESS_DESPAWN_DELAY, despawn_witness, witness)
    return reported


#: How far (straight-line rooms) the witness will run to find a corner.
COWER_RADIUS = 4


def flee_and_cower(witness: Any) -> None:
    """Walk the witness to a nearby room (director travel — visible,
    step-by-step, through real exits) and have it cower there; it slips
    away and despawns only after a long grace, off the scene instead of
    evaporating in front of everyone."""
    from world.director.travel import travel_to
    from world.spatial import rooms_within
    destination = None
    try:
        nearby = rooms_within(witness.location, COWER_RADIUS)
        if nearby:
            destination = choice(nearby)
    except Exception:  # noqa: BLE001 — no spatial data, cower in place
        pass
    try:
        witness.execute_cmd("emote bolts from the scene, head down.")
    except Exception:  # noqa: BLE001
        pass
    if destination is None or not travel_to(
            witness, destination, on_arrive=_cower, on_fail=_cower):
        _cower(witness)


def _cower(witness: Any) -> None:
    """Arrived (or cornered): hunker down, then despawn after the grace."""
    try:
        witness.look_place = ("cowering against the wall, arms wrapped "
                              "tight, eyes on the door.")
        witness.execute_cmd("emote presses into cover, shaking.")
    except Exception:  # noqa: BLE001
        pass
    delay(WITNESS_DESPAWN_DELAY, despawn_witness, witness)


def despawn_witness(witness: Any) -> None:
    """The flash-temp leaves: delete the witness unless the world has
    other plans for the body (dead witnesses belong to the death/corpse
    pipeline, not to us)."""
    try:
        if witness is None or not witness.pk:
            return  # already gone
        if witness.is_dead():
            return  # the corpse pipeline owns it now
        witness.execute_cmd("emote hurries off, wanting no more part of this.")
        witness.delete()
    except Exception:  # noqa: BLE001 — cleanup must never raise into delay
        pass
