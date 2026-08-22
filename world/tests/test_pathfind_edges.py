"""A walking route may not contain a jump (#2227).

`Exit.at_traverse` refuses normal traversal of an edge or a gap
outright — for players too — and hands you off to the `jump` command,
because what is on the other side is a storey of air. The A* graph
never learned: it counted every exit with a destination as a flat
one-step edge.

The cost was visible live. Ten souls stood on `Kaspar Urgent Care -
Rooftop (North)` — a third of the colony's ensouled population,
including the dispatch operator, so the emergency desk was unmanned —
each re-trying a parapet every three minutes on a route to a noodle
yard. The souls engine logged it correctly and forever:

    travel stalled toward Escallier Snailery - Yard
    (an exit that wouldn't give)

The route said "walk north". North was a parapet with
`edge_difficulty: 8` and a one-storey drop. The `flee` step in
`world/souls/jobs.py` already filtered these; the graph did not.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.spatial.pathfind import _neighbors, find_path, is_reachable


class _Exit:
    def __init__(self, key, dest, **flags):
        self.key = key
        self.destination = dest
        self.db = mock.MagicMock()
        self.db.is_edge = flags.get("is_edge")
        self.db.is_gap = flags.get("is_gap")

    def access(self, who, kind):
        return True


class _Room:
    def __init__(self, key):
        self.key = key
        self.exits = []


class TestEdgesAreNotWalkable(EvenniaCommandTest):
    def _roof_and_street(self):
        roof, street = _Room("Rooftop (North)"), _Room("Kaspar Street")
        return roof, street

    def test_an_edge_is_not_a_neighbour(self):
        roof, street = self._roof_and_street()
        roof.exits = [_Exit("north", street, is_edge=True)]
        self.assertEqual(list(_neighbors(roof, None)), [])

    def test_a_gap_is_not_a_neighbour(self):
        roof, street = self._roof_and_street()
        roof.exits = [_Exit("across", street, is_gap=True)]
        self.assertEqual(list(_neighbors(roof, None)), [])

    def test_an_ordinary_exit_still_is(self):
        roof, street = self._roof_and_street()
        stair = _Exit("down", street)
        roof.exits = [stair]
        self.assertEqual(list(_neighbors(roof, None)), [(street, stair)])

    def test_the_stairs_are_taken_over_the_parapet(self):
        """The actual shape of the trap: a roof with a tempting edge and
        a real way down. The route must be the real one."""
        roof, street = self._roof_and_street()
        inside = _Room("Rooftop")
        parapet = _Exit("north", street, is_edge=True)
        stair = _Exit("south", inside)
        roof.exits = [parapet, stair]
        inside.exits = [_Exit("down", street)]
        street.exits = []
        path = find_path(roof, street)
        self.assertIsNotNone(path)
        self.assertIn(inside, path)          # went the long way, on foot

    def test_a_roof_reachable_only_by_jumping_is_not_walkable(self):
        """Honest, not convenient: if the only way is a jump, there is
        no walking route, and a soul must not be sent to find one."""
        roof, street = self._roof_and_street()
        roof.exits = [_Exit("north", street, is_edge=True)]
        street.exits = [_Exit("up", roof, is_edge=True)]
        self.assertFalse(is_reachable(street, roof))

    def test_the_edge_still_exists_for_jumping(self):
        """Pathfinding ignores it; the world does not. The parapet is
        still there and `jump` still uses it."""
        roof, street = self._roof_and_street()
        parapet = _Exit("north", street, is_edge=True)
        roof.exits = [parapet]
        self.assertIs(roof.exits[0], parapet)
        self.assertTrue(parapet.db.is_edge)
