"""``@coordseed`` — assign (x, y, z) coordinates to the world by walking
cardinal exits outward from the PINNED origin room.

Phase 1 of the spatial coordinate substrate
(``specs/proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md``). Authoritative:
geometry contradictions (a direction that doesn't reverse) are reported,
not silently resolved — fix the exit, tag it ``warp`` to exclude it, or
tag it ``slope_down``/``slope_up`` if it's honest split-level geometry.

The origin is PINNED (2026-07-12): seeding always anchors at the one
tagged origin room, never at wherever the builder happens to stand —
re-framing every coordinate in the colony by running the command from
the wrong bar was the grid's worst footgun.
"""

from evennia import default_cmds
from evennia.utils.search import search_tag

from world.spatial import (
    clear_xyz,
    seed_coordinates,
    set_xyz,
)
from world.spatial.coordinates import all_coordinate_rooms

#: The tag pinning the world's canonical (0, 0, 0) room.
ORIGIN_TAG = "coordseed_origin"
ORIGIN_TAG_CATEGORY = "spatial"


def pinned_origin():
    """The one pinned origin room, or None."""
    rooms = search_tag(ORIGIN_TAG, category=ORIGIN_TAG_CATEGORY)
    return rooms[0] if rooms else None


class CmdCoordSeed(default_cmds.MuxCommand):
    """
    Seed the world with (x, y, z) coordinates.

    Usage:
        @coordseed             - seed from the PINNED origin room (0,0,0)
        @coordseed/check       - dry run: report what would happen, write nothing
        @coordseed/origin      - pin YOUR CURRENT ROOM as the canonical origin
        @coordseed/clear       - remove coordinates from every room

    Walks cardinal exits (north/south/east/west, the diagonals, up/down)
    breadth-first from the pinned origin, assigning one coordinate unit
    per step (+X east, +Y north, +Z up). It does not matter where you
    stand — the origin is pinned so the frame can never shift. Non-
    cardinal exits (enter, climb, out) and ``warp``-tagged exits are
    skipped; ``slope_down``/``slope_up``-tagged exits apply their extra
    z-step (split-level geometry, e.g. sunken berths).

    Contradictions — a room reached two ways with different coordinates —
    are a geometry bug in the build (a "north" that doesn't come back
    "south"). They are listed for you to fix; coordinates are never
    averaged. Tags: ``@tag <exit> = warp:exit_type`` (non-Euclidean,
    excluded) or ``@tag <exit> = slope_down:exit_type`` (honest slope,
    derived).
    """

    key = "@coordseed"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        switches = self.switches or []

        if "clear" in switches:
            rooms = all_coordinate_rooms()
            for room in rooms:
                clear_xyz(room)
            caller.msg(f"Cleared coordinates from {len(rooms)} room(s).")
            return

        if "origin" in switches:
            here = caller.location
            if here is None:
                caller.msg("You have no location to pin.")
                return
            old = pinned_origin()
            if old is not None and old != here:
                old.tags.remove(ORIGIN_TAG, category=ORIGIN_TAG_CATEGORY)
            here.tags.add(ORIGIN_TAG, category=ORIGIN_TAG_CATEGORY)
            moved = (f" (moved from {old.get_display_name(caller)})"
                     if old is not None and old != here else "")
            caller.msg(f"|gOrigin pinned:|n {here.get_display_name(caller)} "
                       f"is now (0, 0, 0){moved}.")
            return

        origin = pinned_origin()
        if origin is None:
            caller.msg("|rNo origin is pinned.|n Stand in the world's "
                       "(0, 0, 0) room and run |w@coordseed/origin|n first "
                       "— seeding from an arbitrary room would re-frame "
                       "every coordinate in the colony.")
            return

        assignments, contradictions = seed_coordinates(origin)
        dry = "check" in switches

        if not dry:
            for room, coord in assignments.items():
                set_xyz(room, *coord)

        verb = "Would seed" if dry else "Seeded"
        caller.msg(
            f"|g{verb} {len(assignments)} room(s)|n from the pinned origin "
            f"{origin.get_display_name(caller)} (0, 0, 0)."
        )

        if contradictions:
            caller.msg(
                f"|r{len(contradictions)} geometry contradiction(s) "
                f"— each is a build bug to fix (or tag warp/slope):|n"
            )
            for c in contradictions[:40]:
                caller.msg(
                    f"  {c['from_room'].get_display_name(caller)} "
                    f"--{c['direction']}--> "
                    f"{c['dest'].get_display_name(caller)}: already at "
                    f"{c['existing']}, this path expects {c['expected']}."
                )
            if len(contradictions) > 40:
                caller.msg(f"  ... and {len(contradictions) - 40} more.")
        else:
            caller.msg("|gNo geometry contradictions — clean.|n")

        if dry:
            caller.msg("|y(dry run — nothing was written)|n")
