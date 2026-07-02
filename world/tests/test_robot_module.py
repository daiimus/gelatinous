"""Tests for the robot integrated shotgun module — same augment backend
as human chrome, robot-true presentation, factory-fitted at secbot spawn."""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock

from world.prototypes import (
    ROBOT_ARM_GUN,
    ROBOT_SHOTGUN_MODULE,
    ROBOT_SHOTGUN_MODULE_SPEC,
)


def _attr(proto, key):
    return dict(a[:2] for a in proto["attrs"]).get(key)


class TestRobotModulePrototypes(TestCase):
    def test_module_is_robot_species_gated(self):
        self.assertEqual(_attr(ROBOT_SHOTGUN_MODULE, "compatible_species"),
                         ["robot"])
        self.assertEqual(_attr(ROBOT_SHOTGUN_MODULE, "module_type"), "forearm")
        self.assertIs(_attr(ROBOT_SHOTGUN_MODULE, "organ_spec"),
                      ROBOT_SHOTGUN_MODULE_SPEC)

    def test_spec_is_standard_augment_backend(self):
        # Same shape as the human SHOTGUN_MODULE: hardpoint module organ
        # with an integrated_weapon ability — one backend, two presentations.
        spec = ROBOT_SHOTGUN_MODULE_SPEC
        self.assertTrue(spec["inorganic"])
        self.assertEqual(spec["hardpoint"], "forearm")
        ability = spec["abilities"]["shotgun"]
        self.assertEqual(ability["type"], "integrated_weapon")
        self.assertEqual(ability["weapon_prototype"], "ROBOT_ARM_GUN")

    def test_presentation_is_robot_true(self):
        # Module/deploy prose reads as factory equipment, not grafted chrome.
        ability = ROBOT_SHOTGUN_MODULE_SPEC["abilities"]["shotgun"]
        joined = " ".join(str(v) for v in ability.values()).lower()
        self.assertIn("manipulator", joined)
        self.assertIn("housing", joined)
        self.assertNotIn("flesh", joined)
        self.assertNotIn("skin", joined)
        self.assertIn("plant", ROBOT_SHOTGUN_MODULE["desc"])

    def test_arm_gun_reuses_machine_toned_bank(self):
        self.assertEqual(_attr(ROBOT_ARM_GUN, "weapon_type"),
                         "cybernetic_shotgun")
        self.assertTrue(_attr(ROBOT_ARM_GUN, "integrated"))
        self.assertIn("get:false()", ROBOT_ARM_GUN["locks"])


class TestFactoryFit(TestCase):
    def test_seats_side_formatted_organ_and_saves(self):
        from commands.CmdSpawnMob import CmdSpawnMob
        mob = MagicMock()
        mob.medical_state.organs = {}
        CmdSpawnMob._factory_fit_armament(mob, side="right")
        organ = mob.medical_state.organs["integrated_shotgun_module"]
        self.assertEqual(organ.data["container"], "right_arm")
        ability = organ.data["abilities"]["shotgun"]
        self.assertEqual(ability["slot"], "right_hand")
        self.assertIn("right forearm", ability["deploy_msg"])
        mob.save_medical_state.assert_called_once()
