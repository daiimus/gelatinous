"""Shoot the surgeon and the operation is over (#2926).

Owner ruling: *"An operation should be interruptible. If someone starts
shooting while you're operating on someone — operation over."*

`interrupt_procedure` existed with **zero production callers** while five
docstrings asserted it fired, because surgery was never wired to
`world/channeled.py` — the shipped primitive for timed, interruptible
acts. That primitive already carries the taxonomy:

    BLOCKED  movement, wield, attack, xmit tune/toggle, bare `stop`
    BREAKING take_damage, combat enrollment, grapple establish,
             unconscious/death, forced movement

Seven sites already call `interrupt_channel`. Surgery is now the third
consumer, after graffiti and breach, so it inherits every one of those
without new interruption logic.

The channel **is** the timer rather than running beside the old `delay`:
two timers would resolve the procedure twice. `_finish` clears the
channel before firing `on_complete`, so the chart runner's back-to-back
steps each open a fresh channel without refusing themselves.

**One case the channel cannot cover**, handled separately: the channel is
on the SURGEON, so a patient dying under the knife would otherwise leave
the procedure running to completion on a corpse. `at_death` now ends any
operation being performed on that body too.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.medical import procedures


class _OperationCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.surgeon = self.char1
        self.patient = self.char2
        for c in (self.surgeon, self.patient):
            c.location = self.room1

    def begin(self, verb="incise"):
        return procedures.start_procedure(
            self.patient, verb=verb, actor=self.surgeon,
            location="chest")

    def operating(self):
        return procedures.is_procedure_active(self.patient)


class TestStartingAnOperationOpensAChannel(_OperationCase):
    def test_the_surgeon_is_channeling(self):
        from world.channeled import is_channeling
        self.begin()
        self.assertEqual(is_channeling(self.surgeon), "operating")

    def test_the_procedure_is_active(self):
        self.begin()
        self.assertTrue(self.operating())

    def test_the_room_can_see_what_they_are_doing(self):
        """A channel is public time — it sets a visible tell."""
        self.begin()
        self.assertIn("working on",
                      str(self.surgeon.override_place or ""))


class TestBreakingTheChannelEndsTheOperation(_OperationCase):
    def test_shooting_the_surgeon_ends_it(self):
        """The owner's case, through the real BREAKING path."""
        from world.channeled import interrupt_channel
        self.begin()
        interrupt_channel(self.surgeon, reason="shot")
        self.assertFalse(self.operating())

    def test_the_patient_is_not_left_mid_procedure(self):
        from world.channeled import interrupt_channel
        self.begin()
        interrupt_channel(self.surgeon)
        state = self.patient.db.surgical_state or {}
        self.assertIsNone(state.get("active_procedure"))

    def test_a_surgeon_who_is_not_interrupted_keeps_going(self):
        self.begin()
        self.assertTrue(self.operating())


class TestTheChartStepRecordsWhyItStopped(_OperationCase):
    def test_an_interrupted_step_is_marked_failed(self):
        self.patient.db.medical_chart = {
            "status": "running",
            "steps": [{"verb": "incise", "status": "running"}],
        }
        from world.channeled import interrupt_channel
        self.begin()
        interrupt_channel(self.surgeon)
        chart = self.patient.db.medical_chart or {}
        step = (chart.get("steps") or [{}])[0]
        self.assertEqual(step.get("status"), "failed")
        self.assertIn("interrupted", str(step.get("outcome")))

    def test_the_chart_is_aborted(self):
        self.patient.db.medical_chart = {
            "status": "running",
            "steps": [{"verb": "incise", "status": "running"}],
        }
        from world.channeled import interrupt_channel
        self.begin()
        interrupt_channel(self.surgeon)
        self.assertEqual((self.patient.db.medical_chart or {}).get("status"),
                         "aborted")


class TestThePatientDyingEndsIt(_OperationCase):
    """The channel is on the SURGEON, so this needs its own trigger —
    otherwise the operation completes on a corpse."""

    def test_death_under_the_knife_stops_the_procedure(self):
        self.begin()
        self.assertTrue(self.operating())
        with mock.patch.object(type(self.patient), "is_dead",
                               return_value=True):
            procedures.interrupt_procedure(self.patient,
                                           reason="the patient died")
        self.assertFalse(self.operating())

    def test_at_death_wires_it(self):
        import inspect
        from typeclasses.characters import Character
        src = inspect.getsource(Character.at_death)
        self.assertIn("interrupt_procedure", src)
