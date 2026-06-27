"""Tests for robot spawn flavor — short descs, longdescs, look places,
and the sdesc-key vocabulary used by ``@spawnmob/robot``.
"""

from __future__ import annotations

from unittest import TestCase

from world.identity import ROBOT_CHASSIS, ROBOT_FINISHES
from world.mob_flavor import (
    _LONGDESCS_BY_SPECIES,
    _LOOK_PLACES_BY_SPECIES,
    _SHORT_DESCS_BY_SPECIES,
    random_longdesc,
    random_look_place,
    random_short_desc,
)


class TestRobotFlavor(TestCase):
    def test_robot_registered_in_all_axes(self):
        self.assertIn("robot", _SHORT_DESCS_BY_SPECIES)
        self.assertIn("robot", _LOOK_PLACES_BY_SPECIES)
        self.assertIn("robot", _LONGDESCS_BY_SPECIES)

    def test_short_descs_are_mechanical(self):
        joined = " ".join(_SHORT_DESCS_BY_SPECIES["robot"]).lower()
        self.assertIn("servo", joined)
        # no organic breathing imagery on a machine
        for line in _SHORT_DESCS_BY_SPECIES["robot"]:
            self.assertNotIn("breath", line.lower())

    def test_longdesc_covers_humanoid_slots_no_hair(self):
        slots = _LONGDESCS_BY_SPECIES["robot"]
        for slot in ("head", "face", "neck", "chest", "back", "abdomen",
                     "groin", "eyes", "ears", "arms", "hands", "thighs",
                     "shins", "feet"):
            self.assertIn(slot, slots)
            self.assertTrue(slots[slot], f"{slot} has no options")
        # robots are unhaired — that slot stays unseeded
        self.assertNotIn("hair", slots)

    def test_pair_slots_use_braced_nouns(self):
        for line in _LONGDESCS_BY_SPECIES["robot"]["eyes"]:
            self.assertIn("{eyes}", line)
        for line in _LONGDESCS_BY_SPECIES["robot"]["arms"]:
            self.assertIn("{arms}", line)

    def test_name_vocab_composes(self):
        self.assertTrue(ROBOT_FINISHES)
        self.assertTrue(ROBOT_CHASSIS)
        name = f"a {ROBOT_FINISHES[0]} {ROBOT_CHASSIS[0]} robot"
        self.assertTrue(name.startswith("a "))
        self.assertTrue(name.endswith(" robot"))

    def test_random_helpers_return_robot_content(self):
        self.assertIn(random_short_desc("robot"),
                      _SHORT_DESCS_BY_SPECIES["robot"])
        self.assertIn(random_look_place("robot"),
                      _LOOK_PLACES_BY_SPECIES["robot"])
        self.assertIn(random_longdesc("eyes", "robot"),
                      _LONGDESCS_BY_SPECIES["robot"]["eyes"])
