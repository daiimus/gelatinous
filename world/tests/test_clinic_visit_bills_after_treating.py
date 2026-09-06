"""An NPC clinic visit must treat before it bills (#2428).

The `treat` step called `doctor._treat(soul, "bandage")`. **No such method
exists anywhere in the repo** -- build 143 swapped every
`typeclasses.clinic.Doctor` to `LLMNpc` and the name went with it. The
only real symbol is `world/clinic.py:_treat_tool`, registered as the
doctor's `treat` tool, and the live door underneath it is
`world.clinic.treat`.

The ORDER is what made it damaging. The fee moved first:

    soul.tokens -= TREAT_FEE
    terminal.db.register += TREAT_FEE
    doctor._treat(soul, "bandage")      # AttributeError

The exception unwound into `jobs.fault(soul, "beat crashed: ...")`, which
swallows it, so everything after -- the thought, the 30-minute cooldown,
clearing `soul_job` -- never ran either. The patient had paid and had
nothing to show for it, and a bleeding NPC owed free triage got nothing
at all.

The suite could not see it: `world/tests/test_clinic.py` invented
`d._treat` on its mock doctor, so the fixture supplied what production
did not.

Billing now follows delivery, so a clinic with no gauze turns you away
rather than charging you for it.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.souls import jobs


class _VisitCase(EvenniaTest):
    FEE = 8

    def setUp(self):
        super().setUp()
        self.patient = self.char1
        self.doctor = self.char2
        self.desk = self.obj1
        for o in (self.patient, self.doctor, self.desk):
            o.location = self.room1
        self.desk.db.register = 0
        self.patient.tokens = 100
        self.patient.db.soul_job = {"steps": [{"do": "treat",
                                               "clinic": self.desk.id}],
                                    "at": 0}

    def visit(self, treat_succeeds=True, bleeding=False, tokens=None):
        """Drive the real step with the clinic supply cupboard decided."""
        if tokens is not None:
            self.patient.tokens = tokens
        conditions = ([{"condition_type": "minor_bleeding", "severity": 3}]
                      if bleeding else [])
        self.patient.db.medical_state = {"conditions": conditions}
        self.treated = []

        def _treat(by, patient, what):
            self.treated.append(what)
            return treat_succeeds

        # Only the doctor is the doctor. A blanket return_value made the
        # room's EXIT the nearest "doctor", which still reproduced the
        # crash but for the wrong reason.
        def _job_of(obj):
            return ({"archetype": "doctor"} if obj is self.doctor else None)

        with mock.patch("world.service.job_of", side_effect=_job_of), \
             mock.patch("world.clinic.treat", side_effect=_treat), \
             mock.patch("world.souls.jobs._obj", return_value=self.desk):
            return jobs.step_job(self.patient)

    def register(self):
        return int(self.desk.db.register or 0)


class TestAPayingPatientIsTreatedAndCharged(_VisitCase):
    def test_they_get_the_bandage(self):
        self.visit()
        self.assertIn("bandage", self.treated)

    def test_they_get_the_painkiller_too(self):
        self.visit()
        self.assertIn("painkiller", self.treated)

    def test_the_fee_moves_to_the_register(self):
        self.visit()
        self.assertEqual(self.register(), self.FEE)

    def test_the_patient_pays_exactly_once(self):
        self.visit()
        self.assertEqual(int(self.patient.tokens), 100 - self.FEE)


class TestAClinicWithNothingToTreatWithDoesNotCharge(_VisitCase):
    """The ordering fault, stated as a rule: no delivery, no bill."""

    def test_the_register_stays_empty(self):
        self.visit(treat_succeeds=False)
        self.assertEqual(self.register(), 0)

    def test_the_patient_keeps_their_money(self):
        self.visit(treat_succeeds=False)
        self.assertEqual(int(self.patient.tokens), 100)

    def test_no_painkiller_is_attempted_either(self):
        self.visit(treat_succeeds=False)
        self.assertNotIn("painkiller", self.treated)


class TestFreeTriageForTheBleeding(_VisitCase):
    """A bleeding NPC who cannot pay is treated anyway -- and under the
    old code got nothing, because the crash landed after the branch that
    decided that."""

    def test_a_broke_bleeding_patient_is_still_bandaged(self):
        self.visit(bleeding=True, tokens=0)
        self.assertIn("bandage", self.treated)

    def test_they_are_not_charged(self):
        self.visit(bleeding=True, tokens=0)
        self.assertEqual(self.register(), 0)

    def test_they_do_not_get_the_painkiller(self):
        self.visit(bleeding=True, tokens=0)
        self.assertNotIn("painkiller", self.treated)

    def test_a_broke_patient_who_is_not_bleeding_is_turned_away(self):
        self.visit(bleeding=False, tokens=0)
        self.assertEqual(self.treated, [])


class TestTheBleedingCheckReadsTheRealField(_VisitCase):
    """The step carried its own copy of the pre-#2701 expression, which
    read a `type` key that does not exist, on a branch never taken --
    stored conditions are `_SaverDict` and fail `isinstance(c, dict)`."""

    def test_a_stored_bleeding_record_is_recognised(self):
        from world.souls.needs import is_bleeding_condition
        self.assertTrue(is_bleeding_condition(
            {"condition_type": "minor_bleeding", "severity": 3}))

    def test_a_non_bleeding_record_is_not(self):
        from world.souls.needs import is_bleeding_condition
        self.assertFalse(is_bleeding_condition(
            {"condition_type": "pain", "severity": 3}))
