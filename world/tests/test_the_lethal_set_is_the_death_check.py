"""One list of what kills you (#3677).

`_compute_is_dead` loops over `LETHAL_CAPACITY_NAMES`; the same tuple
drives the vital-location targeting bias; and every species' capacity
table flags exactly those capacities `directly_fatal`. Three places used
to name the five capacities by hand and had already drifted (breathing
and digestion were fatal in code and unflagged in the schema).

Behaviour pins: each lethal capacity at zero is a death on its own, a
full body is alive, and `consciousness` at its floor is not a death.
"""
import inspect
import re

from django.test import TestCase

from world.anatomy import get_species_body_capacities
from world.anatomy.species import SPECIES_DEFINITIONS
from world.medical.constants import LETHAL_CAPACITY_NAMES
from world.medical.core import MedicalState


def _flagged_fatal(species):
    """Capacities the schema calls directly fatal (organ-backed only; the
    `blood_loss` entry is a bleeding source, not a capacity)."""
    caps = get_species_body_capacities(species)
    return {name for name, data in caps.items()
            if data.get("directly_fatal") and data.get("organs")}


class TheThreeListsAgree(TestCase):

    def test_the_schema_flags_are_the_lethal_set_for_every_species(self):
        for species in SPECIES_DEFINITIONS:
            self.assertEqual(_flagged_fatal(species), set(LETHAL_CAPACITY_NAMES), species)

    def test_the_death_check_reads_the_tuple_not_a_hand_list(self):
        # No quoted capacity name at all, not just none of today's five:
        # the drift #3677 describes is a NEW name hand-coded here and left
        # out of the tuple, and that name is by definition not in the tuple.
        src = inspect.getsource(MedicalState._compute_is_dead)
        self.assertIn("for capacity in LETHAL_CAPACITY_NAMES", src)
        spelled = re.findall(r"""calculate_body_capacity\(\s*['"]([a-z_]+)['"]""", src)
        self.assertEqual(spelled, [], f"capacities spelled out by hand in the death check: {spelled}")

    def test_consciousness_is_not_in_the_set(self):
        self.assertNotIn("consciousness", LETHAL_CAPACITY_NAMES)


class EachLethalCapacityKillsOnItsOwn(TestCase):

    def test_control_a_whole_body_is_alive(self):
        state = MedicalState()
        for name in LETHAL_CAPACITY_NAMES:
            self.assertEqual(state.calculate_body_capacity(name), 1.0, name)
        self.assertFalse(state.is_dead())

    def test_zeroing_every_organ_of_one_capacity_is_a_death(self):
        caps = get_species_body_capacities("human")
        for name in LETHAL_CAPACITY_NAMES:
            state = MedicalState()
            for organ in caps[name]["organs"]:
                state.organs[organ].current_hp = 0
            self.assertEqual(state.calculate_body_capacity(name), 0.0, name)
            self.assertTrue(state.is_dead(), f"{name} at zero did not kill")

    def test_control_the_awake_axis_at_zero_is_not_a_death(self):
        state = MedicalState()
        state.consciousness = 0.0
        self.assertTrue(state.is_unconscious())
        self.assertFalse(state.is_dead())
