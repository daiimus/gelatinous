"""The handgun banks fit one hand (MULTI_WEAPON_COMBAT_SPEC §10, slice 2).

Two pistols alternate, one per hand, so no handgun line may describe a
two-hand grip or speak of the shooter's hands in the plural.
"""
import importlib
import re
from unittest import TestCase

HANDGUNS = ("light_pistol", "light_revolver", "heavy_pistol", "heavy_revolver", "machine_pistol")
# No leading \b: a possessive follows a placeholder's closing brace, which is
# not a word character, so `\b` before the apostrophe never matched.
TWO_HANDS = re.compile(r"(?<![a-z])(both hands|two-handed|two hands|the other hand|your hands|their hands)(?![a-z])|['’]s hands\b", re.I)


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

