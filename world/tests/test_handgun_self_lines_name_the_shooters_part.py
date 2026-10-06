"""A shooter's own line names the shooter's own part (#3708).

The loader fills ``{hit_location}`` with the TARGET's rolled location, so a
self line that spends it on the shooter's body read "Your groin is set in
concentration". In the five handgun banks, every attacker line now carries
the token only where its victim and observer siblings carry it too.
"""
import importlib
from unittest import TestCase

HANDGUNS = ("light_pistol", "light_revolver", "heavy_pistol", "heavy_revolver", "machine_pistol")


class TheShooterNamesTheirOwnPart(TestCase):

    def test_no_self_line_spends_the_targets_location_alone(self):
        for bank in HANDGUNS:
            messages = importlib.import_module(f"world.combat.messages.{bank}").MESSAGES
            for phase, entries in messages.items():
                for entry in entries:
                    if "{hit_location}" in entry["attacker_msg"]:
                        self.assertIn("{hit_location}", entry["victim_msg"],
                                      (bank, phase, entry["attacker_msg"]))
