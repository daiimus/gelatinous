"""Patrols spread by identity, and the souled path is the one tested
(#2431).

Two things were wrong, and one of them was the test.

**The stagger was a dice roll on volatile state.** `patrol_idx` lives on
`ndb`, which dies on every reload, so a `randrange` re-randomised the
whole population at each restart — and gave each unit one out-of-sequence
hop as it jumped to a fresh index. `SOULS_SCALE_HARDENING_SPEC` §5 law 4
is explicit: *"Stagger by identity. Anything keyed `beat % N` across a
population is a thundering herd; add the entity id to the phase."* A
`randrange` never satisfied that law even while it was working.

**The builder command pinned everyone to 0.** `CmdPatrol` wrote
`ndb.patrol_idx = 0` when assigning a beat, so every unit given a beat in
one builder session started on the same stop, whatever the roll would
have said.

**And the existing test drove the dead door.** `test_director_civilians`
builds a `SimpleNamespace` with no `tags` attribute, so `_is_souled`
returns False and `tick_npc` walks the UNSOULED director path. Every NPC
is a soul now (`NPC_PLATFORM_SPEC` §5 criteria 3 and 9), so `tick_npc`
returns "souls" for a real body and never reaches the code that test
exercises. It passed while the live path was untested.

The parts of #2431 about `next_waypoint` returning an unstored index, and
`advance_waypoint` collapsing unset to 0, were already fixed by #2804 —
verified before writing any of this, rather than taken from the report.
"""
from types import SimpleNamespace
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.director import routines as rmod


def _beat(n):
    return [SimpleNamespace(key=f"r{i}") for i in range(n)]


class TestTheStaggerComesFromIdentity(EvenniaTest):
    def _body(self, ident, beat):
        return SimpleNamespace(id=ident, ndb=SimpleNamespace(),
                               db=SimpleNamespace(patrol_beat=beat))

    def test_two_bodies_on_one_beat_start_apart(self):
        beat = _beat(6)
        with mock.patch.object(rmod, "get_beat", return_value=beat):
            a = self._body(11, beat)
            b = self._body(12, beat)
            _wa, ia = rmod.next_waypoint(a)
            _wb, ib = rmod.next_waypoint(b)
        self.assertNotEqual(ia, ib)

    def test_a_population_spreads_across_the_whole_loop(self):
        beat = _beat(6)
        seen = set()
        with mock.patch.object(rmod, "get_beat", return_value=beat):
            for ident in range(100, 118):
                seen.add(rmod.next_waypoint(self._body(ident, beat))[1])
        self.assertEqual(seen, set(range(6)))

    def test_the_same_body_resumes_the_same_phase(self):
        """`ndb` dies on reload. Derived from the id, the unit comes back
        where it was instead of jumping."""
        beat = _beat(6)
        with mock.patch.object(rmod, "get_beat", return_value=beat):
            before = rmod.next_waypoint(self._body(31, beat))[1]
            after = rmod.next_waypoint(self._body(31, beat))[1]  # post-reload
        self.assertEqual(before, after)

    def test_an_existing_index_is_left_alone(self):
        beat = _beat(6)
        body = self._body(11, beat)
        body.ndb.patrol_idx = 4
        with mock.patch.object(rmod, "get_beat", return_value=beat):
            self.assertEqual(rmod.next_waypoint(body)[1], 4)

    def test_a_body_with_no_id_still_gets_a_phase(self):
        """A test double or an object mid-creation must not collapse the
        whole population onto stop 0."""
        beat = _beat(6)
        seen = set()
        with mock.patch.object(rmod, "get_beat", return_value=beat):
            for _ in range(24):
                body = SimpleNamespace(ndb=SimpleNamespace(),
                                       db=SimpleNamespace(patrol_beat=beat))
                seen.add(rmod.next_waypoint(body)[1])
        self.assertGreater(len(seen), 2)

    def test_an_empty_beat_is_not_a_patrol(self):
        with mock.patch.object(rmod, "get_beat", return_value=[]):
            self.assertEqual(rmod.next_waypoint(self._body(1, [])),
                             (None, None))


class TestTheIndexStillAdvances(EvenniaTest):
    def test_it_walks_the_loop_in_order(self):
        beat = _beat(4)
        body = SimpleNamespace(id=8, ndb=SimpleNamespace(),
                               db=SimpleNamespace(patrol_beat=beat))
        with mock.patch.object(rmod, "get_beat", return_value=beat):
            start = rmod.next_waypoint(body)[1]
            rmod.advance_waypoint(body)
            self.assertEqual(body.ndb.patrol_idx, (start + 1) % 4)

    def test_it_wraps(self):
        beat = _beat(4)
        body = SimpleNamespace(id=3, ndb=SimpleNamespace(),
                               db=SimpleNamespace(patrol_beat=beat))
        body.ndb.patrol_idx = 3
        with mock.patch.object(rmod, "get_beat", return_value=beat):
            rmod.advance_waypoint(body)
        self.assertEqual(body.ndb.patrol_idx, 0)


class TestTheBuilderCommandDoesNotPinTheIndex(EvenniaTest):
    """Assigning a beat must not put every unit on the same stop."""

    def test_assigning_a_beat_leaves_the_phase_underived(self):
        import inspect
        from commands import CmdPatrol
        src = inspect.getsource(CmdPatrol)
        self.assertNotIn("ndb.patrol_idx = 0", src)


class TestTheSouledPathIsTheOneThatRuns(EvenniaTest):
    """`tick_npc` hands a souled body straight to the souls engine, so a
    test double with no `tags` exercises code no live NPC reaches."""

    def test_a_souled_body_is_not_walked_by_the_director(self):
        # It needs a BEAT: `tick_npc` returns "none" for a body with no
        # patrol before it ever asks whether the body is souled.
        body = self.char1
        beat = _beat(3)
        with mock.patch.object(rmod, "get_beat", return_value=beat), \
             mock.patch.object(rmod, "_is_souled", return_value=True):
            self.assertEqual(rmod.tick_npc(body), "souls")

    def test_a_namespace_without_tags_is_not_souled(self):
        """Which is exactly why the old test walked the dead door."""
        self.assertFalse(rmod._is_souled(SimpleNamespace()))
