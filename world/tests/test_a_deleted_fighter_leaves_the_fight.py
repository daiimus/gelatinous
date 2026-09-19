"""A deleted fighter leaves the fight before their row goes stale (#3555).

Deleting a character mid-fight left a combat row whose character read back
as None. The round tick pruned it, but inside that round any removal that
retargeted (a flee, a jump, a kill) walked the row and dereferenced the
missing character. Two fixes: Character.at_object_delete leaves every fight
through remove_combatant (the #3552 delete-hook pattern), and the retarget
candidate scan skips a row whose character is gone, as its two sibling
loops always did.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import DB_CHAR, DB_TARGET_DBREF
from world.combat.handler import get_or_create_combat
from world.combat.utils import add_combatant


class DeletedFighterLeavesTheFightTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.alpha = create_object("typeclasses.characters.Character", key="Alpha", location=self.room1)
        self.bravo = create_object("typeclasses.characters.Character", key="Bravo", location=self.room1)
        self.charlie = create_object("typeclasses.characters.Character", key="Charlie", location=self.room1)
        self.handler = get_or_create_combat(self.room1)
        add_combatant(self.handler, self.alpha, target=self.bravo)
        add_combatant(self.handler, self.bravo, target=self.alpha)
        add_combatant(self.handler, self.charlie, target=self.alpha)

    def _rows(self):
        return [(e.get(DB_CHAR).key if e.get(DB_CHAR) else None, e.get(DB_TARGET_DBREF))
                for e in (self.handler.db.combatants or [])]

    def _ghost_row(self):
        # What a deletion without the hook leaves behind: the stored entry
        # with its character deserialised to nothing.
        rows = self.handler.db.combatants
        for e in rows:
            if e.get(DB_CHAR) == self.charlie:
                e[DB_CHAR] = None
        self.handler.db.combatants = rows

    # --- the guard --------------------------------------------------------------

    def test_control_a_live_removal_retargets_without_a_ghost(self):
        self.handler.remove_combatant(self.alpha)
        names = [n for n, _ in self._rows()]
        self.assertNotIn("Alpha", names)
        self.assertIn("Bravo", names)

    def test_a_ghost_row_does_not_crash_the_retarget_scan(self):
        self._ghost_row()
        # Bravo (live, not yielding) targets Alpha; Alpha leaves as a flee would.
        # The candidate scan walks Charlie's ghost row.
        self.handler.remove_combatant(self.alpha)
        names = [n for n, _ in self._rows()]
        self.assertNotIn("Alpha", names)
        self.assertIn("Bravo", names)

    # --- the hook -----------------------------------------------------------------

    def test_deleting_a_fighter_removes_their_row_at_once(self):
        # Bravo also targets Charlie so someone is released by the deletion.
        self.handler.set_target(self.bravo, self.charlie)
        with patch.object(self.bravo, "msg") as told:
            self.assertTrue(self.charlie.delete())
        rows = self._rows()
        self.assertNotIn("Charlie", [n for n, _ in rows], rows)
        self.assertNotIn(None, [n for n, _ in rows], "a deserialised-to-None row was left behind: %r" % rows)
        # Released through the ordinary door: Alpha is still targeting Bravo,
        # so Bravo is re-pointed at Alpha and gets the wind-up line at once,
        # not a "choose a new target" a round later.
        bravo = next(t for n, t in rows if n == "Bravo")
        self.assertEqual(bravo, self.handler._get_dbref(self.alpha), "Bravo was not re-pointed at the live attacker")
        self.assertTrue(told.call_args_list, "the attacker was told nothing at delete time")

    # --- regression guards: true on both trees, kept so they stay true ---------

    def test_guard_the_round_after_a_deletion_runs_clean(self):
        # On the old tree the round tick pruned the ghost row itself; on the
        # new tree there is no ghost to prune. Same end state either way.
        self.assertTrue(self.charlie.delete())
        self.handler.at_repeat()
        self.assertNotIn(None, [n for n, _ in self._rows()])

    def test_guard_deleting_a_character_not_in_combat_is_a_no_op(self):
        bystander = create_object("typeclasses.characters.Character", key="Delta", location=self.room2)
        self.assertTrue(bystander.delete())
        self.assertEqual(len(self._rows()), 3)
