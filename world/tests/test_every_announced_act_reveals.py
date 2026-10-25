"""#3769 -- every act a hidden character announces to the room reveals them.

The core of #3659. Owner, 2026-10-24, on the audit of 234 room
announcements: changing clothes, eating or treating yourself, picking up
or dropping, aiming, following, throwing, pulling a pin and wielding all
reveal; whisper and sneak are the only quiet acts. So the rule lives in
`msg_room_identity`: the referent of each ``acting`` placeholder (the
``actor`` by default) is revealed before the line renders, and the
emergence beat lands first. Announcements that are not acts (collapsing,
dying, a garment tearing, falling, a bleed) pass ``acting=()``. `wield`
announces nothing and reveals on its own.

char2 hides; char1 watches, Unaware.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdFollow import CmdFollow, CmdStopFollowing
from commands.CmdInventory import CmdDrop, CmdGet, CmdWield
from commands.CmdStealth import CmdSearch
from world.identity_utils import msg_room_identity
from world.perception import can_perceive
from world.stealth import UNAWARE, set_awareness


class _Hidden(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.heard = []
        self.char1.msg = lambda text=None, **kw: self.heard.append(
            str(text[0] if isinstance(text, tuple) else text))
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, UNAWARE)
        self.assertFalse(can_perceive(self.char1, self.char2), "premise")

    def as_player(self, cmd, args):
        return self.call(cmd, args, caller=self.char2) or ""

    def thing(self, key, location=None):
        return create_object("typeclasses.items.Item", key=key,
                             location=location or self.char2)


class TestTheAnnouncerReveals(_Hidden):

    def test_an_announced_act_reveals_the_actor(self):
        msg_room_identity(location=self.room1, template="{actor} whistles.",
                          char_refs={"actor": self.char2}, exclude=[self.char2])
        self.assertFalse(self.char2.db.hidden)

    def test_the_emergence_beat_lands_before_the_line(self):
        """Read through an NPC watcher: the announcer renders only for a
        session or a class-level at_msg_receive, which LLMNpc has."""
        heard = []
        npc = create_object("typeclasses.llm_npc.LLMNpc", key="a watcher",
                            location=self.room1)
        npc.msg = lambda text=None, **kw: heard.append(
            str(text[0] if isinstance(text, tuple) else text))
        set_awareness(npc, self.char2, UNAWARE)
        msg_room_identity(location=self.room1, template="{actor} whistles.",
                          char_refs={"actor": self.char2}, exclude=[self.char2])
        joined = "\n".join(heard)
        self.assertIn("emerges from concealment", joined)
        self.assertIn("whistles", joined)
        self.assertLess(joined.index("emerges from concealment"),
                        joined.index("whistles"), joined)

    def test_a_non_act_leaves_the_hide(self):
        msg_room_identity(location=self.room1, template="{actor} bleeds.",
                          char_refs={"actor": self.char2}, exclude=[self.char2],
                          acting=())
        self.assertTrue(self.char2.db.hidden)

    def test_a_named_actor_is_revealed(self):
        msg_room_identity(location=self.room1, template="{surgeon} cuts.",
                          char_refs={"surgeon": self.char2}, exclude=[self.char2],
                          acting=("surgeon",))
        self.assertFalse(self.char2.db.hidden)

    def test_a_hidden_non_actor_reference_is_left_alone(self):
        """Being referred to is not acting: the hit rule and the identity
        gate own those cases."""
        msg_room_identity(location=self.room1,
                          template="{actor} glances toward {target}.",
                          char_refs={"actor": self.char1, "target": self.char2},
                          exclude=[self.char1])
        self.assertTrue(self.char2.db.hidden)


class TestTheVerbsTheOwnerRuledOn(_Hidden):

    def test_drop(self):
        self.thing("brass coin")
        self.as_player(CmdDrop(), "coin")
        self.assertFalse(self.char2.db.hidden)

    def test_get(self):
        self.thing("brass coin", location=self.room1)
        self.as_player(CmdGet(), "coin")
        self.assertFalse(self.char2.db.hidden)

    def test_wield_announces_nothing_and_still_reveals(self):
        knife = self.thing("rusty knife")
        self.char2.hands = {"left_hand": None, "right_hand": None}
        self.as_player(CmdWield(), "knife")
        self.assertIn(knife, self.char2.hands.values(), "premise: the wield took")
        self.assertFalse(self.char2.db.hidden)

    def test_a_failed_wield_does_not(self):
        self.as_player(CmdWield(), "nothing")
        self.assertTrue(self.char2.db.hidden)

    def test_follow(self):
        out = self.as_player(CmdFollow(), self.char1.key)
        self.assertIn("fall in behind", out, out)
        self.assertFalse(self.char2.db.hidden)

    def test_the_leader_hears_the_emergence_before_the_follow(self):
        heard = []
        self.char1.msg = lambda text=None, **kw: heard.append(
            str(text[0] if isinstance(text, tuple) else text))
        self.as_player(CmdFollow(), self.char1.key)
        joined = "\n".join(heard)
        self.assertLess(joined.index("emerges from concealment"),
                        joined.index("falls in behind you"), joined)

    def test_stop_following_is_the_players_act_and_reveals(self):
        self.char2.db.hidden = False
        self.as_player(CmdFollow(), self.char1.key)
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, UNAWARE)
        self.as_player(CmdStopFollowing(), "")
        self.assertFalse(self.char2.db.hidden)
        self.assertIsNone(self.char2.db.following)

    def test_a_refused_re_wield_does_not(self):
        knife = self.thing("rusty knife")
        self.char2.hands = {"left_hand": knife, "right_hand": None}
        self.as_player(CmdWield(), "knife in left")
        self.assertTrue(self.char2.db.hidden)

    def test_a_disguise_change_reveals_off_the_announcers_path(self):
        """Wearing or removing a disguise item broadcasts through
        world.identity, not the announcer; the act still reveals."""
        from world.identity import _broadcast_unmask_with_action
        _broadcast_unmask_with_action(
            self.char2, "uid-a", "uid-b",
            action_template="{actor} pulls on a mask.",
            action_char_refs={"actor": self.char2},
            action_pre_resolved_refs={}, action_exclude=[self.char2])
        self.assertFalse(self.char2.db.hidden)


class TestWhatStaysQuiet(_Hidden):

    def test_search_reveals(self):
        """Owner, 2026-10-25: "Search reveals", superseding #2562's quiet
        searcher; so it is in the loud list, not this one."""
        self.as_player(CmdSearch(), "")
        self.assertFalse(self.char2.db.hidden)

    def test_a_move_announcement_is_not_an_act_here(self):
        """Open movement breaks the hide in at_post_move already; a sneak
        must not be revealed by the arrival line. The line itself passes
        acting=(), so the hide is the mover's business, not the room's."""
        msg_room_identity(location=self.room1,
                          template="{actor} arrives to here from there.",
                          char_refs={"actor": self.char2}, exclude=[self.char2],
                          acting=())
        self.assertTrue(self.char2.db.hidden)
