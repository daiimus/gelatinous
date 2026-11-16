"""An AI NPC that forgets somebody also forgets a look it knew only by
seeing through it to them (#3859).

An NPC that knows a person can come to hold records about a disguised
look of that person in three ways:

1. it watched the mask go on. The masked look has an unnamed entry in
   its memory that answers to the person's name. Forgetting the person
   erases that entry too (#3825), and what the NPC filed under the
   masked look goes with it (#3841, #3851);
2. it saw through the mask. The masked look has no entry, only a won
   see-through. Forgetting the person dropped the see-through and left
   everything filed under the masked look: the NPC went on holding a
   grudge against a masked stranger it could no longer place;
3. it gave the masked look a name of its own. The look stays.

The owner was shown the three, with an NPC that is hit by the masked
figure and later made to forget the person, and asked: "Do you agree
with changing case 2 and leaving case 3?" Owner, 2026-11-16: "Yeah,
your assessment is solid."

So `world.identity.erase_look` now also reports, to an observer that
keeps records of its own, the looks it held no entry for and knew only
by a see-through that has just gone. A reply to such a look that is
still being made when the NPC forgets is not written down under it
(`typeclasses.llm_npc._forgotten_since`). This module is case 2, with
cases 1 and 3 beside it as controls. Case 3 with a watched mask is in
`test_an_npc_that_forgets_loses_its_read`.

The NPC is made by the test and types the real `forget`. The see-through
is made the way the game makes it: the masked figure is shown to the
NPC by name (`get_display_name`), with the dice fixed. Every "is gone"
has a control beside it: the same thing is there before, and the same
thing held about ANOTHER person, or about a look the NPC did NOT see
through, is there after.
"""
from types import SimpleNamespace
from unittest import TestCase, mock

from evennia.prototypes.spawner import spawn

from typeclasses.llm_npc import _forgets_so_far, _forgotten_since
from world.identity import erase_look, get_apparent_uid, get_assigned_name
from world.souls import thoughts
from world.tests.test_an_npc_that_forgets import ALL, NONE
from world.tests.test_an_npc_that_forgets_loses_its_read import (
    FRIENDLY, HOSTILE, _SullyHasASoul)

ROLL = "world.combat.dice.opposed_roll"
WON, LOST = (20, 1, True), (1, 20, False)

#: What `filed_under` reports for a look the NPC talked with and never
#: named: no alias, and the talk and the thread.
TALK = {"alias": False, "memory": True, "thread": True}


class _MothComesBackMasked(_SullyHasASoul):
    """Sully knows Moth and knows Wren. Moth goes out, puts a mask on
    where Sully cannot see it, and comes back. `DICE` says whether
    Sully sees through the mask when he is first shown the masked
    figure. The masked figure orders a drink and then hits him."""

    DICE = WON

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.name(self.other, "Wren")
        self.wren = get_apparent_uid(self.other)
        self.talk(self.other, "a clean glass")
        self.thanked_by(self.other)
        self.masked = self.comes_back_wearing("ski mask")
        self.seen_as = self.shown_to_sully()
        self.talk(self.patron, "a rotgut")
        self.attacked_by(self.patron)
        self.mood_before = self.mood_log()

    # ---- staging

    def unseen(self, command):
        self.patron.move_to(self.room2, quiet=True, move_hooks=False)
        self.patron.execute_cmd(command)
        self.patron.move_to(self.room1, quiet=True, move_hooks=False)

    def comes_back_wearing(self, garment):
        self.unseen(f"wear {garment}")
        look = get_apparent_uid(self.patron)
        self.assertNotEqual(look, self.bare)
        self.assertNotIn(look, self.npc.recognition_memory)
        return look

    def shown_to_sully(self, dice=None):
        """The name the room shows Sully for the figure in front of
        him. The first time, this is where the see-through is rolled."""
        with mock.patch(ROLL, return_value=dice or self.DICE):
            return self.patron.get_display_name(self.npc)

    def leaves(self):
        self.patron.move_to(self.room2, quiet=True, move_hooks=False)

    # ---- reading

    def verdict(self, look):
        """True for a won see-through of *look*, False for a lost one,
        None when Sully holds neither."""
        cache = dict(self.npc.db.disguise_pierce_cache or {})
        return cache.get((self.patron.dbref, look))

    def shown_now(self):
        """The name the room shows Sully now, without rolling."""
        return self.patron.get_display_name(self.npc, decided_only=True)

    def masked_line(self, look=None):
        return self.npc._relationship_line(
            look or self.masked, self.patron) or ""

    def assert_wren_is_where_she_was(self):
        self.assertEqual(get_assigned_name(self.npc, self.other), "Wren")
        self.assertEqual(self.reasons(self.wren),
                         ["they were decent to me"] * 2)
        self.assertEqual(self.filed_under(self.wren), ALL)
        self.assertIn(FRIENDLY, self.who_line(self.other))


# ----------------------------------------------------------------------
# Before: the control every "is gone" below stands on
# ----------------------------------------------------------------------

class TestWhatSullyHoldsAboutTheMaskHeSawThrough(_MothComesBackMasked):
    def test_the_room_shows_him_moth(self):
        self.assertEqual(self.seen_as, "Moth")
        self.assertIs(self.verdict(self.masked), True)

    def test_the_masked_look_has_no_entry_of_its_own(self):
        self.assertNotIn(self.masked, self.npc.recognition_memory)
        self.assertIn(self.bare, self.npc.recognition_memory)

    def test_what_he_holds_is_filed_under_the_masked_look(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        self.assertEqual(self.reasons(self.bare), [])
        self.assertEqual(self.filed_under(self.masked), TALK)

    def test_the_talk_is_read_back(self):
        """The control for "there is no thread and nothing to
        recall" below."""
        (turn,) = self.thread(self.patron)
        self.assertIn("a rotgut", turn)
        self.assertIn("a rotgut", self.recalled(self.patron))

    def test_the_model_is_handed_it(self):
        self.assertIn(HOSTILE, self.masked_line())
        prompt = self.prompt(self.patron)
        self.assertIn(HOSTILE, prompt)
        self.assertIn("a rotgut", prompt)


# ----------------------------------------------------------------------
# Case 2: he forgets Moth
# ----------------------------------------------------------------------

class _SullyForgetsMoth:
    """Mixed in ahead of `_MothComesBackMasked`. `HOW` is the way the
    forgetting reaches `erase_look`:

    * ``"masked"``: the masked figure is in the room. `forget moth`
      finds them by the name Sully sees through to, and erases that
      name where it is stored;
    * ``"gone"``: they have left. `forget moth` finds the name in
      his memory;
    * ``"bare"``: they are in the room with the mask off again."""

    HOW = "masked"

    def setUp(self):
        super().setUp()
        if self.HOW == "gone":
            self.leaves()
        elif self.HOW == "bare":
            self.unseen("remove ski mask")
            self.assertEqual(get_apparent_uid(self.patron), self.bare)
        self.forget("moth")
        if self.HOW == "gone":
            self.patron.move_to(self.room1, quiet=True, move_hooks=False)
        elif self.HOW == "bare":
            self.unseen("wear ski mask")
            self.assertEqual(get_apparent_uid(self.patron), self.masked)

    def test_the_name_and_the_see_through_are_gone(self):
        """The control that `forget` ran, and what #3825 already did."""
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assertIsNone(self.verdict(self.masked))
        self.assertNotEqual(self.shown_now(), "Moth")

    def test_his_read_on_the_masked_look_went_with_it(self):
        self.assertNotIn(self.masked, thoughts._opinions(self.npc))
        self.assertEqual(thoughts.opinion_of(self.npc, self.masked), 0.0)

    def test_so_did_the_talk_and_the_thread(self):
        self.assertEqual(self.filed_under(self.masked), NONE)
        self.assertEqual(self.thread(self.patron), [])
        self.assertEqual(self.recalled(self.patron), "")

    def test_the_masked_figure_is_a_stranger_he_holds_nothing_against(self):
        self.assertEqual(self.masked_line(), "")

    def test_the_model_is_handed_none_of_it(self):
        prompt = self.prompt(self.patron)
        for words in ("your read on them", "put hands on me", "a rotgut"):
            self.assertNotIn(words, prompt)

    def test_the_mood_is_what_it_was(self):
        self.assertEqual(self.mood_log(), self.mood_before)

    def test_everything_about_wren_is_where_it_was(self):
        self.assert_wren_is_where_she_was()


class TestForgettingMothWithTheMaskedFigureInTheRoom(
        _SullyForgetsMoth, _MothComesBackMasked):
    HOW = "masked"


class TestForgettingMothAfterTheMaskedFigureLeft(
        _SullyForgetsMoth, _MothComesBackMasked):
    HOW = "gone"


class TestForgettingMothWithTheMaskOffAgain(
        _SullyForgetsMoth, _MothComesBackMasked):
    HOW = "bare"


class TestWhatTheMaskedFigureDoesNextStartsANewRead(_MothComesBackMasked):
    def setUp(self):
        super().setUp()
        self.forget("moth")
        self.attacked_by(self.patron)

    def test_it_is_held_against_a_stranger(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        line = self.masked_line()
        self.assertIn(HOSTILE, line)
        self.assertNotIn("Moth", line)


# ----------------------------------------------------------------------
# The side effect that was named when the ruling was asked for
# ----------------------------------------------------------------------

class TestWhatTheMaskDidBeforeHeSawThroughItGoesToo(_SullyHasASoul):
    """A masked stranger hits Sully. Later he meets the same person
    bare-faced and learns the name Moth; later still the masked figure
    comes back and he sees through the mask. Everything is filed under
    the masked look, the blow from before included, so forgetting Moth
    takes that too."""

    def setUp(self):
        super().setUp()
        self.patron.execute_cmd("wear ski mask")
        self.masked = get_apparent_uid(self.patron)
        self.attacked_by(self.patron)                # a stranger's blow
        self.assertNotIn(self.masked, self.npc.recognition_memory)
        self.assertEqual(self.npc.db.disguise_pierce_cache or {}, {})
        self.patron.move_to(self.room2, quiet=True, move_hooks=False)
        self.patron.execute_cmd("remove ski mask")
        self.patron.move_to(self.room1, quiet=True, move_hooks=False)
        self.name(self.patron, "Moth")
        self.patron.move_to(self.room2, quiet=True, move_hooks=False)
        self.patron.execute_cmd("wear ski mask")
        self.patron.move_to(self.room1, quiet=True, move_hooks=False)
        with mock.patch(ROLL, return_value=WON):
            self.assertEqual(self.patron.get_display_name(self.npc), "Moth")

    def test_before_he_forgets_the_blow_is_held_against_the_mask(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])

    def test_after_he_forgets_moth_it_is_not(self):
        self.forget("moth")
        self.assertNotIn(self.masked, thoughts._opinions(self.npc))


# ----------------------------------------------------------------------
# Controls: looks that do NOT go
# ----------------------------------------------------------------------

class TestAMaskHeFailedToSeeThroughKeepsItsRecords(_MothComesBackMasked):
    """The same evening with the dice the other way. Sully never
    connected the masked figure to Moth, so forgetting Moth takes
    nothing of what the masked figure did. The lost see-through stays
    lost (#3817)."""

    DICE = LOST

    def setUp(self):
        super().setUp()
        self.assertNotEqual(self.seen_as, "Moth")
        self.assertIs(self.verdict(self.masked), False)
        self.leaves()
        self.forget("moth")
        self.patron.move_to(self.room1, quiet=True, move_hooks=False)

    def test_moth_is_forgotten(self):
        self.assertNotIn(self.bare, self.npc.recognition_memory)

    def test_the_lost_see_through_is_still_lost(self):
        self.assertIs(self.verdict(self.masked), False)

    def test_what_the_masked_stranger_did_is_all_there(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        self.assertEqual(self.filed_under(self.masked), TALK)
        self.assertIn(HOSTILE, self.masked_line())
        thread = self.thread(self.patron)
        self.assertEqual(len(thread), 1)
        self.assertIn("a rotgut", thread[0])


class TestAMaskHeSawThroughAndThenNamedStays(_MothComesBackMasked):
    """Case 3. After the blow Sully gives the masked figure a name of
    its own, Ghost. The masked look now has an entry and a name, so
    forgetting Moth is not forgetting Ghost, and what the masked figure
    did before it had that name stays with it."""

    def setUp(self):
        super().setUp()
        with mock.patch(ROLL, side_effect=AssertionError("a roll was made")):
            self.name(self.patron, "Ghost")
            self.assertEqual(
                self.npc.recognition_memory[self.masked]["linked_to"],
                self.bare)
            self.forget("moth")

    def test_moth_went_and_ghost_did_not(self):
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Ghost")

    def test_the_see_through_to_moth_went(self):
        self.assertIsNone(self.verdict(self.masked))

    def test_ghost_is_still_held_to_what_the_masked_figure_did(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        line = self.masked_line()
        self.assertIn("you know them as 'Ghost'", line)
        self.assertIn(HOSTILE, line)
        self.assertNotIn("Moth", line)

    def test_the_talk_from_before_the_name_is_still_filed_under_it(self):
        filed = self.filed_under(self.masked)
        self.assertTrue(filed["memory"])
        self.assertTrue(filed["thread"])


class TestForgettingAnotherNameOfTheirsLeavesTheMask(_MothComesBackMasked):
    """Sully holds two names for the same person: Moth for the face,
    and Hood for a hooded look he saw through and then named. The mask
    he saw through stands on Moth, the first name he held. Forgetting
    Hood is not forgetting Moth: the see-through of the mask stays, and
    so does everything filed under the masked look."""

    def setUp(self):
        super().setUp()
        spawn("HOODIE_HOOD_UP")[0].move_to(self.patron, quiet=True)
        self.unseen("remove ski mask")
        self.hooded = self.comes_back_wearing("hood")
        self.assertEqual(self.shown_to_sully(WON), "Moth")
        self.name(self.patron, "Hood")
        self.unseen("remove hood")
        self.unseen("wear ski mask")
        self.assertEqual(get_apparent_uid(self.patron), self.masked)
        self.assertEqual(
            sorted(look for look in (self.masked, self.hooded)
                   if self.verdict(look)),
            sorted([self.masked, self.hooded]))
        self.leaves()
        self.forget("hood")
        self.patron.move_to(self.room1, quiet=True, move_hooks=False)

    def test_hood_went_and_moth_did_not(self):
        memory = self.npc.recognition_memory
        self.assertNotIn(self.hooded, memory)
        self.assertEqual(memory[self.bare]["assigned_name"], "Moth")

    def test_he_still_sees_through_the_mask(self):
        self.assertIs(self.verdict(self.masked), True)
        self.assertEqual(self.shown_now(), "Moth")

    def test_what_the_masked_figure_did_is_all_there(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        self.assertEqual(self.filed_under(self.masked), TALK)
        self.assertIn(HOSTILE, self.masked_line())


class TestAMaskHeHoldsABlankEntryForIsLeftAlone(_MothComesBackMasked):
    """Not part of the ruling. This is what the code does, pinned so
    that a change to it is made on purpose.

    The `forget` of before #3825 blanked a name and kept the entry.
    Such entries are still in live memories; they are not migrated, and
    are not swept up when some other name is forgotten. A look that has
    one is still in the NPC's memory, so it is not reported with a
    see-through that goes, and what is filed under it stays."""

    def setUp(self):
        super().setUp()
        memory = self.npc.recognition_memory
        memory[self.masked] = {"assigned_name": "",
                               "real_sleeve_uid": self.patron.sleeve_uid}
        self.npc.recognition_memory = memory
        self.assertEqual(self.shown_now(), "Moth")
        self.leaves()
        self.forget("moth")
        self.patron.move_to(self.room1, quiet=True, move_hooks=False)

    def test_the_see_through_went_and_the_blank_entry_did_not(self):
        memory = self.npc.recognition_memory
        self.assertNotIn(self.bare, memory)
        self.assertIsNone(self.verdict(self.masked))
        self.assertIn(self.masked, memory)

    def test_what_is_filed_under_its_look_stays(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        self.assertEqual(self.filed_under(self.masked), TALK)


# ----------------------------------------------------------------------
# A reply that is still being made
# ----------------------------------------------------------------------

class _AReplyIsOnItsWay(_MothComesBackMasked):
    """The masked figure says one more thing, and the reply takes
    time. The whole turn runs through `_try_llm_reply` and `_on_turn`,
    with the model's reply supplied."""

    REPLY = {"speech": "Coming up.", "tool": "none"}

    def masked_turns(self):
        return [turn for turn in self.turns()
                if turn.get("subject") == self.masked]

    def assert_both_turns_are_filed(self):
        said = [turn["user"] for turn in self.masked_turns()]
        self.assertEqual(len(said), 2)
        self.assertIn("a rotgut", said[0])
        self.assertIn("another", said[1])
        self.assertIn("another", self.recalled(self.patron))


class TestAForgetWhileTheReplyToTheMaskIsBeingMade(_AReplyIsOnItsWay):
    """Sully calls the masked figure by a description, so the turn is
    written under nobody's name. It is still a turn with somebody he
    knows. If he is made to forget Moth while the reply is on its way,
    the reply is not written down under the look he has just forgotten
    with Moth."""

    def test_with_no_forget_the_turn_is_written_down(self):
        """The control. And the turn carries nobody's name."""
        self.real_turn(self.patron, "another", self.REPLY)
        self.assert_both_turns_are_filed()
        for turn in self.masked_turns():
            self.assertNotIn("named_by", turn)
            self.assertNotIn("Moth", turn["user"])

    def test_forgotten_before_the_reply_arrives(self):
        self.real_turn(self.patron, "another", self.REPLY,
                       while_replying=lambda: self.forget("moth"))
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assertEqual(self.filed_under(self.masked), NONE)

    def test_forgotten_while_the_memory_is_on_its_way(self):
        self.real_turn(self.patron, "another", self.REPLY,
                       while_embedding=lambda: self.forget("moth"))
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assertEqual(self.filed_under(self.masked), NONE)

    def test_forgetting_somebody_else_meanwhile_changes_nothing(self):
        self.real_turn(self.patron, "another", self.REPLY,
                       while_replying=lambda: self.forget("wren"))
        self.assertIsNone(get_assigned_name(self.npc, self.other))
        self.assert_both_turns_are_filed()

    def test_it_is_the_same_after_an_earlier_forgetting(self):
        """Each forgetting has its own number. A turn that begins after
        Sully forgot Wren is still lost to forgetting Moth."""
        self.forget("wren")
        self.real_turn(self.patron, "another", self.REPLY,
                       while_replying=lambda: self.forget("moth"))
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assertEqual(self.filed_under(self.masked), NONE)


class TestAReplyToAMaskHeFailedToSeeThroughIsWritten(_AReplyIsOnItsWay):
    """The control for the class above, with the dice the other way.
    The masked figure is a stranger to Sully, so forgetting Moth while
    he answers them has nothing to do with the answer."""

    DICE = LOST

    def test_it_is_written_down(self):
        self.real_turn(self.patron, "another", self.REPLY,
                       while_replying=lambda: self.forget("moth"))
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assert_both_turns_are_filed()


class TestAReplyToAMaskWithABlankEntryIsWritten(_AReplyIsOnItsWay):
    """The mask Sully saw through has a blank entry of its own, so it
    is left alone when he forgets Moth
    (`TestAMaskHeHoldsABlankEntryForIsLeftAlone`). A reply that was on
    its way is then written down under it: the writers ask what was
    forgotten, and this look was not."""

    def setUp(self):
        super().setUp()
        memory = self.npc.recognition_memory
        memory[self.masked] = {"assigned_name": "",
                               "real_sleeve_uid": self.patron.sleeve_uid}
        self.npc.recognition_memory = memory
        self.assertEqual(self.shown_now(), "Moth")

    def test_it_is_written_down(self):
        self.real_turn(self.patron, "another", self.REPLY,
                       while_replying=lambda: self.forget("moth"))
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assertIn(self.masked, self.npc.recognition_memory)
        self.assert_both_turns_are_filed()


class TestAReplyToALookThatWentAsKinIsNotWritten(_AReplyIsOnItsWay):
    """The same question for a look that goes with Moth for another
    reason. An older entry can be joined to a name by a link alone,
    with no record that the change was watched: the room shows a
    description for it, so a turn is written under nobody's name, and
    forgetting the name erases the entry with it (#3825). Sully did not
    see through this mask. A reply to it that was on its way when he
    forgot Moth used to be written down under the look he had just
    forgotten. The writers ask what was forgotten, so it is not."""

    DICE = LOST

    def setUp(self):
        super().setUp()
        memory = self.npc.recognition_memory
        memory[self.masked] = {"assigned_name": "", "linked_to": self.bare,
                               "real_sleeve_uid": self.patron.sleeve_uid}
        self.npc.recognition_memory = memory
        self.assertNotEqual(self.shown_now(), "Moth")

    def test_with_no_forget_the_turn_is_written_down(self):
        self.real_turn(self.patron, "another", self.REPLY)
        self.assert_both_turns_are_filed()
        for turn in self.masked_turns():
            self.assertNotIn("named_by", turn)

    def test_forgotten_before_the_reply_arrives(self):
        self.real_turn(self.patron, "another", self.REPLY,
                       while_replying=lambda: self.forget("moth"))
        self.assertNotIn(self.masked, self.npc.recognition_memory)
        self.assertEqual(self.filed_under(self.masked), NONE)


class TestATurnThatBeginsAfterTheForgettingIsWritten(_AReplyIsOnItsWay):
    """Forgetting is not deafness. The masked figure is a stranger
    now, and what a stranger says next is written down."""

    def test_it_is(self):
        self.forget("moth")
        self.assertEqual(self.filed_under(self.masked), NONE)
        self.real_turn(self.patron, "another", self.REPLY)
        (turn,) = self.masked_turns()
        self.assertIn("another", turn["user"])
        self.assertIn("another", self.recalled(self.patron))

    def test_and_so_is_the_one_after_a_second_forgetting(self):
        """Each forgetting has its own number: forgetting Wren later
        does not make the masked stranger's next turn look forgotten."""
        self.forget("moth")
        self.forget("wren")
        self.real_turn(self.patron, "another", self.REPLY)
        self.assertEqual(len(self.masked_turns()), 1)


class TestForgottenSince(TestCase):
    """The question the two writers ask, by itself."""

    def npc(self, forgets=None, marks=None):
        return SimpleNamespace(ndb=SimpleNamespace(
            llm_forgets=forgets, llm_forgotten=marks))

    def test_a_look_forgotten_after_the_turn_began(self):
        npc = self.npc(2, {"look": 2, "other": 1})
        self.assertTrue(_forgotten_since(npc, "look", 1))
        self.assertTrue(_forgotten_since(npc, "other", 0))

    def test_a_look_forgotten_before_the_turn_began(self):
        npc = self.npc(2, {"look": 2})
        self.assertFalse(_forgotten_since(npc, "look", 2))
        self.assertFalse(_forgotten_since(npc, "look", 3))

    def test_a_look_that_was_never_forgotten(self):
        npc = self.npc(2, {"look": 2})
        self.assertFalse(_forgotten_since(npc, "somebody else", 0))

    def test_a_turn_that_carries_no_count(self):
        npc = self.npc(2, {"look": 2})
        for count in (None, True, "1", 1.0):
            self.assertFalse(_forgotten_since(npc, "look", count))

    def test_nothing_noted_yet(self):
        self.assertFalse(_forgotten_since(self.npc(), "look", 0))
        self.assertEqual(_forgets_so_far(self.npc()), 0)
        self.assertEqual(_forgets_so_far(self.npc(forgets=3)), 3)

    def test_a_mock_for_the_npc_loses_no_writes(self):
        """Many tests stand a `MagicMock` in for the NPC. A mock has
        an answer for every attribute, and none of them is a count or
        a note."""
        npc = mock.MagicMock()
        self.assertEqual(_forgets_so_far(npc), 0)
        self.assertFalse(_forgotten_since(npc, "look", 0))
        self.assertFalse(
            _forgotten_since(npc, mock.MagicMock(), mock.MagicMock()))


class TestANoteOfTheWrongKindIsStartedAgain(_AReplyIsOnItsWay):
    """`ndb` holds whatever was last put there. A count or a note that
    is not what it should be is started again by the next forgetting,
    and that forgetting still stops the reply that was on its way."""

    def test_it_is(self):
        self.npc.ndb.llm_forgets = "three"
        self.npc.ndb.llm_forgotten = ["junk"]
        self.real_turn(self.patron, "another", self.REPLY,
                       while_replying=lambda: self.forget("moth"))
        self.assertEqual(self.npc.ndb.llm_forgets, 1)
        self.assertEqual(self.npc.ndb.llm_forgotten.get(self.masked), 1)
        self.assertEqual(self.filed_under(self.masked), NONE)


# ----------------------------------------------------------------------
# What the observer is told, and who is asked
# ----------------------------------------------------------------------

class TestWhatTheObserverIsToldAboutASeeThrough(_MothComesBackMasked):
    def told_on_erasing(self, uid):
        with mock.patch.object(type(self.npc), "at_looks_erased",
                               autospec=True) as told:
            erase_look(self.npc, uid)
        return told

    def test_the_look_he_saw_through_is_among_the_looks_that_went(self):
        voices = set(self.npc.voice_memory)
        told = self.told_on_erasing(self.bare)
        gone_voices = voices - set(self.npc.voice_memory)
        told.assert_called_once_with(
            self.npc, {self.bare, self.masked}, gone_voices)

    def test_forgetting_somebody_else_does_not_report_it(self):
        told = self.told_on_erasing(self.wren)
        looks = told.call_args.args[1]
        self.assertEqual(looks, {self.wren})


class TestALostSeeThroughIsNotReported(_MothComesBackMasked):
    DICE = LOST

    def test_only_the_entry_is(self):
        with mock.patch.object(type(self.npc), "at_looks_erased",
                               autospec=True) as told:
            erase_look(self.npc, self.bare)
        self.assertEqual(told.call_args.args[1], {self.bare})


class TestAPlayerWhoSawThroughForgetsAsBefore(_MothComesBackMasked):
    """A player keeps no records of their own, and has no door to be
    told at. Wren saw through the same mask; forgetting the name works
    for her as it did."""

    def setUp(self):
        super().setUp()
        self.other.db.disguise_pierce_cache = None
        self.unseen("remove ski mask")
        self.other.execute_cmd("remember gaunt man as Moth")
        self.assertEqual(get_assigned_name(self.other, self.patron), "Moth")
        self.unseen("wear ski mask")
        with mock.patch(ROLL, return_value=WON):
            self.assertEqual(self.patron.get_display_name(self.other), "Moth")

    def test_she_forgets_and_nothing_else_is_asked_of_her(self):
        self.assertFalse(hasattr(self.other, "at_looks_erased"))
        cache = dict(self.other.db.disguise_pierce_cache)
        self.assertIs(cache.get((self.patron.dbref, self.masked)), True)
        self.assertEqual(erase_look(self.other, self.bare), "Moth")
        self.assertEqual(dict(self.other.db.disguise_pierce_cache), {})
        self.assertEqual(dict(self.other.recognition_memory), {})
