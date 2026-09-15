"""A combat handler survives a room deleted out from under it (#3520).

A handler that outlived a deleted room carried ``None`` in
``db.managed_rooms``; every round its debug line -- ``[r.key for r in
managed_rooms]`` -- crashed BEFORE the "no valid combatants, stopping"
check, so the script tracebacked every six seconds for ever, and a new
attack that merged into it crashed the same way and never started.
``live_rooms()`` is now the one reader: dead rooms are pruned and the
pruned list written back.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.handler import get_or_create_combat
from world.combat.utils import add_combatant


class ADeletedRoomDoesNotCrashAFightTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.gone = create_object("typeclasses.rooms.Room", key="doomed room")
        self.handler = get_or_create_combat(self.room1)
        self.handler.enroll_room(self.gone)
        add_combatant(self.handler, self.char1, target=self.char2)
        add_combatant(self.handler, self.char2, target=self.char1)
        self.gone.delete()                      # the fight now spans a room that no longer exists

    def test_live_rooms_prunes_the_dead_room_and_writes_back(self):
        self.assertEqual(self.handler.live_rooms(), [self.room1])
        self.assertEqual(list(self.handler.db.managed_rooms), [self.room1])

    def test_a_round_still_runs(self):
        try:
            self.handler.at_repeat()
        except AttributeError as exc:  # the old failure: 'NoneType' object has no attribute 'key'
            self.fail(f"the round crashed on the dead room: {exc}")

    def test_enrolling_nothing_is_a_no_op(self):
        before = list(self.handler.live_rooms())
        self.handler.enroll_room(None)
        self.assertEqual(list(self.handler.db.managed_rooms), before)

    def test_merging_a_handler_with_a_dead_room_keeps_only_the_living(self):
        other = get_or_create_combat(self.room2)
        other.db.managed_rooms = [self.room2, None]
        self.handler.merge_handler(other)
        self.assertEqual(sorted(r.key for r in self.handler.live_rooms()), sorted([self.room1.key, self.room2.key]))
