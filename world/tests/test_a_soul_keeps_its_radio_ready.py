"""#3777: a soul keeps its radio ready. One pure predicate says whether a
carried handheld is not transmit-ready and why; the band tree offers the
`comms` goal on it (idle band, duty band after a refused transmit); the
`ready_radio` job issues `wield` then `toggle ... on`, one real command
per beat, and faults legibly when it cannot.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.souls import actions, engine, jobs
from world.souls.comms import (
    ACTING, GAVE_UP, OFF, POCKET, READY, radio_to_ready, ready_beat, wants_comms,
)


def _radio(on=True, freq="27MHz", key="AWE Magpie radio"):
    r = MagicMock()
    r.key = key
    r.id = 7
    r.db.is_radio = True
    r.db.radio_on = on
    r.db.frequency = freq
    return r


def _tries(state, n, radio=7, age=0.0):
    import time
    return {"state": state, "radio": radio, "n": n, "at": time.time() - age}


def _soul(worn=(), hands=None, pocket=(), organ=None):
    s = MagicMock()
    s.key = "Wren"
    s.get_worn_items = lambda: list(worn)
    s.hands = dict(hands or {"left_hand": None, "right_hand": None})
    s.contents = list(worn) + [v for v in s.hands.values() if v] + list(pocket)
    s.medical_state = None
    s.location = MagicMock()
    s.db.soul_comms_pending = None
    s.db.soul_job = None
    s.db.soul_schedule = "day"
    s.db.soul_comms_tries = None

    def _search(phrase, candidates=None, quiet=False, **kw):
        pool = candidates if candidates is not None else s.contents
        return [o for o in pool if getattr(o, "key", None) == phrase]
    s.search = _search
    return s


# --------------------------------------------------------------------------
# The one predicate
# --------------------------------------------------------------------------

class TestWhatNeedsReadying(TestCase):
    def test_nothing_carried(self):
        self.assertIsNone(radio_to_ready(_soul()))

    def test_a_worn_set_on_and_tuned_is_ready(self):
        self.assertIsNone(radio_to_ready(_soul(worn=[_radio()])))

    def test_a_held_set_switched_off(self):
        r = _radio(on=False)
        s = _soul(hands={"left_hand": r, "right_hand": None})
        s.search = lambda phrase, **kw: [r]
        self.assertEqual(radio_to_ready(s), (OFF, r))

    def test_a_worn_set_on_but_on_no_band_is_not_wanted(self):
        """Nothing tells a soul its home band yet: not offered, not faulted."""
        self.assertIsNone(radio_to_ready(_soul(worn=[_radio(freq="scan")])))
        self.assertIsNone(radio_to_ready(_soul(worn=[_radio(freq=None)])))

    def test_a_pocket_set_with_both_hands_full_is_not_wanted(self):
        s = _soul(hands={"left_hand": MagicMock(), "right_hand": MagicMock()},
                  pocket=[_radio()])
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertIsNone(radio_to_ready(s))

    def test_an_off_set_with_a_twin_in_sight_is_not_wanted(self):
        """`toggle <key>` would multimatch and Evennia's ordinal cannot
        narrow a key with -01 in it: unreachable, so not wanted."""
        r = _radio(on=False)
        s = _soul(worn=[r])
        s.search = lambda phrase, **kw: [r, _radio(on=False)]
        self.assertIsNone(radio_to_ready(s))

    def test_an_off_set_alone_is_wanted(self):
        r = _radio(on=False)
        self.assertEqual(radio_to_ready(_soul(worn=[r])), (OFF, r))

    def test_a_pocket_radio(self):
        r = _radio()
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertEqual(radio_to_ready(_soul(pocket=[r])), (POCKET, r))

    def test_two_pocket_sets_with_one_key_are_not_wanted(self):
        """`wield <key>` takes whichever the search returns first, so the
        dead twin could end up in hand with the live one left behind."""
        dead, live = _radio(on=False), _radio()
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertIsNone(radio_to_ready(_soul(pocket=[dead, live])))

    def test_two_pocket_sets_with_different_keys_pick_the_live_one(self):
        dead, live = _radio(on=False, key="dead set"), _radio(key="live set")
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertEqual(radio_to_ready(_soul(pocket=[dead, live])), (POCKET, live))

    def test_a_comms_organ_covers_everything(self):
        s = _soul(pocket=[_radio(on=False)])
        with patch("world.souls.comms.comms_organ_frequency", return_value="911MHz"):
            self.assertIsNone(radio_to_ready(s))

    def test_wants_comms_is_the_predicate(self):
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertTrue(wants_comms(_soul(pocket=[_radio()])))
            self.assertFalse(wants_comms(_soul()))


# --------------------------------------------------------------------------
# The band tree
# --------------------------------------------------------------------------

class TestTheTreeOffersComms(TestCase):
    def desired(self, soul, hour=12.0, exclude=()):
        soul.db.soul_post = None
        soul.db.soul_home = None
        soul.db.patrol_beat = None
        with patch.object(engine.needs_mod, "pressures", return_value={}), \
                patch.object(engine.needs_mod, "profile_of", return_value=[]), \
                patch.object(engine.needs_mod, "critical_for", return_value=1.0), \
                patch("world.director.hunt.wants_hunt", return_value=False):
            return engine._desired_goal(soul, hour, exclude=exclude)

    def test_idle_band_when_a_set_needs_readying(self):
        s = _soul(pocket=[_radio()])
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertEqual(self.desired(s), (4, "comms"))

    def test_a_refused_call_is_not_a_goal_in_the_tree(self):
        """It is a reflex in think() (see TestTheReflex); the tree only
        ever offers comms as idle colour."""
        s = _soul(pocket=[_radio()])
        s.db.soul_comms_pending = True
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertEqual(self.desired(s), (4, "comms"))

    def test_nothing_offered_when_ready(self):
        self.assertEqual(self.desired(_soul()), (4, None))

    def test_a_cooling_goal_is_skipped(self):
        s = _soul(pocket=[_radio()])
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertEqual(self.desired(s, exclude={"comms"}), (4, None))

    def test_comms_is_idle_colour_for_interrupts(self):
        self.assertEqual(engine._goal_band("comms"), 4)


# --------------------------------------------------------------------------
# The plan
# --------------------------------------------------------------------------

class TestThePlan(TestCase):
    def test_one_step(self):
        s = _soul(pocket=[_radio()])
        with patch("world.radio.seated_base_station", return_value=None):
            plan = actions.plan_for(s, "comms")
        self.assertEqual(plan["goal"], "comms")
        self.assertEqual([st["do"] for st in plan["steps"]], ["ready_radio"])

    def test_no_plan_when_nothing_to_ready(self):
        self.assertIsNone(actions.plan_for(_soul(), "comms"))


# --------------------------------------------------------------------------
# ready_beat: one real command per beat, three beats per state
# --------------------------------------------------------------------------

class TestOneBeatOfReadying(TestCase):
    def beat(self, soul, want):
        with patch("world.souls.comms.radio_to_ready", return_value=want):
            return ready_beat(soul)

    def test_a_pocket_radio_is_wielded(self):
        s = _soul()
        self.assertEqual(self.beat(s, (POCKET, _radio())), ACTING)
        s.execute_cmd.assert_called_once_with("wield AWE Magpie radio")

    def test_a_switched_off_set_is_toggled_on(self):
        s = _soul()
        self.assertEqual(self.beat(s, (OFF, _radio(on=False))), ACTING)
        s.execute_cmd.assert_called_once_with("toggle AWE Magpie radio on")

    def test_ready_when_the_predicate_answers_none(self):
        s = _soul()
        s.db.soul_comms_tries = _tries(POCKET, 2)
        self.assertEqual(self.beat(s, None), READY)
        s.execute_cmd.assert_not_called()
        self.assertIsNone(s.db.soul_comms_tries)

    def test_each_beat_is_counted(self):
        s = _soul()
        self.beat(s, (POCKET, _radio()))
        rec = s.db.soul_comms_tries
        self.assertEqual((rec["state"], rec["n"]), (POCKET, 1))

    def test_the_count_starts_over_when_the_state_changes(self):
        """A pocket set that is also off: the wield counts against POCKET,
        the toggles against OFF — three beats per state."""
        s = _soul()
        s.db.soul_comms_tries = _tries(POCKET, 2)
        self.assertEqual(self.beat(s, (OFF, _radio(on=False))), ACTING)
        rec = s.db.soul_comms_tries
        self.assertEqual((rec["state"], rec["n"]), (OFF, 1))

    def test_three_beats_in_one_state_give_up(self):
        s = _soul()
        s.db.soul_comms_tries = _tries(POCKET, 3)
        self.assertEqual(self.beat(s, (POCKET, _radio())), GAVE_UP)
        s.execute_cmd.assert_not_called()
        self.assertIsNone(s.db.soul_comms_tries)

    def test_a_budget_from_an_earlier_episode_starts_over(self):
        """An idle job dropped mid-way, or a set readied another way, can
        leave a count behind; minutes later it is not this episode's."""
        s = _soul()
        s.db.soul_comms_tries = _tries(POCKET, 3, age=600.0)
        self.assertEqual(self.beat(s, (POCKET, _radio())), ACTING)
        self.assertEqual(s.db.soul_comms_tries["n"], 1)

    def test_a_saved_budget_is_a_mapping_not_a_dict(self):
        """Evennia hands a db dict back as a _SaverDict (a Mapping). The
        count must still read it, or it never passes 1 and a refused
        wield repeats every beat with no cap."""
        from collections.abc import Mapping

        class Saved(Mapping):
            def __init__(self, d): self._d = dict(d)
            def __getitem__(self, k): return self._d[k]
            def __iter__(self): return iter(self._d)
            def __len__(self): return len(self._d)

        s = _soul()
        s.db.soul_comms_tries = Saved(_tries(POCKET, 3))
        self.assertEqual(self.beat(s, (POCKET, _radio())), GAVE_UP)

    def test_a_budget_for_another_set_starts_over(self):
        s = _soul()
        s.db.soul_comms_tries = _tries(POCKET, 3, radio=999)
        self.assertEqual(self.beat(s, (POCKET, _radio())), ACTING)


# --------------------------------------------------------------------------
# The idle job delegates to ready_beat
# --------------------------------------------------------------------------

class TestTheIdleJob(TestCase):
    def job(self, soul):
        soul.db.soul_job = {"goal": "comms", "at": 0,
                            "steps": [{"do": "ready_radio"}]}
        return soul

    def step(self, soul, outcome):
        with patch("world.souls.comms.ready_beat", return_value=outcome), \
                patch("world.souls.jobs.fault") as fault:
            cont = jobs.step_job(soul)
        return cont, fault

    def test_acting_continues(self):
        s = self.job(_soul())
        cont, fault = self.step(s, ACTING)
        self.assertTrue(cont)
        self.assertEqual(s.db.soul_job["at"], 0)
        fault.assert_not_called()

    def test_ready_advances_and_clears_the_flag(self):
        s = self.job(_soul())
        s.db.soul_comms_pending = True
        cont, fault = self.step(s, READY)
        self.assertTrue(cont)
        self.assertEqual(s.db.soul_job["at"], 1)
        self.assertIsNone(s.db.soul_comms_pending)
        fault.assert_not_called()

    def test_giving_up_faults(self):
        s = self.job(_soul())
        cont, fault = self.step(s, GAVE_UP)
        self.assertFalse(cont)
        self.assertIn("could not ready the radio", fault.call_args.args[1])


# --------------------------------------------------------------------------
# The reflex: a refused call costs one beat, never the running job
# --------------------------------------------------------------------------

class TestTheReflex(TestCase):
    def think(self, soul, outcome):
        with patch("world.souls.comms.ready_beat", return_value=outcome) as beat, \
                patch("world.director.security._in_combat", return_value=False), \
                patch("world.director.travel.is_travelling", return_value=False), \
                patch("world.director.medical.notice_casualty"), \
                patch.object(engine, "is_pinned", return_value=False), \
                patch.object(engine.jobs, "step_job") as step, \
                patch.object(engine, "_desired_goal", return_value=(4, None)) as tree:
            engine.think(soul, 12.0)
        return beat, step, tree

    def _running(self):
        s = _soul()
        s.db.placed_by_shift = None
        s.db.soul_goal_cooldown = {}
        s.db.soul_job = {"goal": "run", "band": 2, "at": 1,
                         "steps": [{"do": "collect"}, {"do": "travel"}]}
        s.db.soul_comms_pending = True
        return s

    def test_one_beat_goes_to_the_radio_and_the_run_is_untouched(self):
        s = self._running()
        beat, step, tree = self.think(s, ACTING)
        beat.assert_called_once_with(s)
        step.assert_not_called()
        tree.assert_not_called()
        self.assertEqual(s.db.soul_job["goal"], "run")
        self.assertIs(s.db.soul_comms_pending, True)

    def test_when_ready_the_flag_clears_and_the_run_steps(self):
        s = self._running()
        beat, step, tree = self.think(s, READY)
        self.assertIsNone(s.db.soul_comms_pending)
        step.assert_called_once_with(s)
        self.assertEqual(s.db.soul_job["goal"], "run")

    def test_giving_up_also_clears_and_moves_on(self):
        s = self._running()
        _, step, _ = self.think(s, GAVE_UP)
        self.assertIsNone(s.db.soul_comms_pending)
        step.assert_called_once_with(s)

    def test_no_flag_no_reflex(self):
        s = self._running()
        s.db.soul_comms_pending = None
        beat, step, _ = self.think(s, ACTING)
        beat.assert_not_called()
        step.assert_called_once_with(s)
