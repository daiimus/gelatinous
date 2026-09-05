"""A pose renders for people, not for crates (#2788).

`if not hasattr(observer, "msg"): continue` appeared three times in
`world/emote.py` and excluded NOTHING -- every typeclassed Evennia
object has `.msg`, so the guard was always true and the loop body ran
for every item, corpse and organ in the room. It read as a safety
filter, which is why it survived review.

Not free: those loops call `render_for_observer` and `speech_payload`
PER observer. Measured across the live world, 1,961 of 2,037 objects
standing in rooms are not characters.

The fix is NOT the session gate `world/identity_utils.py` uses beside
its own copy of this check (#462). NPCs have no session, and an
action-aware NPC reacting to a pose aimed at it is deliberate -- the
call sites say so. `Character` is the predicate that keeps them.
"""
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world import emote


class TestPerceivers(EvenniaCommandTest):
    def test_an_item_in_the_room_is_not_a_perceiver(self):
        item = create_object("typeclasses.items.Item", key="a crate",
                             location=self.room1)
        self.assertNotIn(item, emote._perceivers(self.room1))

    def test_a_player_character_is_a_perceiver(self):
        self.char1.location = self.room1
        self.assertIn(self.char1, emote._perceivers(self.room1))

    def test_an_npc_with_no_session_is_still_a_perceiver(self):
        """The load-bearing case. A session gate would drop every NPC,
        and an NPC reacting to a pose directed at it is the point."""
        npc = create_object("typeclasses.characters.Character",
                            key="an NPC", location=self.room1)
        npc.db.is_npc = True
        self.assertFalse(npc.sessions.count(), "fixture has a session")
        self.assertIn(npc, emote._perceivers(self.room1))

    def test_a_corpse_is_not_a_perceiver(self):
        corpse = create_object("typeclasses.corpse.Corpse", key="a corpse",
                               location=self.room1)
        self.assertNotIn(corpse, emote._perceivers(self.room1))

    def test_the_exclude_set_is_honoured(self):
        self.char1.location = self.room1
        self.char2.location = self.room1
        out = emote._perceivers(self.room1, {self.char1})
        self.assertNotIn(self.char1, out)
        self.assertIn(self.char2, out)

    def test_it_filters_the_bulk_of_a_cluttered_room(self):
        """The shape of the live world: mostly things, not people."""
        for n in range(12):
            create_object("typeclasses.items.Item", key=f"item {n}",
                          location=self.room1)
        self.char1.location = self.room1
        contents = len(self.room1.contents)
        perceivers = len(emote._perceivers(self.room1))
        self.assertGreater(contents, perceivers)
        self.assertEqual(perceivers,
                         sum(1 for o in self.room1.contents
                             if hasattr(o, "is_dead")))

    def test_the_old_guard_would_have_excluded_nothing(self):
        """Pins the premise: every object in a room has `.msg`, so the
        guard this replaced could never filter anything."""
        create_object("typeclasses.items.Item", key="a crate",
                      location=self.room1)
        create_object("typeclasses.corpse.Corpse", key="a corpse",
                      location=self.room1)
        self.assertTrue(all(hasattr(o, "msg")
                            for o in self.room1.contents))
