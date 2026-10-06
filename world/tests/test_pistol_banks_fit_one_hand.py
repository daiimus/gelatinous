"""The handgun banks fit one hand (MULTI_WEAPON_COMBAT_SPEC §10, slice 2).

Two pistols alternate, one per hand, so no handgun line may describe a
two-hand grip or speak of the shooter's hands in the plural. The Nailz
banks name no other weapon (owner ruling §14 #10).
"""
import importlib
import re
from unittest import TestCase

HANDGUNS = ("light_pistol", "light_revolver", "heavy_pistol", "heavy_revolver", "machine_pistol")
TWO_HANDS = re.compile(r"\b(both hands|two-handed|two hands|the other hand|in your hands|in their hands|'s hands)\b", re.I)


def _lines(bank):
    for phase, entries in importlib.import_module(f"world.combat.messages.{bank}").MESSAGES.items():
        for entry in entries:
            for role, line in entry.items():
                yield phase, role, line


class HandgunsFitOneHand(TestCase):

    def test_no_handgun_line_needs_two_hands(self):
        for bank in HANDGUNS:
            for phase, role, line in _lines(bank):
                self.assertIsNone(TWO_HANDS.search(line), (bank, phase, role, line))


class TheNailzBanksNameNoOtherWeapon(TestCase):

    def test_no_tiger_in_the_nailz_banks(self):
        for bank in ("nailz", "nailz_akimbo"):
            for phase, role, line in _lines(bank):
                self.assertNotIn("tiger", line.lower(), (bank, phase, role, line))
