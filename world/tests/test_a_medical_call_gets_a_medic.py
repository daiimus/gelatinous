"""A phoned-in medical emergency reaches a medic.

Regression pin for #2721. `REPORTED_EVENTS` converted the classifier's
`medical` incident to `disturbance` before the director ever saw it:

    "medical": ("disturbance", 1),   # wellness check — no medic role yet

So a medical call dispatched SECURITY and never a medic -- behind a
comment whose reason had stopped being true. `dispatch.ROLE_RESPONDS_TO`
already maps `medical` to `("medic",)`, and the colony has a medic
(Maritza O' Cruz, #8288) alongside its eight security units.

The classifier recognised the type all along; the report layer threw it
away in the one step between them.
"""

from unittest import TestCase

from world.director.dispatch import ROLE_RESPONDS_TO
from world.director.radio_report import REPORTED_EVENTS


class TestAMedicalCallGetsAMedic(TestCase):

    def test_a_medical_report_stays_medical(self):
        self.assertEqual(REPORTED_EVENTS["medical"][0], "medical")

    def test_it_reaches_the_medic_role(self):
        """End to end through the two tables that have to agree."""
        incident = REPORTED_EVENTS["medical"][0]
        self.assertEqual(ROLE_RESPONDS_TO[incident], ("medic",))

    def test_every_reported_event_is_one_the_director_knows(self):
        """The shape of the defect: the two tables drifting apart.

        A mapping the director has no entry for would dispatch nobody,
        which is how this one hid -- `disturbance` IS a valid key, so
        the downgrade looked like it worked.
        """
        for name, (incident, _weight) in REPORTED_EVENTS.items():
            with self.subTest(name):
                self.assertIn(incident, ROLE_RESPONDS_TO)

    def test_the_other_mappings_are_unchanged(self):
        """The control — violence still scales, theft is still crime."""
        self.assertEqual(REPORTED_EVENTS["assault"], ("assault", 2))
        self.assertEqual(REPORTED_EVENTS["theft"][0], "crime")
        self.assertEqual(REPORTED_EVENTS["fire"][0], "fire")
