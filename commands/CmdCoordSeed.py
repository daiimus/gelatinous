"""``@coordseed`` — assign (x, y, z) coordinates to the world by walking
cardinal exits outward from a chosen origin room.

Phase 1 of the spatial coordinate substrate
(``specs/proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md``). Authoritative:
geometry contradictions (a direction that doesn't reverse) are reported,
not silently resolved — fix the exit, or tag it ``warp`` to exclude it.
"""

from evennia import default_cmds

from world.spatial import (
    clear_xyz,
    seed_coordinates,
    set_xyz,
)
from world.spatial.coordinates import all_coordinate_rooms


class CmdCoordSeed(default_cmds.MuxCommand):
    """
    Seed the world with (x, y, z) coordinates.

    Usage:
        @coordseed             - seed outward from this room as origin (0,0,0)
        @coordseed/check       - dry run: report what would happen, write nothing
        @coordseed/clear       - remove coordinates from every room

    Walks cardinal exits (north/south/east/west, the diagonals, up/down)
    breadth-first from your current room, assigning one coordinate unit per
    step (+X east, +Y north, +Z up). Non-cardinal exits (enter, climb, out)
    and ``warp``-tagged exits are skipped.

    Contradictions — a room reached two ways with different coordinates —
    are a geometry bug in the build (a "north" that doesn't come back
    "south"). They are listed for you to fix; coordinates are never
    averaged. Tag a deliberately non-Euclidean exit with
    ``@tag <exit> = warp:exit_type`` to exclude it.
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

        origin = caller.location
        if origin is None:
            caller.msg("You have no location to seed from.")
            return

        assignments, contradictions = seed_coordinates(origin)
        dry = "check" in switches

        if not dry:
            for room, coord in assignments.items():
                set_xyz(room, *coord)

        verb = "Would seed" if dry else "Seeded"
        caller.msg(
            f"|g{verb} {len(assignments)} room(s)|n from "
            f"{origin.get_display_name(caller)} as origin (0, 0, 0)."
        )

        if contradictions:
            caller.msg(
                f"|r{len(contradictions)} geometry contradiction(s) "
                f"— each is a build bug to fix (or tag warp):|n"
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
