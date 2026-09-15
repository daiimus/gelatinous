"""A pinned soul is frozen in time (owner ruling 2026-09-14).

It keeps its soul -- persona, needs, memory, the tag -- but the
heartbeat leaves it alone: no need decay, no thinking, no planning, no
walking. `@unpin` restarts its clock from that moment, so the frozen
interval is never paid back as a lump of hunger.
"""
import time
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.souls import engine
from world.souls import needs as needs_mod


class PinnedSoulsAreFrozenInTimeTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc", key="Frozen", location=self.room1)
        self.npc.db.is_npc = True
        engine.ensoul(self.npc, role="resident", home=None, post=None)

    def _backdate(self, hours):
        stored = dict(self.npc.db.soul_needs or {})
        stored["_at"] = time.time() - hours * 3600
        self.npc.db.soul_needs = stored

    def test_pinned_needs_do_not_decay(self):
        engine.pin(self.npc)
        stored = dict(self.npc.db.soul_needs)
        self._backdate(3)
        now = needs_mod.pressures(self.npc)
        for need, value in stored.items():
            if need.startswith("_") or need in ("health", "craving", "wardrobe"):
                continue
            self.assertAlmostEqual(now.get(need, 0.0), value, places=6,
                                   msg=f"{need} moved while pinned")

    def test_an_unpinned_soul_still_decays(self):
        """Control: the same three hours on a living soul raise hunger."""
        stored = dict(self.npc.db.soul_needs)
        self._backdate(3)
        now = needs_mod.pressures(self.npc)
        self.assertGreater(now["hunger"], stored["hunger"])

    def test_unpin_restarts_the_clock_without_catch_up(self):
        engine.pin(self.npc)
        stored = dict(self.npc.db.soul_needs)
        self._backdate(3)
        engine.unpin(self.npc)
        now = needs_mod.pressures(self.npc)
        self.assertAlmostEqual(now["hunger"], stored["hunger"], places=2,
                               msg="the frozen hours were paid back as hunger")

    def test_the_heartbeat_skips_a_pinned_soul(self):
        beat = engine.SoulsHeartbeat()
        with mock.patch.object(engine, "think") as think, \
             mock.patch.object(engine, "_wear_and_tear"):
            engine.pin(self.npc)
            beat._beat_soul(self.npc, 1, 12.0, {self.room1}, [], time.time())
            self.assertFalse(think.called, "a pinned soul thought")
            engine.unpin(self.npc)
            beat._beat_soul(self.npc, 1, 12.0, {self.room1}, [], time.time())
            self.assertTrue(think.called, "control: an unpinned hot soul did not think")

    def test_think_itself_refuses_a_pinned_soul(self):
        engine.pin(self.npc)
        with mock.patch.object(engine, "_desired_goal") as goal:
            engine.think(self.npc, 12.0)
            self.assertFalse(goal.called)

    def test_pin_stops_the_walk_and_drops_the_job(self):
        self.npc.db.soul_job = {"goal": "hunger", "steps": [], "at": 0}
        with mock.patch("world.director.travel.stop_travel") as stop:
            engine.pin(self.npc)
            self.assertTrue(stop.called)
        self.assertIsNone(self.npc.db.soul_job)
        self.assertTrue(engine.is_pinned(self.npc))
        self.assertIn(self.npc, engine.pinned_souls())

    def test_pin_and_unpin_are_idempotent(self):
        engine.pin(self.npc); engine.pin(self.npc)
        self.assertTrue(engine.is_pinned(self.npc))
        engine.unpin(self.npc); engine.unpin(self.npc)
        self.assertFalse(engine.is_pinned(self.npc))


class NothingOutsideTheHeartbeatPlansForAPinnedSoulTest(EvenniaTest):
    """The skeptics' finding: the freeze was right inside the heartbeat and
    blind everywhere else -- posts offered a frozen soul a claim job,
    dispatch handed it a respond job, and the arrival keeper counted it
    as a job-seeker and stopped the shuttle."""

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc", key="Mannequin", location=self.room1)
        self.npc.db.is_npc = True
        engine.ensoul(self.npc, role="hawker", home=None, post=None)
        engine.pin(self.npc)

    def test_the_post_sweep_never_offers_it_a_slot(self):
        from world.souls.posts import _eligible_candidates
        self.assertNotIn(self.npc, _eligible_candidates(self.room1))
        engine.unpin(self.npc)
        self.assertIn(self.npc, _eligible_candidates(self.room1), "control")

    def test_the_arrival_keeper_does_not_count_it_as_unemployed(self):
        from world.souls.population import unemployed_count
        self.assertEqual(unemployed_count([self.npc]), 0)
        engine.unpin(self.npc)
        self.assertEqual(unemployed_count([self.npc]), 1, "control")

    def test_dispatch_refuses_to_assign_it(self):
        from types import SimpleNamespace
        from world.director.assignment import assign, is_assigned
        event = SimpleNamespace(location=self.room2, source=None, type="crime", severity=1, id=1)
        self.assertFalse(assign(self.npc, event))
        self.assertFalse(is_assigned(self.npc))
        self.assertIsNone(self.npc.db.soul_job)

    def test_pin_pays_out_a_duty_shift(self):
        engine.unpin(self.npc)
        self.npc.db.soul_job = {"goal": "duty", "steps": [], "at": 0}
        with mock.patch.object(engine.economy, "pay_wage") as pay:
            engine.pin(self.npc)
            self.assertTrue(pay.called, "a shift cut short by a pin was not paid out")

    def test_a_homeless_soul_never_wants_rest(self):
        engine.unpin(self.npc)
        stored = dict(self.npc.db.soul_needs); stored["rest"] = 1.0; self.npc.db.soul_needs = stored
        band, goal = engine._desired_goal(self.npc, 12.0)
        self.assertNotEqual(goal, "rest", "rest was arbitrated for a soul with no home to sleep in")
