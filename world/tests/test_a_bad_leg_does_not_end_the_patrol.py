"""A patrol survives a waypoint it can never reach (#2566).

Two ways to get an unreachable waypoint into a beat, and an index that
pins forever once one is hit.

`@patrol/auto` sampled `rooms_within` RAW, with neither filter its
sibling applies — the civilian haunt sampler excludes sky rooms (all
keyed "In the Air" by house convention) and anything with no walkable
route, and says in a comment why. `@patrol/beat` ran `caller.search(...,
global_search=True)` with no typeclass filter at all, so a CHARACTER
could be written into `db.patrol_beat`; the pathfinding graph holds only
rooms, so that leg can never resolve.

Either way the unit stopped patrolling permanently, because
`next_waypoint` pins the index BEFORE the walk and `advance_waypoint`
clears it only on ARRIVAL. `ndb.patrol_idx` is non-persistent, so a
reload cleared it — and it re-pinned on the next tick.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdPatrol import CmdPatrol
from world.director import routines
from world.director.routines import advance_waypoint, next_waypoint

#: Read off the module rather than imported by name: importing a
#: constant that does not exist yet makes this file fail to LOAD against
#: the unfixed tree, and a test that never runs is not a control. With a
#: default, the behavioural assertions below still fail there — which is
#: the claim.
PATROL_FAULT_LIMIT = getattr(routines, "PATROL_FAULT_LIMIT", 4)


class TestABadLegDoesNotEndThePatrol(EvenniaCommandTest):
    """The fault counter — the half that covers a waypoint going bad
    AFTER it was set: a door locked, an exit removed, a building gone."""

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.characters.Character",
                                 key="secbot", location=self.room1)
        self.npc.db.patrol_beat = [self.room1, self.room2]
        self.npc.db.post = self.room1

    def aim(self):
        return next_waypoint(self.npc)[1]

    def test_the_beat_yields_a_waypoint_at_all(self):
        """Control: no beat means no aim, and every assertion below
        would pass on an empty list."""
        self.assertIsNotNone(self.aim())

    def test_it_keeps_aiming_at_the_same_stop_while_it_might_arrive(self):
        """It must NOT give up on a stop that is merely slow, or a
        pre-empted plan would cost a waypoint every time."""
        first = self.aim()
        for _ in range(PATROL_FAULT_LIMIT - 1):
            self.assertEqual(self.aim(), first)

    def test_it_moves_on_after_the_limit(self):
        first = self.aim()
        for _ in range(PATROL_FAULT_LIMIT + 1):
            self.aim()
        self.assertNotEqual(
            self.aim(), first,
            "a waypoint that can never be reached pinned the beat "
            "forever")

    def test_arriving_clears_the_count(self):
        """The thing that makes a run of aims a run of FAILURES."""
        first = self.aim()
        for _ in range(PATROL_FAULT_LIMIT - 1):
            self.aim()
        advance_waypoint(self.npc)          # arrived
        self.npc.ndb.patrol_idx = first     # aim back at it
        for _ in range(PATROL_FAULT_LIMIT - 1):
            self.assertEqual(self.aim(), first,
                             "the count survived an arrival")


class TestAWaypointIsValidatedWhenItIsSet(EvenniaCommandTest):
    """The other half: stop the common cause at set time, so the
    builder learns then rather than never."""

    def setUp(self):
        super().setUp()
        self.char1.permissions.add("Developers")
        self.npc = create_object("typeclasses.characters.Character",
                                 key="secbot", location=self.room1)
        self.npc.db.post = self.room1
        self.exit = create_object("typeclasses.exits.Exit", key="east",
                                  location=self.room1,
                                  destination=self.room2)
        create_object("typeclasses.exits.Exit", key="west",
                      location=self.room2, destination=self.room1)

    def beat(self):
        return self.npc.db.patrol_beat

    def test_a_reachable_room_is_accepted(self):
        """Control: the command CAN set a beat, so a refusal below is
        the guard and not a broken fixture."""
        self.call(CmdPatrol(), f"/beat secbot = #{self.room2.id}")
        self.assertEqual([r.id for r in self.beat() or []], [self.room2.id])

    def test_a_character_is_refused(self):
        out = self.call(CmdPatrol(), "/beat secbot = Char2")
        self.assertFalse(self.beat())
        self.assertIn("isn't a room", out)

    def test_a_sky_room_is_refused(self):
        self.room2.db.is_sky_room = True
        out = self.call(CmdPatrol(), f"/beat secbot = #{self.room2.id}")
        self.assertFalse(self.beat())
        self.assertIn("open air", out)

    def test_an_unwalkable_room_is_refused(self):
        """An island with no exits at all. Deleting the OUTBOUND exit
        from the post is not enough — `EvenniaTest` wires room1 and
        room2 both ways, and the graph still finds the way back."""
        island = create_object("typeclasses.rooms.Room", key="Sealed Vault")
        out = self.call(CmdPatrol(), f"/beat secbot = #{island.id}")
        self.assertFalse(self.beat())
        self.assertIn("walkable", out)
