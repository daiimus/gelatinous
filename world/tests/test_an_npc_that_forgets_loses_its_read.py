"""An AI NPC that forgets somebody loses its read on them (#3851).

An AI NPC keeps a read on each person it has dealt with: what they did
to it, entry by entry, each with its reason (`db.soul_opinions`,
`world.souls.thoughts`). The model is handed it on every turn: "your
read on them: hostile (because they put hands on me)".

#3841 made an NPC that forgets a look lose the names, the talk and the
thread it had filed under it. The read was left alone, so an NPC that
had forgotten somebody was still told what they had done to it. The
owner was asked whether the read goes too, with the recommendation that
it does and that the general mood stays. Owner, 2026-11-16: "I concur
with your recommendation."

So:

* the read goes with the looks that were erased;
* the mood stays, and so does the general memory a strong mood wrote:
  neither is filed under anybody. The NPC is still shaken, and no
  longer knows at whom;
* only what was erased. A look the NPC still knows keeps its read.

The reads here are written by the two doors the game writes them
through: `react_to_attack`, which combat calls for whoever was hit, and
`_note_courtesy`, which hearing thanks calls. The NPC types the real
`forget`. Every "is gone" below has a control beside it: the same thing
is shown to be there before, and the same thing held about ANOTHER
person is shown to be there after.
"""
from types import SimpleNamespace
from unittest import TestCase, mock

from world.director.civilians import react_to_attack
from world.identity import erase_look, get_apparent_uid, get_assigned_name
from world.souls import engine, thoughts
from world.tests.test_an_npc_that_forgets import _AtTheBar, _embed_at_once

HOSTILE = "your read on them: hostile (because they put hands on me)"
FRIENDLY = "your read on them: friendly (because they were decent to me)"
SHAKEN = "You are worn down and short on patience today."
GENERAL = "I remember: they put hands on me."


class _SullyHasASoul(_AtTheBar):
    """Sully has a soul, as the whole cast does: somewhere for a
    feeling to go."""

    def setUp(self):
        super().setUp()
        self.npc.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])

    def attacked_by(self, who, writes_a_memory=False):
        """What combat does for whoever was hit. With *writes_a_memory*
        the NPC has its voice on, so the share of the blow that goes
        into its mood is also written down as a general memory."""
        self.npc.db.llm_driven = writes_a_memory
        with mock.patch("world.llm.client.llm_enabled",
                        return_value=writes_a_memory), \
                mock.patch("world.llm.client.request_embedding",
                           _embed_at_once):
            react_to_attack(self.npc, who)

    def thanked_by(self, who):
        """What hearing thanks does. Twice: once is not enough to move
        the read off neutral."""
        self.npc._note_courtesy(who)
        self.npc._note_courtesy(who)

    def reasons(self, key):
        """Why the NPC thinks what it thinks of one look."""
        return [note for _at, _key, _valence, note in
                (tuple(entry) for entry in
                 thoughts._opinions(self.npc).get(key) or ())]

    def mood_log(self):
        return [(key, valence, note) for _at, key, valence, note in
                (tuple(entry) for entry in self.npc.db.soul_thoughts or ())]

    def wronged_by_moth_thanked_by_wren(self):
        self.know_both()
        self.wren = get_apparent_uid(self.other)
        self.attacked_by(self.patron)
        self.thanked_by(self.other)


# ----------------------------------------------------------------------
# Before: the control every "is gone" below stands on
# ----------------------------------------------------------------------

class TestTheReadBeforeItForgets(_SullyHasASoul):
    def setUp(self):
        super().setUp()
        self.wronged_by_moth_thanked_by_wren()

    def test_each_read_is_filed_under_the_look(self):
        self.assertEqual(self.reasons(self.bare), ["they put hands on me"])
        self.assertEqual(self.reasons(self.wren),
                         ["they were decent to me"] * 2)

    def test_the_who_line_has_the_name_and_the_read(self):
        line = self.who_line(self.patron)
        self.assertIn("you know them as 'Moth'", line)
        self.assertIn(HOSTILE, line)
        self.assertIn(FRIENDLY, self.who_line(self.other))

    def test_the_model_is_handed_it(self):
        self.assertIn(HOSTILE, self.prompt(self.patron))

    def test_the_blow_went_into_the_mood_as_well(self):
        self.assertIn("attacked_me", [key for key, _v, _n in self.mood_log()])
        self.assertIn(SHAKEN, self.prompt(self.patron))


# ----------------------------------------------------------------------
# The two doors of `forget`
# ----------------------------------------------------------------------

class _TheNpcForgetsWhoWrongedIt:
    """Mixed in ahead of `_SullyHasASoul`. `LEAVES` says whether Moth
    has left the room when the NPC forgets: `forget` takes a different
    path for somebody present than for somebody remembered."""

    LEAVES = False

    def setUp(self):
        super().setUp()
        self.wronged_by_moth_thanked_by_wren()
        self.mood_before = self.mood_log()
        if self.LEAVES:
            self.patron.move_to(self.room2, quiet=True, move_hooks=False)
        self.forget("moth")
        if self.LEAVES:
            self.patron.move_to(self.room1, quiet=True, move_hooks=False)

    def test_the_name_is_gone(self):
        """The control that `forget` ran at all."""
        self.assertIsNone(get_assigned_name(self.npc, self.patron))
        self.assertNotIn(self.bare, self.npc.recognition_memory)

    def test_the_read_went_with_it(self):
        self.assertNotIn(self.bare, thoughts._opinions(self.npc))
        self.assertEqual(thoughts.opinion_of(self.npc, self.bare), 0.0)

    def test_the_who_line_is_a_strangers(self):
        self.assertEqual(self.who_line(self.patron), "")

    def test_the_model_is_not_told_what_they_did(self):
        prompt = self.prompt(self.patron)
        for words in ("your read on them", "put hands on me", "Moth"):
            self.assertNotIn(words, prompt)

    def test_the_mood_is_what_it_was(self):
        self.assertEqual(self.mood_log(), self.mood_before)

    def test_so_it_is_still_shaken(self):
        self.assertIn(SHAKEN, self.prompt(self.patron))

    def test_its_read_on_somebody_else_is_where_it_was(self):
        self.assertEqual(self.reasons(self.wren),
                         ["they were decent to me"] * 2)
        line = self.who_line(self.other)
        self.assertIn("you know them as 'Wren'", line)
        self.assertIn(FRIENDLY, line)

    def test_and_the_model_is_still_handed_that_one(self):
        self.assertIn(FRIENDLY, self.prompt(self.other))


class TestForgettingWhoWrongedItInTheRoom(
        _TheNpcForgetsWhoWrongedIt, _SullyHasASoul):
    LEAVES = False


class TestForgettingWhoWrongedItAfterTheyLeft(
        _TheNpcForgetsWhoWrongedIt, _SullyHasASoul):
    LEAVES = True


class TestWhatTheyDoNextStartsANewRead(_SullyHasASoul):
    """Forgetting is not forgiving in advance. A blow after the wipe is
    a new entry, held against a stranger."""

    def setUp(self):
        super().setUp()
        self.wronged_by_moth_thanked_by_wren()
        self.forget("moth")
        self.attacked_by(self.patron)

    def test_it_is_held_against_a_stranger(self):
        line = self.who_line(self.patron)
        self.assertIn(HOSTILE, line)
        self.assertNotIn("Moth", line)
        self.assertEqual(self.reasons(self.bare), ["they put hands on me"])


# ----------------------------------------------------------------------
# What stays
# ----------------------------------------------------------------------

class TestTheGeneralMemoryOfTheBlowStays(_SullyHasASoul):
    """A blow hard enough to move the mood is also written down as a
    general memory, filed under nobody. It says what happened to the
    NPC and not who did it."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.attacked_by(self.patron, writes_a_memory=True)
        self.assertEqual(
            [(rec.get("subject"), rec.get("text"))
             for rec in self.npc._load_memories()],
            [("", GENERAL)])
        self.forget("moth")

    def test_the_read_went(self):
        self.assertNotIn(self.bare, thoughts._opinions(self.npc))

    def test_the_general_memory_is_still_recalled(self):
        self.assertEqual(self.recalled(self.patron), GENERAL)

    def test_the_model_is_handed_what_happened_and_not_who(self):
        prompt = self.prompt(self.patron)
        self.assertIn(GENERAL, prompt)
        for words in ("your read on them", "Moth"):
            self.assertNotIn(words, prompt)


class TestTheReadOnSomebodyNeverNamedStays(_SullyHasASoul):
    """As for a player: `forget` forgets a name. A stranger who hit the
    NPC has no name to forget, and the NPC keeps what it holds against
    that look."""

    def setUp(self):
        super().setUp()
        self.attacked_by(self.patron)

    def test_the_command_finds_nothing_to_forget(self):
        self.forget("lean man")
        self.assertIn(HOSTILE, self.who_line(self.patron))

    def test_erasing_a_look_it_has_no_entry_for_does_nothing(self):
        self.assertEqual(erase_look(self.npc, self.bare), "")
        self.assertEqual(self.reasons(self.bare), ["they put hands on me"])


# ----------------------------------------------------------------------
# Only what was erased
# ----------------------------------------------------------------------

class _MothPutsTheMaskOn(_SullyHasASoul):
    """Sully knows Moth and watches the mask go on. The masked figure
    is the one who hits him, so the read is filed under the masked
    look."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.patron.execute_cmd("wear ski mask")
        self.masked = get_apparent_uid(self.patron)
        self.assertNotEqual(self.masked, self.bare)


class TestAReadOnALookKnownOnlyThroughTheForgottenOne(_MothPutsTheMaskOn):
    """The masked look has no name of its own: it answers to "Moth"
    because Sully watched it arrive. Forgetting Moth takes that entry
    too (#3825), and with it what he holds against the masked look."""

    def setUp(self):
        super().setUp()
        self.attacked_by(self.patron)
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        self.assertEqual(self.reasons(self.bare), [])
        line = self.who_line(self.patron)
        self.assertIn(HOSTILE, line)
        self.forget("moth")

    def test_both_entries_left_its_memory(self):
        """The control: #3825 erased the pointer entry as well."""
        memory = self.npc.recognition_memory
        self.assertNotIn(self.bare, memory)
        self.assertNotIn(self.masked, memory)

    def test_the_read_on_the_masked_look_went_too(self):
        self.assertNotIn(self.masked, thoughts._opinions(self.npc))
        self.assertEqual(self.who_line(self.patron), "")


class _MothAndGhostAndABlow(_MothPutsTheMaskOn):
    """Sully gives the masked figure a name of its own, Ghost, and it
    is Ghost who hits him. He holds two names for one person and has
    connected them, so the grudge reads on both faces (#3371)."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Ghost")
        self.attacked_by(self.patron)

    def face_line(self):
        return self.npc._relationship_line(self.bare, self.patron) or ""


class TestTwoNamesBeforeAnythingIsForgotten(_MothAndGhostAndABlow):
    def test_the_setup_is_what_it_says(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        self.assertEqual(self.reasons(self.bare), [])
        self.assertIn(HOSTILE, self.who_line(self.patron))
        self.assertIn(HOSTILE, self.face_line())


class TestForgettingTheOtherNameKeepsTheRead(_MothAndGhostAndABlow):
    """Forgetting Moth is not forgetting Ghost. The read is filed under
    the look he still knows."""

    def setUp(self):
        super().setUp()
        self.forget("moth")

    def test_the_face_went_and_the_masked_name_did_not(self):
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Ghost")

    def test_ghost_is_still_held_to_it(self):
        self.assertEqual(self.reasons(self.masked), ["they put hands on me"])
        line = self.who_line(self.patron)
        self.assertIn("you know them as 'Ghost'", line)
        self.assertIn(HOSTILE, line)
        self.assertNotIn("Moth", line)


class TestForgettingTheNameThatDidItClearsBothFaces(_MothAndGhostAndABlow):
    """The cost that was named when the ruling was asked for. Sully had
    connected the two looks, so the face carried what the mask did
    (#3371). With Ghost forgotten, the masked figure is a stranger he
    holds nothing against, and the face he still calls Moth reads
    clean."""

    def setUp(self):
        super().setUp()
        self.forget("ghost")

    def test_the_masked_name_went_and_the_face_did_not(self):
        self.assertNotIn(self.masked, self.npc.recognition_memory)
        self.assertEqual(
            self.npc.recognition_memory[self.bare]["assigned_name"], "Moth")

    def test_the_read_went(self):
        self.assertNotIn(self.masked, thoughts._opinions(self.npc))

    def test_the_masked_figure_is_a_stranger_he_holds_nothing_against(self):
        self.assertEqual(self.who_line(self.patron), "")

    def test_the_face_no_longer_carries_it(self):
        line = self.face_line()
        self.assertIn("you know them as 'Moth'", line)
        self.assertNotIn("your read on them", line)


class TestAReadEarnedBeforeTheLookHadItsOwnName(_MothPutsTheMaskOn):
    """The masked figure hits Sully while he still calls it Moth, and
    only then gets a name of its own. A read is filed under the look
    and has no name in it, so it stays with the look he still knows
    when he forgets Moth. (What he WROTE DOWN while he called it Moth
    has the name in it, and goes: #3841.)"""

    def setUp(self):
        super().setUp()
        self.attacked_by(self.patron)              # still "Moth" to him
        self.name(self.patron, "Ghost")
        self.forget("moth")

    def test_the_masked_name_stays(self):
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Ghost")

    def test_and_so_does_what_the_masked_figure_did(self):
        line = self.who_line(self.patron)
        self.assertIn("you know them as 'Ghost'", line)
        self.assertIn(HOSTILE, line)
        self.assertNotIn("Moth", line)


# ----------------------------------------------------------------------
# The soul's half, by itself
# ----------------------------------------------------------------------

class TestForgetOpinions(TestCase):
    def soul(self):
        soul = SimpleNamespace(db=SimpleNamespace(
            soul_opinions={}, soul_thoughts=[], soul_wound_keys=None,
            llm_driven=False))
        thoughts.add_opinion(soul, "one", "attacked_me", -0.6, "a")
        thoughts.add_opinion(soul, "two", "was_civil", 0.1, "b")
        thoughts.add_opinion(soul, "three", "was_civil", 0.1, "c")
        return soul

    def test_the_control(self):
        self.assertEqual(sorted(thoughts._opinions(self.soul())),
                         ["one", "three", "two"])

    def test_it_drops_the_ones_named_and_no_others(self):
        soul = self.soul()
        thoughts.forget_opinions(soul, {"one", "three", "nobody"})
        self.assertEqual(list(thoughts._opinions(soul)), ["two"])

    def test_the_mood_is_not_touched(self):
        soul = self.soul()
        before = list(soul.db.soul_thoughts)
        self.assertEqual(len(before), 3)
        thoughts.forget_opinions(soul, ["one", "two", "three"])
        self.assertEqual(soul.db.soul_thoughts, before)
        self.assertEqual(thoughts._opinions(soul), {})

    def test_nobody_it_holds_anything_against(self):
        soul = self.soul()
        book = soul.db.soul_opinions
        for uids in ((), None, ["nobody"], ["voice:one"], [None, ""]):
            thoughts.forget_opinions(soul, uids)
        self.assertIs(soul.db.soul_opinions, book)
        self.assertEqual(sorted(book), ["one", "three", "two"])
