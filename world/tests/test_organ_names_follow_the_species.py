"""A synth's organs are named by species on every surface (#3537).

A synthetic humanoid's liver is stored under the key ``liver`` (human
mechanics) and shown as a "filter gland" (alien presentation) through
``get_organ_display_name(name, species)``. The harvested item, the chart,
the operate picker and the medical organ table all used it; the wound
prose ``{organ}`` token, the ``medical`` summary's damaged-organ list and
the surgical refusals printed the raw key. A surgeon read "filter gland"
on the chart and "liver" in the wound line about the same organ.

Humans are the control: they still read "liver" everywhere.
"""
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import apply_species
from world.medical.utils import get_medical_status_summary
from world.medical.wounds.wound_descriptions import get_wound_description

STAGES = ("harvested", "fresh", "healing", "scarred")


class _Bodies(EvenniaTest):
    def body(self, species, key):
        who = create_object("typeclasses.characters.Character", key=key,
                            location=self.room1)
        apply_species(who, species)
        liver = who.medical_state.organs["liver"]
        liver.current_hp = int(liver.max_hp * 0.4)
        return who

    def wound_lines(self, who):
        container = who.medical_state.organs["liver"].container
        # `{organ}` lives in the banks' "harvested" injury type.
        return {get_wound_description("harvested", container, "Severe", stage,
                                      organ="liver", character=who)
                for stage in STAGES for _ in range(15)}


class TestTheMedicalSummary(_Bodies):
    def test_a_synth_reads_filter_gland(self):
        text = get_medical_status_summary(self.body("synthetic_humanoid", "Synthy"))
        self.assertIn("filter gland", text)
        self.assertNotIn("liver", text)

    def test_a_human_still_reads_liver(self):
        self.assertIn("liver", get_medical_status_summary(self.body("human", "Hume")))


class TestTheWoundLine(_Bodies):
    def test_a_synth_wound_names_the_filter_gland(self):
        lines = self.wound_lines(self.body("synthetic_humanoid", "Synthy"))
        self.assertTrue(any("filter gland" in l for l in lines), lines)
        self.assertFalse(any("liver" in l for l in lines), lines)

    def test_a_human_wound_still_names_the_liver(self):
        lines = self.wound_lines(self.body("human", "Hume"))
        self.assertTrue(any("liver" in l for l in lines), lines)


class TestTheHarvestRefusal(_Bodies):
    def _reach(self, who):
        from world.medical.procedures import _resolve_harvest
        seen = []
        self.char1.msg = lambda text=None, **kw: seen.append(str(text))
        container = who.medical_state.organs["liver"].container
        _resolve_harvest(self.char1, who, organ_name="liver", location=container)
        return " ".join(seen)

    def test_reaching_for_a_closed_filter_gland(self):
        said = self._reach(self.body("synthetic_humanoid", "Synthy"))
        self.assertIn("filter gland", said, said)
        self.assertNotIn("liver", said, said)

    def test_reaching_for_a_closed_human_liver(self):
        self.assertIn("liver", self._reach(self.body("human", "Hume")))
