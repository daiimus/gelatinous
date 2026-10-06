"""The hands view iterates in the body's own order (MULTI_WEAPON_COMBAT_SPEC
§6, §11; owner ruling §14 #8): the species' anatomical display order, left
hand first, then unlisted slots alphabetically. The wheel, wield, get and
disarm all read this order, so nothing hashes it.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest

from world.combat.constants import NDB_LAST_WEAPON_SLOT


class TheOrder(EvenniaTest):

    def test_a_human_lists_the_left_hand_first(self):
        self.char1.db.species = "human"
        self.assertEqual(list(self.char1.hands), ["left_hand", "right_hand"])

    def test_an_unlisted_slot_sorts_after_the_listed_ones_alphabetically(self):
        self.char1.db.species = "human"
        self.assertEqual(self.char1.slot_order({"tail", "right_hand", "antenna", "left_hand"}),
                         ["left_hand", "right_hand", "antenna", "tail"])


class TheCursorClearsWithCombatState(EvenniaTest):

    def test_cleanup_drops_the_wheels_cursor(self):
        from world.combat.utils import cleanup_combatant_state
        setattr(self.char1.ndb, NDB_LAST_WEAPON_SLOT, "right_hand")
        handler = mock.MagicMock()
        handler.db.combatants = [{"char": self.char1}]
        cleanup_combatant_state(self.char1, {"char": self.char1}, handler)
        # an ndb miss answers None, so ask for the value, not for the attribute
        self.assertIsNone(getattr(self.char1.ndb, NDB_LAST_WEAPON_SLOT, None))


class TheDefaultHandIsTheFirstListed(EvenniaCommandTest):
    """Every picker reads the hands view, so the default hand follows its
    order (owner ruling §14 #8: species display order, no dominant hand)."""

    def test_wield_and_get_land_in_the_left_hand_first(self):
        from evennia import create_object
        from commands.CmdInventory import CmdGet, CmdWield
        self.char1.db.species = "human"
        knife = create_object("typeclasses.items.Item", key="knife", location=self.char1)
        knife.tags.add("weapon", category="type")
        self.call(CmdWield(), "knife", caller=self.char1)
        self.assertEqual(self.char1.hands.get("left_hand"), knife)
        self.assertIsNone(self.char1.hands.get("right_hand"))
        bottle = create_object("typeclasses.items.Item", key="bottle", location=self.room1)
        self.call(CmdGet(), "bottle", caller=self.char1)
        self.assertEqual(self.char1.hands.get("right_hand"), bottle, "the second item did not take the next hand")
