"""Akimbo pairs by weapon type (MULTI_WEAPON_COMBAT_SPEC §5, §13 slice 4,
#3718; owner ruling §14 #14: *"focus on weapon type akimbo combinations and
then just insert the item name"*).

Two items of one `weapon_type` with a row in `AKIMBO_PROFILES_BY_TYPE` are
one attack on the row's values and bank; the bank says `{item_name}` for the
lead item. Two types never pair; a type without a row never pairs. The
Voxhaul Tiger claw is sold one to a hand and pairs with its own kind.
"""
import importlib
import re
from unittest import TestCase
from unittest.mock import patch

from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import AKIMBO_PROFILES_BY_TYPE
from world.combat.weapon_choice import choose_weapon, weapon_options
from world.tests.test_weapon_autoprioritizer import _char, _weapon

PHASES = ("initiate", "hit", "miss", "kill")
NEW_BANKS = ("tiger_claws", "tiger_claws_akimbo", "light_pistol_akimbo")
ALLOWED = {"attacker_name", "target_name", "hit_location", "item_name", "blood", "Blood"}


def _bank(name):
    return importlib.import_module(f"world.combat.messages.{name}").MESSAGES


def _lines(name):
    for phase, entries in _bank(name).items():
        for entry in entries:
            for role, line in entry.items():
                yield phase, role, line


class TheDoorPairsByType(TestCase):

    def test_two_light_pistols_of_any_make_are_one_attack(self):
        pam = _weapon("PAM Model 6 pistol", True, 12, weapon_type="light_pistol")
        other = _weapon("HDG compact pistol", True, 12, weapon_type="light_pistol")
        attacker = _char([pam, other], slots=["left_hand", "right_hand"])
        choice = choose_weapon(attacker)
        self.assertTrue(choice.akimbo)
        self.assertEqual((choice.weapon_type, choice.damage, choice.hit_bonus), ("light_pistol_akimbo", 16, -1))
        self.assertTrue(choice.is_ranged)
        self.assertIs(choice.item, pam)

    def test_a_light_and_a_heavy_pistol_alternate(self):
        light = _weapon("PAM Model 6 pistol", True, 12, weapon_type="light_pistol")
        heavy = _weapon("HDG M88 tactical pistol", True, 18, weapon_type="heavy_pistol")
        attacker = _char([light, heavy], slots=["left_hand", "right_hand"])
        self.assertEqual([len(o.items) for o in weapon_options(attacker)], [1, 1])

    def test_two_tiger_claws_pair_on_the_claws_row(self):
        a = _weapon("Voxhaul Tiger claw", False, 6, weapon_type="tiger_claws", damage_type="cut")
        b = _weapon("Voxhaul Tiger claw", False, 6, weapon_type="tiger_claws", damage_type="cut")
        attacker = _char([a, b], slots=["left_hand", "right_hand"])
        choice = choose_weapon(attacker)
        self.assertEqual((choice.weapon_type, choice.damage, choice.hit_bonus, choice.damage_type),
                         ("tiger_claws_akimbo", 9, 1, "cut"))
        self.assertFalse(choice.natural)

    def test_a_held_claw_and_a_nailz_hand_are_two_weapons(self):
        # Same idea, different types: the glove and the implant never pair.
        # Precedence is off so the natural does not simply outrank the glove
        # (that is ruling §14 #2, tested elsewhere); only the grouping is asked.
        glove = _weapon("Voxhaul Tiger claw", False, 6, weapon_type="tiger_claws")
        attacker = _char([glove, None], slots=["left_hand", "right_hand"])
        with patch("world.medical.augments.get_active_natural_weapons",
                   return_value=[("right_hand", _weapon("carbide blades", False, 6, weapon_type="nailz"))]):
            options = weapon_options(attacker, precedence=False)
        self.assertEqual([len(o.items) for o in options], [1, 1])
        self.assertEqual({o.weapon_type for o in options}, {"tiger_claws", "nailz"})

    def test_every_row_names_banks_that_exist(self):
        for weapon_type, rows in AKIMBO_PROFILES_BY_TYPE.items():
            importlib.import_module(f"world.combat.messages.{weapon_type}")
            for count, profile in rows.items():
                self.assertGreater(count, 1, weapon_type)
                importlib.import_module(f"world.combat.messages.{profile['weapon_type']}")


class TheNewBanksResolve(TestCase):

    def test_every_phase_has_entries_with_three_roles(self):
        for name in NEW_BANKS:
            bank = _bank(name)
            for phase in PHASES:
                self.assertTrue(bank.get(phase), f"{name} has no {phase} lines")
                for entry in bank[phase]:
                    self.assertEqual(set(entry), {"attacker_msg", "victim_msg", "observer_msg"}, (name, phase))

    def test_only_known_placeholders(self):
        for name in NEW_BANKS:
            for phase, role, line in _lines(name):
                used = set(re.findall(r"\{([A-Za-z_]+)\}", line))
                self.assertTrue(used <= ALLOWED, (name, phase, role, used - ALLOWED))
                self.assertEqual(line.count("{"), line.count("}"), (name, phase, role, line))

    def test_the_pair_banks_insert_the_item_name(self):
        for name in ("tiger_claws_akimbo", "light_pistol_akimbo"):
            for phase in PHASES:
                self.assertTrue(any("{item_name}" in e["attacker_msg"] for e in _bank(name)[phase]), (name, phase))

    def test_the_one_glove_bank_never_speaks_of_two(self):
        pat = re.compile(r"\b(both|pair|twin|two|eight|second (claw|glove|hand)|each other|one claw then the other)\b", re.I)
        for phase, role, line in _lines("tiger_claws"):
            self.assertIsNone(pat.search(line), (phase, role, line))

    def test_blood_is_a_token_never_a_colour(self):
        for name in NEW_BANKS:
            for phase, role, line in _lines(name):
                self.assertNotRegex(line, r"\b(red|crimson|scarlet|cobalt|amber)\b", (name, phase, role, line))

    def test_each_bank_keeps_to_its_own_weapon(self):
        for name in ("tiger_claws", "tiger_claws_akimbo"):
            for phase, role, line in _lines(name):
                self.assertNotRegex(line.lower(), r"pistol|bullet|trigger|muzzle|fingernail", (name, phase, role, line))
        for phase, role, line in _lines("light_pistol_akimbo"):
            self.assertNotRegex(line.lower(), r"claw|tiger|blade", (phase, role, line))

    def test_the_loader_reaches_each_by_weapon_type(self):
        from world.combat.messages import get_combat_message
        for name in NEW_BANKS:
            for phase in PHASES:
                out = get_combat_message(name, phase, attacker=None, target=None, item=None,
                                         hit_location="chest", damage=3, audiences=("actor",))
                self.assertTrue(out.get("attacker_msg"), (name, phase))
                self.assertNotIn("Error:", out["attacker_msg"], (name, phase))
                self.assertNotIn("{", out["attacker_msg"], (name, phase, out["attacker_msg"]))


class TheDataSaysSo(TestCase):

    def test_nailz_carries_no_pair_attributes(self):
        from world import prototypes as P
        self.assertFalse({"akimbo_family", "akimbo_profiles"} & set(dict(P.NAILZ_CLAWS["attrs"])))
        self.assertIn("nailz", AKIMBO_PROFILES_BY_TYPE)

    def test_the_tiger_claw_is_a_branded_held_cut_weapon_on_the_rack(self):
        from world import prototypes as P
        self.assertEqual(P.TIGER_CLAWS["prototype_parent"], "MELEE_WEAPON_BASE")
        self.assertTrue(P.TIGER_CLAWS["key"].startswith("Voxhaul "))
        self.assertEqual((P.TIGER_CLAWS["weapon_type"], P.TIGER_CLAWS["damage"], P.TIGER_CLAWS["damage_type"]),
                         ("tiger_claws", 6, "cut"))
        self.assertNotIn("hands_required", P.TIGER_CLAWS)
        # Nailz parity: hooks sever nothing and parry no better than bare steel.
        self.assertFalse({"can_sever", "deflection_bonus"} & set(P.TIGER_CLAWS))
        self.assertEqual(dict(P.WEAPONS_SHELF["attrs"])["prototype_inventory"]["TIGER_CLAWS"], 180)

    def test_the_light_pistol_type_has_the_pair_row(self):
        from world import prototypes as P
        self.assertEqual(dict(P.LIGHT_PISTOL["attrs"])["weapon_type"], "light_pistol")
        self.assertEqual(AKIMBO_PROFILES_BY_TYPE["light_pistol"][2]["weapon_type"], "light_pistol_akimbo")


class TwoRealItemsAreOneAttack(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.species = "human"
        self.char2.db.species = "human"

    def _held(self, proto, hand):
        item = spawn(proto)[0]
        item.location = self.char1
        self.char1.wield_item(item, hand)
        return item

    def test_two_model_6s_fire_as_a_pair(self):
        a = self._held("LIGHT_PISTOL", "left_hand")
        b = self._held("LIGHT_PISTOL", "right_hand")
        choice = choose_weapon(self.char1)
        self.assertEqual(set(choice.items), {a, b})
        self.assertEqual((choice.weapon_type, choice.damage, choice.hit_bonus), ("light_pistol_akimbo", 16, -1))

    def test_one_tiger_claw_then_two(self):
        self._held("TIGER_CLAWS", "left_hand")
        self.assertEqual(choose_weapon(self.char1).weapon_type, "tiger_claws")
        self._held("TIGER_CLAWS", "right_hand")
        choice = choose_weapon(self.char1)
        self.assertEqual((choice.weapon_type, choice.damage, choice.hit_bonus), ("tiger_claws_akimbo", 9, 1))

    def test_the_pair_bank_speaks_the_lead_pistols_name(self):
        from world.combat.messages import get_combat_message
        a = self._held("LIGHT_PISTOL", "left_hand")
        self._held("LIGHT_PISTOL", "right_hand")
        named = [e for e in _bank("light_pistol_akimbo")["hit"] if "{item_name}" in e["attacker_msg"]][0]
        with patch("world.combat.messages.random.choice", lambda seq: named if named in seq else seq[0]):
            out = get_combat_message("light_pistol_akimbo", "hit", attacker=self.char1, target=self.char2,
                                     item=a, hit_location="chest", damage=3, audiences=("actor",))
        self.assertIn("PAM Model 6 pistol", out["attacker_msg"])
        self.assertNotIn("{", out["attacker_msg"])
