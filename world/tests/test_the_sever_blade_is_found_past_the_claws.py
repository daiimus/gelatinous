"""The sever verb's blade comes through the one door, read before natural
precedence (MULTI_WEAPON_COMBAT_SPEC §4): deployed claws do not hide a
held blade, claws themselves do not sever, and with nothing that cuts the
first option is named so the dull-blade line has a subject.
"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from commands.forensics import _blade_in_hand


class _Tags:
    def has(self, key, category=None):
        return key == "weapon" and category == "type"


def _item(key, can_sever=None, damage=5):
    return SimpleNamespace(key=key, tags=_Tags(),
                           db=SimpleNamespace(is_ranged=False, damage=damage, weapon_type=key,
                                              damage_type="cut", hit_bonus=None, can_sever=can_sever))


def _caller(**hands):
    return SimpleNamespace(hands=hands, location=object(), ndb=SimpleNamespace())


class TheBladePastTheClaws(TestCase):

    def test_a_held_blade_is_found_while_the_claws_are_out(self):
        sword = _item("sword", can_sever=True)
        claws = _item("carbide blades")
        with patch("world.medical.augments.get_active_natural_weapons", return_value=[("left_hand", claws)]):
            self.assertIs(_blade_in_hand(_caller(left_hand=None, right_hand=sword)), sword)

    def test_claws_alone_are_named_but_do_not_sever(self):
        claws = _item("carbide blades")
        with patch("world.medical.augments.get_active_natural_weapons", return_value=[("left_hand", claws)]):
            self.assertIs(_blade_in_hand(_caller(left_hand=None)), claws)

    def test_a_dull_held_weapon_is_named_for_the_refusal(self):
        club = _item("club", can_sever=False)
        with patch("world.medical.augments.get_active_natural_weapons", return_value=[]):
            self.assertIs(_blade_in_hand(_caller(right_hand=club)), club)

    def test_empty_hands_give_nothing(self):
        with patch("world.medical.augments.get_active_natural_weapons", return_value=[]):
            self.assertIsNone(_blade_in_hand(_caller()))
