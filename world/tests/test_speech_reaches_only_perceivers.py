"""A spoken line renders for people, not for crates (#3420).

`if not hasattr(observer, "msg"): continue` guarded the say/`to` loop
in `world/speech.py` and whisper's bystander loop in
`commands/CmdCommunication.py`, and excluded NOTHING -- every
typeclassed Evennia object has `.msg`, so each line was rendered,
perception-checked and stealth-adjudicated once per item, corpse and
organ in the room. Poses were fixed the same way in #2788; the
predicate now lives in `world.perception` so the two cannot drift.

Measured in the live world before the fix: ~2 ms per object for a say
and ~4 ms per object for a whisper, person or not.

Same discipline as the pose test: the filter is NOT a session gate.
A session-less NPC still receives speech, because action-aware NPCs
answering what is said to them is the point.
"""
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world import speech


def _recorder(sink):
    """A real `def`, not a Mock: some audience gates inspect callables."""
    def msg(text=None, **kwargs):
        sink.append((text, kwargs))
    return msg


class _RoomWithThings(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.item = create_object("typeclasses.items.Item", key="a crate",
                                  location=self.room1)
        self.corpse = create_object("typeclasses.corpse.Corpse",
                                    key="a corpse", location=self.room1)
        self.npc = create_object("typeclasses.characters.Character",
                                 key="Bystander", location=self.room1)
        self.assertFalse(self.npc.sessions.count(), "fixture has a session")
        self.heard = {}
        for name, thing in (("item", self.item), ("corpse", self.corpse),
                            ("npc", self.npc), ("char2", self.char2)):
            self.heard[name] = []
            thing.msg = _recorder(self.heard[name])


class TestSayReachesOnlyPerceivers(_RoomWithThings):
    def _say(self):
        speech.broadcast_speech(self.char1, "hello there", self.room1)

    def test_a_crate_is_not_rendered_for(self):
        self._say()
        self.assertEqual(self.heard["item"], [])

    def test_a_corpse_is_not_rendered_for(self):
        self._say()
        self.assertEqual(self.heard["corpse"], [])

    def test_a_session_less_npc_still_hears(self):
        self._say()
        self.assertEqual(len(self.heard["npc"]), 1)
        self.assertEqual(self.heard["npc"][0][1].get("type"), "say")

    def test_a_character_still_hears(self):
        self._say()
        self.assertEqual(len(self.heard["char2"]), 1)

    def test_the_speaker_is_still_excluded(self):
        mine = []
        self.char1.msg = _recorder(mine)
        self._say()
        self.assertEqual(mine, [])


class TestWhisperBystandersAreOnlyPerceivers(_RoomWithThings):
    def _whisper(self):
        from commands.CmdCommunication import CmdWhisper
        cmd = CmdWhisper()
        cmd.caller = self.char1
        cmd.args = ' "psst" to Char2'
        cmd.cmdstring = "whisper"
        cmd.parse()
        with patch.object(self.char1, "search", return_value=self.char2):
            cmd.func()

    def test_a_crate_is_not_a_bystander(self):
        self._whisper()
        self.assertEqual(self.heard["item"], [])

    def test_a_corpse_is_not_a_bystander(self):
        self._whisper()
        self.assertEqual(self.heard["corpse"], [])

    def test_a_session_less_npc_sees_the_lean_in(self):
        self._whisper()
        self.assertEqual(len(self.heard["npc"]), 1)
        self.assertEqual(self.heard["npc"][0][1].get("type"), "whisper")
        self.assertIn("whispers something to", str(self.heard["npc"][0][0]))

    def test_the_target_gets_the_words_not_the_lean_in(self):
        self._whisper()
        self.assertEqual(len(self.heard["char2"]), 1)
        self.assertIn("psst", str(self.heard["char2"][0][0]))


class TestThePremise(EvenniaCommandTest):
    def test_there_is_one_name_for_the_predicate(self):
        """No second door (#3530): neither emote nor radio carries an alias
        or a wrapper; every audience imports `world.perception` directly."""
        from world import emote, radio
        for mod in (emote, radio):
            self.assertFalse(hasattr(mod, "_perceivers"), mod.__name__)
            self.assertFalse(hasattr(mod, "_perceives"), mod.__name__)

    def test_the_old_guard_would_have_excluded_nothing(self):
        create_object("typeclasses.items.Item", key="a crate",
                      location=self.room1)
        self.assertTrue(all(hasattr(o, "msg") for o in self.room1.contents))
