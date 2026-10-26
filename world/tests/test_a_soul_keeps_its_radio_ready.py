"""#3777: a soul keeps its radio ready. One pure predicate says whether a
carried handheld is not transmit-ready and why; the band tree offers the
`comms` goal on it (idle band, duty band after a refused transmit); the
`ready_radio` job issues `wield` then `toggle ... on`, one real command
per beat, and faults legibly when it cannot.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.souls import actions, engine, jobs
from world.souls.comms import OFF, POCKET, UNTUNED, radio_to_ready, wants_comms


def _radio(on=True, freq="27MHz", key="AWE Magpie-01 radio"):
    r = MagicMock()
    r.key = key
    r.db.is_radio = True
    r.db.radio_on = on
    r.db.frequency = freq
    return r


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
        why, which = radio_to_ready(_soul(hands={"left_hand": r, "right_hand": None}))
        self.assertEqual((why, which), (OFF, r))

    def test_a_worn_set_sweeping(self):
        r = _radio(freq="scan")
        self.assertEqual(radio_to_ready(_soul(worn=[r]))[0], UNTUNED)

    def test_a_worn_set_on_no_band(self):
        r = _radio(freq=None)
        self.assertEqual(radio_to_ready(_soul(worn=[r]))[0], UNTUNED)

    def test_a_pocket_radio(self):
        r = _radio()
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertEqual(radio_to_ready(_soul(pocket=[r])), (POCKET, r))

    def test_the_pocket_set_already_on_and_tuned_comes_first(self):
        dead, live = _radio(on=False, key="dead set"), _radio(key="live set")
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertIs(radio_to_ready(_soul(pocket=[dead, live]))[1], live)

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

    def test_duty_band_after_a_refused_transmit(self):
        s = _soul(pocket=[_radio()])
        s.db.soul_comms_pending = True
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertEqual(self.desired(s), (2, "comms"))

    def test_nothing_offered_when_ready(self):
        self.assertEqual(self.desired(_soul()), (4, None))

    def test_a_pending_flag_with_nothing_to_ready_offers_nothing(self):
        s = _soul()
        s.db.soul_comms_pending = True
        self.assertEqual(self.desired(s), (4, None))

    def test_a_cooling_goal_is_skipped(self):
        s = _soul(pocket=[_radio()])
        with patch("world.radio.seated_base_station", return_value=None):
            self.assertEqual(self.desired(s, exclude={"comms"}), (4, None))

    def test_comms_is_a_band_two_goal_for_interrupts(self):
        self.assertEqual(engine._goal_band("comms"), 2)


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
# The job: one real command per beat
# --------------------------------------------------------------------------

class TestReadyingTheRadio(TestCase):
    def job(self, soul, tries=0):
        soul.db.soul_job = {"goal": "comms", "at": 0,
                            "steps": [{"do": "ready_radio", "tries": tries}]}
        return soul

    def step(self, soul, want):
        with patch("world.souls.comms.radio_to_ready", return_value=want), \
                patch("world.souls.jobs.fault") as fault:
            cont = jobs.step_job(soul)
        return cont, fault

    def test_a_pocket_radio_is_wielded(self):
        s = self.job(_soul())
        cont, fault = self.step(s, (POCKET, _radio()))
        s.execute_cmd.assert_called_once_with("wield AWE Magpie-01 radio")
        self.assertTrue(cont)
        fault.assert_not_called()

    def test_a_switched_off_set_is_toggled_on(self):
        s = self.job(_soul())
        cont, _ = self.step(s, (OFF, _radio(on=False)))
        s.execute_cmd.assert_called_once_with("toggle AWE Magpie-01 radio on")
        self.assertTrue(cont)

    def test_done_when_the_predicate_answers_none(self):
        s = self.job(_soul())
        s.db.soul_comms_pending = True
        cont, fault = self.step(s, None)
        s.execute_cmd.assert_not_called()
        self.assertTrue(cont)
        self.assertEqual(s.db.soul_job["at"], 1)
        self.assertIsNone(s.db.soul_comms_pending)
        fault.assert_not_called()

    def test_hands_full_faults(self):
        s = self.job(_soul(hands={"left_hand": MagicMock(), "right_hand": MagicMock()}))
        s.db.soul_comms_pending = True
        cont, fault = self.step(s, (POCKET, _radio()))
        s.execute_cmd.assert_not_called()
        self.assertFalse(cont)
        self.assertIn("hands full", fault.call_args.args[1])
        self.assertIsNone(s.db.soul_comms_pending)

    def test_no_band_faults(self):
        s = self.job(_soul())
        cont, fault = self.step(s, (UNTUNED, _radio(freq=None)))
        s.execute_cmd.assert_not_called()
        self.assertFalse(cont)
        self.assertIn("no band", fault.call_args.args[1])

    def test_three_refused_tries_fault(self):
        s = self.job(_soul(), tries=3)
        cont, fault = self.step(s, (POCKET, _radio()))
        s.execute_cmd.assert_not_called()
        self.assertFalse(cont)
        self.assertIn("could not ready", fault.call_args.args[1])

    def test_each_try_is_counted(self):
        s = self.job(_soul())
        self.step(s, (POCKET, _radio()))
        self.assertEqual(s.db.soul_job["steps"][0]["tries"], 1)
