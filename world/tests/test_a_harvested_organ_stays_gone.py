"""A harvested organ does not heal back, and a transplanted one does (#3651).

Organ loss is permanent (#3400); only a transplant fills the slot again.
`MedicalState.full_heal` knew a harvested organ was absent, but the two
healing paths a player actually reaches did not ask:

* wound care (`treatments.damaged_organs_at_location`) listed every organ
  below full HP, so dressing the open abdomen a harvest leaves behind
  stabilised the harvested kidney and set its healing rate, and an
  organ-repair item through that same incision restored its HP outright;
* the medical script's per-tick healing (`script._healing_organs`) then
  healed any stabilised organ back.

All three now ask `MedicalState.organ_is_gone`. And the organic transplant
branch now clears the harvest markers the way the chrome branch always did
(#3047), or the new organ would have read as still gone and never healed.
Real bodies throughout; controls first.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical import procedures
from world.medical.procedures import _mark_organ_removed
from world.medical.script import _healing_organs
from world.medical.treatments import damaged_organs_at_location


class _Harvested(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.ms = self.char1.medical_state
        _mark_organ_removed(self.char1, "left_kidney")
        self.gone = self.ms.organs["left_kidney"]
        assert self.gone.current_hp == 0 and self.ms.organ_is_gone("left_kidney"), "fixture"
        # The control: an ordinary wound at the same location.
        self.hurt = self.ms.organs["right_kidney"]
        self.hurt.current_hp = self.hurt.max_hp // 2


class WoundCareDoesNotReachAHarvestedOrgan(_Harvested):

    def test_the_wound_list_holds_the_injury_and_not_the_absence(self):
        found = damaged_organs_at_location(self.char1, "abdomen")
        self.assertIn(self.hurt, found, "control: an ordinary wound must be treatable")
        self.assertNotIn(self.gone, found, "a harvested organ was offered to wound care")

    def test_the_healing_tick_skips_it_even_if_dressed(self):
        for organ in (self.gone, self.hurt):
            organ.stabilized = True
            organ.dressing_rate = 50
        healing = _healing_organs(self.ms)
        self.assertIn(self.hurt, healing, "control: a dressed wound must heal")
        self.assertNotIn(self.gone, healing, "a harvested organ would heal back")

    def test_an_organ_repair_item_does_not_restore_it(self):
        from world.medical import treatments
        result = {"rolls": {"organ_repair": {"item_rating": 8}}, "messages": []}
        with patch("world.medical.procedures.has_incision", return_value=True):
            treatments._apply_organ_repair_outcome(self.char1, "abdomen", "success", result)
        self.assertEqual(self.gone.current_hp, 0, "organ repair regrew a harvested kidney")
        self.assertGreater(self.hurt.current_hp, self.hurt.max_hp // 2,
                           "control: organ repair must still mend the ordinary wound")

    def test_full_heal_still_leaves_it_gone(self):
        self.ms.full_heal()
        self.assertEqual(self.gone.current_hp, 0)
        self.assertEqual(self.hurt.current_hp, self.hurt.max_hp)


class AnOrganicTransplantIsPresent(_Harvested):
    """The organic install branch never cleared the markers, so a donor
    kidney read as still harvested: unhealable, and refused by harvest."""

    def _install(self, condition="pristine"):
        kidney = create_object("typeclasses.items.Item", key="donor kidney",
                               location=self.char2)
        kidney.db.organ_name = "left_kidney"
        kidney.db.condition = condition
        from world.anatomy import species_of
        kidney.db.source_species = species_of(self.char1) or "human"   # the species gate
        with patch.object(procedures, "roll_procedure", return_value={"outcome": "success"}), \
                patch.object(procedures, "has_incision", return_value=True):
            procedures._resolve_install(self.char2, self.char1, organ_item=kidney,
                                        location="abdomen")

    def test_the_new_organ_is_not_gone(self):
        self._install()
        self.assertGreater(self.ms.organs["left_kidney"].current_hp, 0, "fixture: install did not seat")
        self.assertFalse(self.ms.organ_is_gone("left_kidney"))
        self.assertNotIn("left_kidney", self.char1.db.removed_organs or [])

    def test_a_damaged_transplant_can_heal(self):
        self._install("damaged")
        kidney = self.ms.organs["left_kidney"]
        assert 0 < kidney.current_hp < kidney.max_hp, "fixture"
        self.assertIn(kidney, damaged_organs_at_location(self.char1, "abdomen"))
        self.ms.full_heal()
        self.assertEqual(kidney.current_hp, kidney.max_hp)
