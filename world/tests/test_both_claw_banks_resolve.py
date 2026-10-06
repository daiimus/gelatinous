"""Both claw banks resolve every phase (MULTI_WEAPON_COMBAT_SPEC §7, §13).

`nailz` is one hand, `nailz_akimbo` the designed pair; the
loader reaches each by `choice.weapon_type`. Neither may leave a phase to
the generic fallback, and the pair bank no longer dresses an implant in
gloves or a belt.
"""
import importlib
from unittest import TestCase

PHASES = ("initiate", "hit", "miss", "kill")


class BothBanksResolve(TestCase):

    def _bank(self, name):
        return importlib.import_module(f"world.combat.messages.{name}").MESSAGES

    def test_every_phase_has_entries_in_both_banks(self):
        for name in ("nailz", "nailz_akimbo"):
            bank = self._bank(name)
            for phase in PHASES:
                self.assertTrue(bank.get(phase), f"{name} has no {phase} lines")
                for entry in bank[phase]:
                    self.assertEqual(set(entry), {"attacker_msg", "victim_msg", "observer_msg"}, (name, phase))

    def test_the_one_hand_bank_never_speaks_of_both_hands(self):
        import re
        pat = re.compile(r"\b(both hands|both|ten|hands|fingers|gloves?|belt|five blades|pair|twin|two)\b", re.I)
        for phase, entries in self._bank("nailz").items():
            for entry in entries:
                for line in entry.values():
                    self.assertIsNone(pat.search(line), (phase, line))

    def test_the_pair_bank_is_an_implant_not_a_glove(self):
        for phase, entries in self._bank("nailz_akimbo").items():
            for entry in entries:
                for line in entry.values():
                    self.assertNotIn("glove", line.lower(), (phase, line))
                    self.assertNotIn("belt", line.lower(), (phase, line))
                self.assertNotIn("{hit_location}", entry["attacker_msg"].replace("{target_name}'s {hit_location}", "")
                                 if phase == "initiate" else "", (phase, entry["attacker_msg"]))

    def test_the_loader_reaches_both_by_weapon_type(self):
        from world.combat.messages import get_combat_message
        for name in ("nailz", "nailz_akimbo"):
            for phase in PHASES:
                out = get_combat_message(name, phase, attacker=None, target=None, item=None,
                                         hit_location="chest", damage=3, audiences=("actor",))
                self.assertTrue(out.get("attacker_msg"), (name, phase))
                self.assertNotIn("Error:", out["attacker_msg"], (name, phase))
