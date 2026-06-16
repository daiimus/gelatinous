"""Tests for the ``/system`` cyberware diagnostic readout (#567).

``render_system`` is a pure function over the medical-state organ view,
so these build duck-typed organs (no DB) and assert on the rendered
string.  One test prints the full render for each sample subject so the
visual can be eyeballed with ``evennia test ... --debug-mode`` / a
failure trace if the layout ever needs review.
"""

from __future__ import annotations

from types import SimpleNamespace as NS
from unittest import TestCase

from world.medical.cyberware_status import render_system


def _organ(container, hp, mx, data, astate=None):
    organ = NS(container=container, current_hp=hp, max_hp=mx, data=data)
    organ.ability_state = astate or {}
    return organ


def _char(organs):
    return NS(medical_state=NS(organs=organs))


# Chromed razorboy: cyber arm + shotgun (deployed), cyber jaw + jawz
# (retracted), damaged cyber left eye.
_RAZORBOY = {
    "right_humerus": _organ(
        "right_arm", 30, 30, {"inorganic": True, "prosthetic_frame": True}),
    "right_forearm_hardpoint": _organ(
        "right_arm", 12, 12,
        {"inorganic": True, "prosthetic_frame": True, "hardpoint": "forearm",
         "abilities": {"shotgun": {"type": "integrated_weapon"}}},
        {"shotgun": {"deployed": True}}),
    "right_metacarpals": _organ(
        "right_hand", 18, 18, {"inorganic": True, "prosthetic_frame": True}),
    "jaw": _organ(
        "head", 14, 14,
        {"inorganic": True, "prosthetic_frame": True, "hardpoint": "jaw",
         "abilities": {"jawz": {"type": "natural_weapon"}}},
        {"jawz": {"deployed": False}}),
    "left_eye": _organ(
        "head", 6, 14, {"inorganic": True, "prosthetic_frame": True}),
}

# Razorgirl: flesh body, Nailz both hands (deployed).
_RAZORGIRL = {
    "left_metacarpals": _organ(
        "left_hand", 15, 15,
        {"abilities": {"nailz": {"type": "natural_weapon"}}},
        {"nailz": {"deployed": True}}),
    "right_metacarpals": _organ(
        "right_hand", 15, 15,
        {"abilities": {"nailz": {"type": "natural_weapon"}}},
        {"nailz": {"deployed": True}}),
}


class TestCyberwareSystemReadout(TestCase):

    def test_no_cyberware(self):
        out = render_system(_char({}))
        self.assertIn("No cybernetics installed", out)

    def test_chrome_limb_groups_by_container(self):
        out = render_system(_char(_RAZORBOY))
        # Cyber arm = humerus + forearm hardpoint at right_arm → ONE device.
        self.assertIn("cybernetic right arm", out)
        self.assertIn("cybernetic right hand", out)
        self.assertEqual(out.count("cybernetic right arm"), 1)

    def test_head_organ_labels_by_name_not_head(self):
        out = render_system(_char(_RAZORBOY))
        self.assertIn("cybernetic jaw", out)        # not "cybernetic head"
        self.assertNotIn("cybernetic head", out)
        self.assertIn("cybernetic left eye", out)

    def test_deploy_state_shown(self):
        out = render_system(_char(_RAZORBOY))
        self.assertIn("shotgun", out)
        self.assertIn("DEPLOYED", out)
        self.assertIn("jawz", out)
        self.assertIn("retracted", out)

    def test_damaged_unit_reads_degraded_prose_only(self):
        out = render_system(_char(_RAZORBOY))
        self.assertIn("DAMAGED", out)
        self.assertIn("degraded", out)
        # Prose-only — no raw HP numbers.
        self.assertNotIn("6/14", out)

    def test_nailz_flesh_mount_groups_both_hands(self):
        out = render_system(_char(_RAZORGIRL))
        self.assertIn("Nailz", out)
        self.assertIn("both hands", out)
        self.assertIn("host tissue", out)
        self.assertIn("DEPLOYED", out)

    def test_render_visual_smoke(self):
        """Not an assertion of layout — prints the full render for both
        subjects so the box/tree can be eyeballed when reviewing."""
        for label, organs in (("RAZORBOY", _RAZORBOY),
                              ("RAZORGIRL", _RAZORGIRL)):
            rendered = render_system(_char(organs))
            print(f"\n===== {label} =====\n{rendered}")
            self.assertTrue(rendered)
