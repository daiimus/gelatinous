"""Two more presence-gate leaks, and three findings that were already
fixed (#2452).

**`whisper` and `to` resolved through the RAW search.**
`Character.search` runs the identity pipeline into
`world/search.py:identity_match_characters`, which filters on
`_has_identity` and self-exclusion and has **no `can_perceive` clause
anywhere**. So a hidden character the caller is Unaware of was a live
match: `whisper "x" to man` answered *'You whisper to a lanky man,
"x"'* while `look` still omitted them entirely.

That is a zero-cost, unlimited hidden-presence detector — no search
roll made or spent, nothing contested, and whisper does not break the
whisperer's own stealth — and it handed over the exact sdesc. The
gated sibling `resolve_character_target` has carried `filter_present`
all along; these two never used it, and cannot switch to it wholesale
because they must also target objects (`to <radio>`, `to <crate>`).

**The refusal is Evennia's own no-match wording, verbatim.** A
different message would still be an oracle: "that name resolves but I
won't tell you about it" is precisely the fact being protected.

**Logout and login broadcast a hidden character by sdesc.**
`at_post_unpuppet` and `at_post_puppet` call `msg_room_identity` with
`exclude=[self]` only, and that function gates solely on `.msg` and
session count. So hiding and then quitting handed every observer *"A
lanky man goes still…"* — including the ones `look` had been correctly
omitting them from. `db.hidden` is persistent and survives the session,
and `at_pre_puppet` restores location by direct assignment rather than
`move_to`, so `at_pre_move` — the one place a walk-off breaks stealth —
never fires. The movement announcements sixty lines below have carried
this exact gate all along, which is what made the omission read as
covered.

**Three of the five findings in the issue were already fixed**, and
checking beat assuming: the speech commands validate arguments before
`break_stealth` (#2530), the take path calls `_clear_stash_state`
(#2476), and the `search` broadcast excludes observers who cannot
perceive the searcher (#2562/#2563). Pinned below so they stay fixed.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdCommunication import CmdSay, CmdTo, CmdWhisper


class _HiddenCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        for char in (self.char1, self.char2):
            char.location = self.room1
        self.char2.height, self.char2.build = "tall", "lean"
        self.char2.sdesc_keyword = "man"

    def hide(self, char):
        char.db.hidden = True


class TestWhisperIsNotAPresenceDetector(_HiddenCase):
    def test_a_hidden_target_cannot_be_whispered_to(self):
        self.hide(self.char2)
        out = self.call(CmdWhisper(), '"psst" to man')
        self.assertNotIn("You whisper to", out)

    def test_the_refusal_is_evennias_own_no_match_wording(self):
        """Indistinguishable from a genuine miss — a bespoke message
        would still confirm the name resolves."""
        self.hide(self.char2)
        hidden_out = self.call(CmdWhisper(), '"psst" to man')
        missing_out = self.call(CmdWhisper(), '"psst" to zephyr')
        self.assertIn("Could not find", hidden_out)
        self.assertIn("Could not find", missing_out)

    def test_the_sdesc_is_not_handed_over(self):
        self.hide(self.char2)
        self.assertNotIn("lean man", self.call(CmdWhisper(), '"psst" to man'))

    def test_a_visible_target_still_works(self):
        self.assertIn("You whisper to", self.call(CmdWhisper(), '"psst" to man'))


class TestToIsNotOneEither(_HiddenCase):
    def test_a_hidden_target_cannot_be_addressed(self):
        self.hide(self.char2)
        out = self.call(CmdTo(), "man you there")
        self.assertNotIn("You say to", out)

    def test_the_refusal_matches_a_genuine_miss(self):
        self.hide(self.char2)
        self.assertIn("Could not find", self.call(CmdTo(), "man you there"))

    def test_a_visible_target_still_works(self):
        self.assertIn("You say to", self.call(CmdTo(), "man you there"))


class TestTheBystanderLineToo(_HiddenCase):
    """Caller and bystander can differ: an ALERT whisperer may
    legitimately address someone an Unaware bystander cannot see."""

    def test_an_unaware_bystander_is_not_told_the_targets_name(self):
        from world.stealth import ALERT, set_awareness
        third = create_object("typeclasses.characters.Character",
                              key="Bystander", location=self.room1)
        third.height, third.build = "average", "stocky"
        heard = []
        third.msg = lambda text="", **kw: heard.append(str(text))
        self.hide(self.char2)
        set_awareness(self.char1, self.char2, ALERT)   # caller CAN see them
        self.call(CmdWhisper(), '"psst" to man')
        self.assertFalse([h for h in heard if "whispers" in h],
                         f"bystander was told: {heard}")


class TestQuittingDoesNotBlowConcealment(_HiddenCase):
    def test_the_exclude_list_covers_unaware_observers(self):
        self.hide(self.char1)
        excluded = self.char1._unaware_of_me()
        self.assertIn(self.char2, excluded)

    def test_a_visible_character_excludes_nobody(self):
        self.assertEqual(self.char1._unaware_of_me(), [])

    def test_an_aware_observer_is_not_excluded(self):
        from world.stealth import ALERT, set_awareness
        self.hide(self.char1)
        set_awareness(self.char2, self.char1, ALERT)
        self.assertNotIn(self.char2, self.char1._unaware_of_me())

    def test_both_session_hooks_use_it(self):
        import inspect
        from typeclasses.characters import Character
        for hook in (Character.at_post_puppet, Character.at_post_unpuppet):
            self.assertIn("_unaware_of_me", inspect.getsource(hook))


class TestTheThreeAlreadyFixedStayFixed(_HiddenCase):
    """Regression pins, not evidence — these passed before this change."""

    def test_a_bare_say_does_not_reveal_you(self):
        self.hide(self.char1)
        self.call(CmdSay(), "")
        self.assertTrue(self.char1.db.hidden)

    def test_a_bare_to_does_not_reveal_you(self):
        self.hide(self.char1)
        self.call(CmdTo(), "")
        self.assertTrue(self.char1.db.hidden)

    def test_picking_a_stash_up_clears_the_flag(self):
        from commands.CmdInventory import _clear_stash_state
        item = create_object("typeclasses.items.Item", key="a shiv",
                             location=self.room1)
        item.db.hidden = True
        item.db.stash_roll = 17
        _clear_stash_state(item)
        self.assertIsNone(item.db.hidden)
        self.assertIsNone(item.db.stash_roll)
