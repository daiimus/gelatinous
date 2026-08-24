"""The operate chart names components in the patient's own words (#2262).

Organ identity is the dict KEY, and the chart humanised it directly
with `replace("_", " ")`. So a mechanic charted against a list reading
*heart*, *liver*, *left kidney* while the prose underneath described a
power core. The description was already machine; the noun never was.

The act itself does not fork -- same chart, same hit locations, same
resolvers, same keys. Only the words change, because you do not
suture a robot.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.medical import charts


def _step(verb, **args):
    return {"verb": verb, "args": args}


class TestTheNoun(EvenniaCommandTest):
    def test_a_person_keeps_organic_words(self):
        self.assertEqual(
            charts.render_step_summary(_step("harvest", organ_name="heart")),
            "harvest heart")

    def test_a_chassis_reads_as_a_machine(self):
        self.assertEqual(
            charts.render_step_summary(_step("harvest", organ_name="heart"),
                                       "robot"),
            "pull power core")

    def test_the_organs_that_used_to_leak_worst(self):
        for organ, reads in (("liver", "fluid reclaimer"),
                             ("left_kidney", "left coolant filter"),
                             ("stomach", "fuel cell"),
                             ("left_lung", "left cooling unit"),
                             ("brain", "processor core")):
            with self.subTest(organ=organ):
                self.assertIn(reads, charts.render_step_summary(
                    _step("harvest", organ_name=organ), "robot"))

    def test_it_resolves_through_the_same_helper_as_the_readout(self):
        """The chart must not carry its own table, or it drifts from
        the medical readout printed beside it."""
        from world.anatomy import get_organ_display_name
        self.assertIn(get_organ_display_name("left_femur", "robot"),
                      charts.render_step_summary(
                          _step("harvest", organ_name="left_femur"), "robot"))


class TestTheVerb(EvenniaCommandTest):
    def test_you_do_not_suture_a_robot(self):
        self.assertEqual(
            charts.render_step_summary(_step("suture", location="chest"),
                                       "robot"),
            "seal chest")

    def test_nor_suture_all_of_one(self):
        self.assertEqual(
            charts.render_step_summary(_step("suture"), "robot"), "seal all")

    def test_a_mechanic_cuts_in_and_pulls(self):
        self.assertEqual(
            charts.render_step_summary(_step("incise", location="chest"),
                                       "robot"), "cut into chest")
        self.assertEqual(
            charts.render_step_summary(_step("amputate", location="left_arm"),
                                       "robot"), "shear off left arm")

    def test_and_seats_a_component(self):
        self.assertEqual(
            charts.render_step_summary(
                _step("install", organ_item_key="power core",
                      location="chest"), "robot"),
            "seat power core in chest")

    def test_a_surgeon_still_sutures(self):
        self.assertEqual(
            charts.render_step_summary(_step("suture", location="chest")),
            "suture chest")

    def test_an_unlisted_verb_keeps_its_word(self):
        """The verb table is a partial override, not a replacement."""
        self.assertEqual(
            charts.render_step_summary(_step("autopsy"), "robot"),
            "conduct autopsy")


class TestNothingElseMoved(EvenniaCommandTest):
    def test_the_species_argument_is_optional(self):
        """Existing callers must keep working untouched — the whole
        reason this could be a one-seam change."""
        self.assertEqual(
            charts.render_step_summary(_step("incise", location="chest")),
            "incise chest")

    def test_item_keys_are_not_species_translated(self):
        """An item key is already the words a player sees."""
        self.assertEqual(
            charts.render_step_summary(
                _step("apply", item_key="sealant patches", location="chest"),
                "robot"),
            "apply sealant patches on chest")

    def test_a_synthetic_keeps_organic_words(self):
        self.assertEqual(
            charts.render_step_summary(_step("suture", location="chest"),
                                       "synthetic_humanoid"),
            "suture chest")

    def test_a_missing_organ_still_renders(self):
        self.assertEqual(
            charts.render_step_summary(_step("harvest"), "robot"), "pull ?")


class TestTheLastUndescribedComponent(EvenniaCommandTest):
    def test_every_organ_a_unit_has_is_described(self):
        import world.anatomy.organ_descriptions as m
        from world.anatomy.species import SPECIES_DEFINITIONS
        described = set(m.ORGAN_DESCRIPTIONS_ROBOT)
        labelled = set(SPECIES_DEFINITIONS["robot"].get("organ_display") or {})
        # augments are machine-named by nature and carry their own prose
        self.assertEqual(labelled - described, set())

    def test_the_neck_reads_as_a_servo_column(self):
        import world.anatomy.organ_descriptions as m
        entry = m.ORGAN_DESCRIPTIONS_ROBOT["cervical_spine"]
        self.assertIn("servo column", entry["pristine"])
        self.assertIn("amber", entry["damaged"])
