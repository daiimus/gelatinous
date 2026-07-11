"""Breach — sabotage and repair of breachable infrastructure (§2.4,
narrow cut 2026-07-11: masts only; door-forcing is a different fantasy).

A mast is a physical single point of failure the range layer already
respects (``db.intact``): wreck the Constabulary mast and dispatch goes
deaf AND quiet colony-wide — including to the report of the wrecking
itself (reciprocity is the heist); wreck the Queen of Cups mast and the
house band collapses to walkie range. This module adds the missing
verbs, riding machinery that already exists:

* **Channeled** (world/channeled.py): sabotage and repair occupy the
  actor for real minutes with a visible tell — anyone who walks in on
  the act sees it, and the world's contact seams break it.
* **Witnessed** (world/director/crime.py): completing a sabotage is a
  crime committed at that spot — the crowd-gated witness, the BOLO, and
  the dispatch response all ride the existing pipeline. The radio
  silence AFTERWARD is earned; the sight-line risk DURING is real.
* **Binary state**: ``db.intact`` flips; every consumer (range, relay,
  console carrier, integrate lines) reacts on its own. Repair is the
  counter-play — the same stillness, longer.

Builders: mark a structure ``db.breachable = True`` (both masts carry
it). Original desc/sensory prose is stashed on the object at wreck time
and restored at repair, so bespoke authored masts survive the round trip.
"""

from evennia import Command

from world.identity_utils import msg_room_identity

#: Cutting guys and tearing a feedline takes a sustained window —
#: exposure is the cost of the crime.
SABOTAGE_SECONDS = 90.0
#: Re-truing a mast takes longer than dropping it.
REPAIR_SECONDS = 180.0

WRECKED_DESC = (
    "The mast is down: guy lines cut, the structure listing hard "
    "against the few wires still holding, its feedline torn loose and "
    "bleeding braid. Whatever this steel used to carry, it carries "
    "nothing now."
)

WRECKED_SENSORY = {
    "visual": ("A wrecked |cantenna mast|n lists against its cut guy "
               "lines, feedline torn loose. The air where its carrier "
               "hum used to sit is just air."),
}


def _is_breachable(obj):
    return getattr(getattr(obj, "db", None), "breachable", None) is True


def find_breachable(caller, name):
    """A breachable structure in the caller's room matching *name*, or
    None — room objects only (you sabotage what you're standing at)."""
    if not name:
        return None
    location = getattr(caller, "location", None)
    try:
        contents = list(getattr(location, "contents", None) or [])
    except Exception:  # noqa: BLE001
        return None
    needle = name.strip().lower()
    for obj in contents:
        if not _is_breachable(obj):
            continue
        names = [getattr(obj, "key", "") or ""]
        try:
            names += list(obj.aliases.all())
        except Exception:  # noqa: BLE001
            pass
        if any(needle in str(n).lower() for n in names):
            return obj
    return None


def wreck_structure(structure):
    """Flip to wrecked: stash the authored prose, install the wreck."""
    db = structure.db
    db.intact_desc = db.desc
    db.intact_sensory = db.sensory_contributions
    db.desc = WRECKED_DESC
    db.sensory_contributions = dict(WRECKED_SENSORY)
    db.intact = False


def mend_structure(structure):
    """Flip to intact: restore the stashed prose (fail-soft if absent)."""
    db = structure.db
    if db.intact_desc:
        db.desc = db.intact_desc
        db.intact_desc = None
    if db.intact_sensory:
        db.sensory_contributions = db.intact_sensory
        db.intact_sensory = None
    db.intact = True


class CmdSabotage(Command):
    """
    Bring down breachable infrastructure.

    Usage:
      sabotage <structure>

    Work at a structure — cutting guy lines, tearing a feedline — for a
    sustained, very visible window. Anyone can walk in on you; damage,
    grapples, or combat break the act and nothing lands. Completing it
    is a crime, committed in full view of wherever you're standing.

    What a wrecked mast stops carrying is the point.
    """

    key = "sabotage"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        target = find_breachable(caller, self.args)
        if target is None:
            caller.msg("Sabotage what? Nothing here answers to that.")
            return
        if getattr(target.db, "intact", None) is not True:
            caller.msg(f"The {target.key} is already down.")
            return
        from world.channeled import begin_channel

        def _complete():
            wreck_structure(target)
            caller.msg(f"The last guy line parts and the {target.key} "
                       "comes down with a groan of steel. Whatever it "
                       "carried dies with it.")
            msg_room_identity(
                location=caller.location,
                template="{actor} cuts the last line — the "
                         f"{target.key} comes down with a groan of steel.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
            # the act of commission: a witness, a BOLO, a response —
            # if a report can still reach anyone with ears
            try:
                from world.director.crime import report_crime
                report_crime("sabotage", caller.location, perp=caller)
            except Exception:  # noqa: BLE001 — the wreck stands regardless
                pass

        def _interrupted(fraction):
            caller.msg(f"You break off — the {target.key} holds, "
                       "scarred but standing.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} backs away from the {target.key}, "
                         "leaving it scarred but standing.",
                char_refs={"actor": caller},
                exclude=[caller],
            )

        started = begin_channel(
            caller, SABOTAGE_SECONDS,
            tell=f"working at the {target.key}, cutting into its fittings",
            on_complete=_complete, on_interrupt=_interrupted,
            key="sabotaging")
        if started:
            caller.msg(f"You set into the {target.key}'s fittings — "
                       "this will take a while, and anyone can see it.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} sets into the {target.key}'s "
                         "fittings with intent.",
                char_refs={"actor": caller},
                exclude=[caller],
            )


def try_repair_structure(caller, args):
    """The structure branch of the shared ``repair`` verb (CmdArmor owns
    the key; armor stays untouched when nothing breachable matches).
    Returns True when this path handled the command."""
    target = find_breachable(caller, args)
    if target is None:
        return False
    if getattr(target.db, "intact", None) is True:
        caller.msg(f"The {target.key} is standing and sound.")
        return True
    from world.channeled import begin_channel

    def _complete():
        mend_structure(target)
        caller.msg(f"You true the {target.key} back against fresh guy "
                   "lines and re-seat the feedline. It hums.")
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} hauls the {target.key} true against "
                     "fresh lines. Its hum comes back.",
            char_refs={"actor": caller},
            exclude=[caller],
        )

    def _interrupted(fraction):
        caller.msg(f"You break off — the {target.key} is still down.")
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} steps back from the wrecked "
                     f"{target.key}, the job unfinished.",
            char_refs={"actor": caller},
            exclude=[caller],
        )

    started = begin_channel(
        caller, REPAIR_SECONDS,
        tell=f"rigging the {target.key} back upright",
        on_complete=_complete, on_interrupt=_interrupted,
        key="repairing")
    if started:
        caller.msg(f"You start rigging the {target.key} back upright — "
                   "slow, honest work.")
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} starts rigging the wrecked "
                     f"{target.key} back upright.",
            char_refs={"actor": caller},
            exclude=[caller],
        )
    return True
