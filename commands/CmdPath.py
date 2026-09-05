"""``@path`` — show the travel route from here to another room.

A builder/debug window onto the Phase 2 pathfinder
(``world/spatial/pathfind.py``): A* over the real exit graph with the
seeded coordinates as the heuristic.
"""

from evennia import Command

from world.spatial import distance, find_path, find_path_exits
from world.spatial.coordinates import exit_direction


def _traversable_by(traverser, origin, target) -> bool:
    """Can *traverser* actually walk the route, locks and all?

    `@path` shows the topological route. This is the second question —
    the one `travel_to` asks — so the two can be reported apart instead
    of the first being mistaken for the second.
    """
    try:
        from world.spatial import is_reachable
        return bool(is_reachable(origin, target, traverser=traverser))
    except Exception:  # noqa: BLE001 — a debug window never raises
        return True


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
        # SAY THAT THIS IGNORES LOCKS. `find_path_exits` takes a
        # `traverser` and this debug window does not pass one, which is
        # defensible for a builder tool — the topological route is what
        # you usually want to see. But it is the tool somebody reaches
        # for when an NPC will not walk somewhere, and three separate
        # bugs in this codebase were exactly a lock-blind route being
        # trusted over a lock-aware walk (#2711, #2714, #2758). An
        # unqualified route here sends the next person down the same
        # hour of debugging that #2321 records.
        if not _traversable_by(caller, origin, target):
            caller.msg(
                "  |y(Lock-blind: this is the topological route. YOU "
                "cannot walk it — a door on the way refuses you.)|n"
            )
        else:
            caller.msg("  (Lock-blind route; you can walk it as well.)")
        los = distance(origin, target)
        if los is not None:
            caller.msg(
                f"  (straight-line coordinate distance: {los:.1f}; "
                f"travel steps: {steps})"
            )
