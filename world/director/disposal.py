"""What the precinct does with a wreck (#2255 §2).

    destroyed → remains taken to the constabulary
              → weapon arm module removed
              → disposed of in the junkyard

Owner, 2026-08-24: *"The shotgun arm module is what needs to be
removed."* The module, not the limb — a stripped chassis keeps its
arms and loses the gun that was seated in one.

The chassis PERSISTS in the yard rather than being deleted (owner
ruling): it is the obvious feedstock for the Ripper's cold room and
for parts, and it lets the junkyard accumulate a visible history of
the force's bad nights.
"""
from typing import Any

#: The armament to recover. A unit's weapon is an augment ORGAN seated
#: in an arm, not a carried item, which is exactly why an unrecovered
#: wreck is a working shotgun lying in the street.
ARMAMENT = "integrated_shotgun_module"

#: Where a stripped chassis goes. Tag-driven so a builder can move the
#: yard without editing code.
SCRAPYARD_TAG = ("scrapyard", "disposal")


def scrapyard():
    """The room stripped chassis are disposed of in, or None."""
    from evennia.utils.search import search_tag
    rooms = [r for r in search_tag(*SCRAPYARD_TAG) if r and r.pk]
    return rooms[0] if rooms else None


def strip_and_junk(actor: Any, wreck: Any) -> dict:
    """Take the armament off a destroyed unit and send it to the yard.

    Order matters and is not arbitrary: the module comes off FIRST and
    stays where the actor is. If the yard is missing or the move fails,
    the colony has still recovered its shotgun — which is the whole
    point of the errand. Junking is the tidy-up; disarming is the
    objective.

    Returns a small report so callers can log or narrate.
    """
    out = {"module": None, "junked": False}
    if wreck is None or not getattr(wreck, "pk", None):
        return out

    from world.medical.procedures import strip_organ
    try:
        out["module"] = strip_organ(
            wreck, ARMAMENT,
            into=getattr(actor, "location", None) or wreck.location)
    except Exception:  # noqa: BLE001 — a failed strip must not strand
        out["module"] = None                # the wreck mid-disposal

    yard = scrapyard()
    if yard is None or yard == wreck.location:
        return out
    try:
        wreck.move_to(yard, quiet=True, move_hooks=False)
        out["junked"] = True
    except Exception:  # noqa: BLE001 — the wreck stays put; still disarmed
        pass
    return out
