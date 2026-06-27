"""``@path`` — show the travel route from here to another room.

A builder/debug window onto the Phase 2 pathfinder
(``world/spatial/pathfind.py``): A* over the real exit graph with the
seeded coordinates as the heuristic.
"""

from evennia import Command

from world.spatial import distance, find_path, find_path_exits
from world.spatial.coordinates import exit_direction


class CmdPath(Command):
    """
    Show the shortest travel route from your room to another.

    Usage:
        @path <room>          - route from here to <room> (name or #dbref)

    Walks the real exit graph (A* guided by seeded coordinates), so the
    route respects actual connectivity — locked doors, warp links, and
    non-cardinal exits all count. Reports the step-by-step directions, the
    travel-step count, and (when both rooms are on-grid) the straight-line
    coordinate distance for comparison.
    """

    key = "@path"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not self.args.strip():
            caller.msg("Usage: @path <room>")
            return

        origin = caller.location
        if origin is None:
            caller.msg("You have no location to route from.")
            return

        target = caller.search(self.args.strip(), global_search=True)
        if not target:
            return  # search already reported the failure

        path = find_path(origin, target)
        if path is None:
            caller.msg(
                f"No route from {origin.get_display_name(caller)} to "
                f"{target.get_display_name(caller)} over the exit graph."
            )
            return

        steps = len(path) - 1
        if steps == 0:
            caller.msg("You're already there.")
            return

        exits = find_path_exits(origin, target) or []
        directions = [exit_direction(ex) or ex.key for ex in exits]

        caller.msg(
            f"|gRoute to {target.get_display_name(caller)}|n — "
            f"{steps} step(s): {', '.join(directions)}."
        )
        los = distance(origin, target)
        if los is not None:
            caller.msg(
                f"  (straight-line coordinate distance: {los:.1f}; "
                f"travel steps: {steps})"
            )
