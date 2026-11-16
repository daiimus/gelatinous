"""An AI NPC that forgets somebody loses what a player loses (#3841).

Owner, 2026-11-15: "This should be identical to what a player loses.
Their behavior is ideally identical to avoid cheating/hacking."

`forget` is a real erase of a look from one observer (#3825). A player
who forgets a look is left with no memory of it. An AI NPC is an
observer like any other, and it also keeps records of its own about
each look it deals with, each of which is put back in front of the
model on the next turn:

* the names it knew them by (`db.llm_dossiers`);
* what was said between them (`db.llm_memories`);
* the conversation thread (`ndb.llm_history`).

None of them went when the NPC forgot, so it was still handed the name
and the talk. They now go at the one door forgetting goes through,
`world.identity.erase_look`, which tells the observer which looks and
voices have just left its memory (`at_looks_erased`).

A record goes when it is FILED UNDER a forgotten look or voice, and
also when it was WRITTEN UNDER A FORGOTTEN NAME: a look the NPC keeps
may once have answered to the name it loses.

The NPC's read on a person (`db.soul_opinions`) is not touched here.
Whether it goes with the look is not ruled (#3851).

The NPC here is made by the test and types the real `remember` and
`forget` commands. Every "is gone" below has a control beside it: the
same thing is shown to be there before, and the same thing held about
ANOTHER person is shown to be there after.
"""
from unittest import TestCase, mock

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.identity import erase_look, get_apparent_uid, get_assigned_name
from world.llm import memory as mem
from world.voice import named_voice_entry

VEC = [1.0, 0.0]


def _embed_at_once(text, on_done, on_fail=None):
    """Stands in for the embedding service: answers in the same call."""
    on_done(list(VEC))


class _AtTheBar(EvenniaTest):
    """Sully keeps bar. Two people come in: one he calls Moth, one he
    calls Wren."""

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc", key="Sully",
                                 location=self.room1)
        self.npc.recognition_memory = {}
        self.npc.voice_memory = {}
        self.patron = self.body("Jorvik Ansel", "sleeve-jorvik",
                                "tall", "lean", "man")
        self.other = self.body("Petra Lund", "sleeve-petra",
                               "short", "stocky", "woman")
        spawn("SKI_MASK")[0].move_to(self.patron, quiet=True)
        self.bare = get_apparent_uid(self.patron)

    def body(self, key, sleeve, height, build, keyword):
        char = create_object(Character, key=key, location=self.room1)
        char.sleeve_uid = sleeve
        char.height, char.build, char.sdesc_keyword = height, build, keyword
        char.recognition_memory = {}
        return char

    # ---- what the NPC does, by its own doors

    def name(self, who, name):
        """The NPC's own naming: the real `remember`, then the alias."""
        self.npc._remember_person(who, name)
        self.assertEqual(get_assigned_name(self.npc, who), name)

    def talk(self, who, line, subject=None):
        """One finished turn, filed the way `_try_llm_reply` has it
        filed: the handle and whose name it is are worked out first,
        then the thread and the long-term record are written."""
        radio = bool(subject and subject.startswith("voice:"))
        handle = (self.npc._radio_voice_handle(who) if radio
                  else self.npc._address_handle(who))
        named_by = self.npc._name_source(who, radio)
        self.npc._remember_turn(who, line, handle, "Coming up.", None,
                                subject=subject, named_by=named_by)
        with mock.patch("typeclasses.llm_npc.request_embedding",
                        _embed_at_once):
            self.npc._store_memory(who, handle, line, "Coming up.",
                                   subject=subject, named_by=named_by)

    def forget(self, words):
        self.npc.execute_cmd(f"forget {words}")

    def know_both(self):
        self.name(self.patron, "Moth")
        self.talk(self.patron, "a rotgut")
        self.name(self.other, "Wren")
        self.talk(self.other, "a clean glass")

    # ---- what the NPC holds, read the way the prompt reads it

    def who_line(self, who):
        return self.npc._relationship_line(
            self.npc._memory_subject(who), who) or ""

    def thread(self, who, subject=None):
        return [turn["user"] for turn in
                self.npc._recent_history(who, subject=subject)]

    def recalled(self, who, subject=None):
        subject = subject or self.npc._memory_subject(who)
        hits = mem.retrieve(list(VEC), self.npc._load_memories(), k=20,
                            subject=self.npc._memory_scope(subject))
        return " | ".join(sorted(mem.memory_texts(hits)))

    def turns(self):
        return [turn for turns in (self.npc.ndb.llm_history or {}).values()
                for turn in turns]

    def filed_under(self, key):
        """Which of the NPC's own records are filed under one key."""
        return {
            "alias": key in self.npc._dossiers(),
            "memory": any(rec.get("subject") == key
                          for rec in self.npc._load_memories()),
            "thread": any(
                (turn.get("subject") or filed) == key
                for filed, turns in (self.npc.ndb.llm_history or {}).items()
                for turn in turns),
        }

    def prompt(self, who, line="evening"):
        """The messages the model would be sent for one line from *who*."""
        self.npc.db.llm_driven = True
        self.npc.ndb.last_llm = None
        sent = []

        def capture(messages, *args, **kwargs):
            sent.append(messages)

        with mock.patch("typeclasses.llm_npc.llm_enabled",
                        return_value=True), \
                mock.patch("typeclasses.llm_npc.request_embedding",
                           _embed_at_once), \
                mock.patch.object(self.npc, "_agentic_round", capture):
            self.assertTrue(self.npc._try_llm_reply(line, who, "directed"))
        self.assertEqual(len(sent), 1)
        return "\n".join(str(m.get("content") or "") for m in sent[0])


ALL = {"alias": True, "memory": True, "thread": True}
NONE = {"alias": False, "memory": False, "thread": False}


# ----------------------------------------------------------------------
# Before: the control every "is gone" below stands on
# ----------------------------------------------------------------------

class TestWhatTheNpcHoldsBeforeItForgets(_AtTheBar):
    def setUp(self):
        super().setUp()
        self.know_both()

    def test_all_three_are_filed_under_the_look(self):
        self.assertEqual(self.filed_under(self.bare), ALL)

    def test_the_who_line_has_the_name(self):
        self.assertIn("you know them as 'Moth'", self.who_line(self.patron))

    def test_the_thread_and_the_memory_are_read_back(self):
        self.assertEqual(self.thread(self.patron),
                         ['Moth says to you: "a rotgut"'])
        self.assertIn('Moth said: "a rotgut"', self.recalled(self.patron))

    def test_the_model_is_handed_all_of_it(self):
        prompt = self.prompt(self.patron)
        for words in ("Moth", "a rotgut"):
            self.assertIn(words, prompt)


# ----------------------------------------------------------------------
# The two doors of `forget`
# ----------------------------------------------------------------------

class _TheNpcForgetsMoth:
    """Mixed in ahead of `_AtTheBar`. `LEAVES` says whether the patron
    has left the room when the NPC forgets: `forget` takes a different
    path for somebody present than for somebody remembered."""

    LEAVES = False

    def setUp(self):
        super().setUp()
        self.know_both()
        self.wren = get_apparent_uid(self.other)
        if self.LEAVES:
            self.patron.move_to(self.room2, quiet=True, move_hooks=False)
        self.forget("moth")
        if self.LEAVES:
            self.patron.move_to(self.room1, quiet=True, move_hooks=False)

    def test_the_name_is_gone_as_it_is_for_a_player(self):
        """The control that `forget` ran at all."""
        self.assertIsNone(get_assigned_name(self.npc, self.patron))
        self.assertNotIn(self.bare, self.npc.recognition_memory)

    def test_nothing_of_its_own_is_left_under_that_look(self):
        self.assertEqual(self.filed_under(self.bare), NONE)

    def test_the_who_line_is_a_strangers(self):
        self.assertEqual(self.who_line(self.patron), "")

    def test_there_is_no_thread_and_nothing_to_recall(self):
        self.assertEqual(self.thread(self.patron), [])
        self.assertEqual(self.recalled(self.patron), "")

    def test_the_model_is_handed_none_of_it(self):
        prompt = self.prompt(self.patron)
        for words in ("Moth", "a rotgut"):
            self.assertNotIn(words, prompt)

    def test_everything_about_somebody_else_is_where_it_was(self):
        self.assertEqual(self.filed_under(self.wren), ALL)
        self.assertIn("you know them as 'Wren'", self.who_line(self.other))
        self.assertEqual(self.thread(self.other),
                         ['Wren says to you: "a clean glass"'])
        self.assertIn('Wren said: "a clean glass"', self.recalled(self.other))

    def test_and_the_model_is_still_handed_it(self):
        prompt = self.prompt(self.other)
        for words in ("Wren", "a clean glass"):
            self.assertIn(words, prompt)


class TestForgettingSomebodyInTheRoom(_TheNpcForgetsMoth, _AtTheBar):
    LEAVES = False


class TestForgettingSomebodyWhoHasLeft(_TheNpcForgetsMoth, _AtTheBar):
    LEAVES = True


# ----------------------------------------------------------------------
# What stays
# ----------------------------------------------------------------------

class TestWhatIsFiledUnderNobodyStays(_AtTheBar):
    """A general memory says what happened to the NPC. It is not filed
    under anybody, so there is nothing to tell whose it is."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.talk(self.patron, "a rotgut")
        self.npc.db.llm_memories = mem.remember(
            self.npc._load_memories(), "I remember: they put hands on me.",
            list(VEC), subject="")
        self.forget("moth")

    def test_the_general_memory_is_still_recalled(self):
        self.assertEqual(self.recalled(self.patron),
                         "I remember: they put hands on me.")


class TestSomebodyNeverNamedCannotBeForgotten(_AtTheBar):
    """As for a player: `forget` forgets a name. An NPC that talked to
    a stranger and never named them has no name to forget, and keeps
    what it filed under that look."""

    def setUp(self):
        super().setUp()
        self.talk(self.patron, "a rotgut")

    def test_the_command_finds_nothing_to_forget(self):
        self.forget("gaunt man")
        self.assertEqual(
            self.filed_under(self.bare),
            {"alias": False, "memory": True, "thread": True})

    def test_erasing_a_look_it_has_no_entry_for_does_nothing(self):
        self.assertEqual(erase_look(self.npc, self.bare), "")
        self.assertEqual(
            self.filed_under(self.bare),
            {"alias": False, "memory": True, "thread": True})


# ----------------------------------------------------------------------
# A look the NPC knew only through the one it forgot
# ----------------------------------------------------------------------

class TestALookKnownOnlyThroughTheForgottenOne(_AtTheBar):
    """Sully knows Moth and watches the mask go on. The masked look has
    no name of its own: it answers to "Moth" because he watched it
    arrive. Forgetting Moth takes that entry too (#3825), and with it
    what he filed under the masked look."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.talk(self.patron, "a rotgut")
        self.patron.execute_cmd("wear ski mask")
        self.masked = get_apparent_uid(self.patron)
        self.assertNotEqual(self.masked, self.bare)
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Moth")
        self.talk(self.patron, "another")
        self.assertEqual(
            self.filed_under(self.masked),
            {"alias": False, "memory": True, "thread": True})
        self.forget("moth")

    def test_both_entries_left_its_memory(self):
        """The control: #3825 erased the pointer entry as well."""
        memory = self.npc.recognition_memory
        self.assertNotIn(self.bare, memory)
        self.assertNotIn(self.masked, memory)

    def test_nothing_is_left_under_either_look(self):
        self.assertEqual(self.filed_under(self.bare), NONE)
        self.assertEqual(self.filed_under(self.masked), NONE)

    def test_the_masked_figure_is_a_stranger_to_the_model(self):
        prompt = self.prompt(self.patron)
        for words in ("Moth", "a rotgut", "another"):
            self.assertNotIn(words, prompt)


class TestAnUnmarkedRecordUnderALookThatWentWithIt(_AtTheBar):
    """A record that does not say whose name it was written under (one
    from before records said so) still goes when the look it is filed
    under was erased together with the forgotten one."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.patron.execute_cmd("wear ski mask")
        self.masked = get_apparent_uid(self.patron)
        self.npc.db.llm_memories = mem.remember(
            self.npc._load_memories(), 'Moth said: "another"', list(VEC),
            subject=self.masked)
        self.npc.ndb.llm_history = {self.masked: [
            {"user": 'Moth says to you: "another"', "assistant": "Mm.",
             "n": 1}]}
        self.assertEqual(
            self.filed_under(self.masked),
            {"alias": False, "memory": True, "thread": True})

    def test_it_goes_with_the_look_it_is_filed_under(self):
        self.forget("moth")
        self.assertNotIn(self.masked, self.npc.recognition_memory)
        self.assertEqual(self.filed_under(self.masked), NONE)


# ----------------------------------------------------------------------
# Two names for one person: forgetting one leaves the other
# ----------------------------------------------------------------------

class _MothAndGhost(_AtTheBar):
    """Sully knows the bare face as Moth, watches the mask go on, and
    gives the masked figure a name of its own, Ghost. One conversation
    ran across both looks, so its thread is one thread, filed under the
    look that spoke last."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.talk(self.patron, "a rotgut")
        self.patron.execute_cmd("wear ski mask")
        self.masked = get_apparent_uid(self.patron)
        self.name(self.patron, "Ghost")
        self.talk(self.patron, "another")


class TestMothAndGhostBeforeAnythingIsForgotten(_MothAndGhost):
    def test_the_setup_is_what_it_says(self):
        """The control: one thread holding both looks' turns, filed
        under the masked look, and everything filed under each."""
        self.assertEqual(self.thread(self.patron),
                         ['Moth says to you: "a rotgut"',
                          'Ghost says to you: "another"'])
        self.assertEqual(list(self.npc.ndb.llm_history), [self.masked])
        self.assertEqual(self.filed_under(self.bare), ALL)
        self.assertEqual(self.filed_under(self.masked), ALL)


class TestForgettingTheMaskedNameLeavesTheFace(_MothAndGhost):
    def setUp(self):
        super().setUp()
        self.forget("ghost")

    def test_the_masked_name_went_and_the_face_did_not(self):
        memory = self.npc.recognition_memory
        self.assertNotIn(self.masked, memory)
        self.assertEqual(memory[self.bare]["assigned_name"], "Moth")

    def test_what_was_filed_under_the_mask_is_gone(self):
        self.assertEqual(self.filed_under(self.masked), NONE)

    def test_what_was_filed_under_the_face_is_all_there(self):
        self.assertEqual(self.filed_under(self.bare), ALL)

    def test_the_faces_turns_were_kept_out_of_the_lost_thread(self):
        """The thread was filed under the masked look and held the
        face's turn too. That turn was not said under the mask."""
        self.assertEqual(self.thread(self.patron, subject=self.bare),
                         ['Moth says to you: "a rotgut"'])
        self.assertEqual(self.thread(self.patron, subject=self.masked), [])

    def test_the_face_still_reads_as_moth_and_not_as_ghost(self):
        line = self.npc._relationship_line(self.bare, self.patron) or ""
        self.assertIn("you know them as 'Moth'", line)
        self.assertNotIn("Ghost", line)


class TestForgettingTheFaceLeavesTheMaskedName(_MothAndGhost):
    def setUp(self):
        super().setUp()
        self.forget("moth")

    def test_the_face_went_and_the_masked_name_did_not(self):
        memory = self.npc.recognition_memory
        self.assertNotIn(self.bare, memory)
        self.assertEqual(memory[self.masked]["assigned_name"], "Ghost")
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Ghost")

    def test_what_was_filed_under_the_face_is_gone(self):
        self.assertEqual(self.filed_under(self.bare), NONE)

    def test_what_was_filed_under_the_mask_is_all_there(self):
        self.assertEqual(self.filed_under(self.masked), ALL)

    def test_the_faces_turn_is_out_of_the_thread_that_stays(self):
        self.assertEqual(self.thread(self.patron),
                         ['Ghost says to you: "another"'])

    def test_the_model_is_handed_ghost_and_nothing_of_moth(self):
        prompt = self.prompt(self.patron)
        for words in ("Ghost", "another"):
            self.assertIn(words, prompt)
        for words in ("Moth", "a rotgut"):
            self.assertNotIn(words, prompt)


# ----------------------------------------------------------------------
# Written under the forgotten name, filed under a look that stays
# ----------------------------------------------------------------------

class _ServedAsMothBeforeBeingNamedGhost(_AtTheBar):
    """Sully knows Moth and watches the mask go on. He serves the
    masked figure while he still calls them Moth, and only then gives
    them a name of their own. What he wrote down in between is filed
    under the masked look and reads "Moth said ..."."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.patron.execute_cmd("wear ski mask")
        self.masked = get_apparent_uid(self.patron)
        self.talk(self.patron, "another")          # still "Moth" to him
        self.name(self.patron, "Ghost")
        self.talk(self.patron, "a third")          # "Ghost" now


class TestWhatWasWrittenUnderEachName(_ServedAsMothBeforeBeingNamedGhost):
    def test_both_are_filed_under_the_masked_look(self):
        """The control: same shelf, two names."""
        self.assertEqual(self.thread(self.patron),
                         ['Moth says to you: "another"',
                          'Ghost says to you: "a third"'])
        self.assertEqual({turn["subject"] for turn in self.turns()},
                         {self.masked})

    def test_each_says_whose_name_it_was_written_under(self):
        self.assertEqual([turn.get("named_by") for turn in self.turns()],
                         [self.bare, self.masked])
        self.assertEqual(
            sorted((rec["text"][:4], rec.get("named_by"))
                   for rec in self.npc._load_memories()),
            sorted([("Moth", self.bare), ("Ghos", self.masked)]))


class TestForgettingTheNameItWasWrittenUnder(
        _ServedAsMothBeforeBeingNamedGhost):
    def setUp(self):
        super().setUp()
        self.forget("moth")

    def test_the_masked_name_stays(self):
        """The control: the look these records are filed under was not
        erased, so filing alone would have kept all of them."""
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Ghost")
        self.assertIn(self.masked, self.npc.recognition_memory)

    def test_what_was_written_as_moth_is_gone(self):
        self.assertEqual(self.thread(self.patron),
                         ['Ghost says to you: "a third"'])
        self.assertEqual(self.recalled(self.patron),
                         'Ghost said: "a third" — I answered: "Coming up."')

    def test_the_model_is_handed_ghost_and_nothing_of_moth(self):
        prompt = self.prompt(self.patron)
        for words in ("Ghost", "a third"):
            self.assertIn(words, prompt)
        for words in ("Moth", "another"):
            self.assertNotIn(words, prompt)


class TestForgettingTheOtherNameKeepsThem(
        _ServedAsMothBeforeBeingNamedGhost):
    """The same records, the other way round: forgetting Ghost erases
    the masked look they are filed under, so both go, and nothing
    written under Moth's name is filed anywhere else."""

    def test_both_go_with_the_look_they_are_filed_under(self):
        self.forget("ghost")
        self.assertEqual(self.turns(), [])
        self.assertEqual(self.npc._load_memories(), [])
        self.assertEqual(get_assigned_name(self.npc, self.patron), None)
        self.assertEqual(
            self.npc.recognition_memory[self.bare]["assigned_name"], "Moth")


class TestARealTurnMarksWhatItFiles(_AtTheBar):
    """The whole turn, with the model's reply supplied: `_try_llm_reply`
    works out the handle and whose name it is, and `_on_turn` files the
    thread and the memory with both."""

    def turn(self, who, line, reply):
        self.npc.db.llm_driven = True
        self.npc.ndb.last_llm = None

        def answer(messages, on_turn, on_fail=None, schema=None):
            on_turn(dict(reply))

        with mock.patch("typeclasses.llm_npc.llm_enabled",
                        return_value=True), \
                mock.patch("typeclasses.llm_npc.request_embedding",
                           _embed_at_once), \
                mock.patch("typeclasses.llm_npc.request_turn", answer):
            self.assertTrue(self.npc._try_llm_reply(line, who, "directed"))

    def test_a_stranger_is_filed_with_no_name(self):
        self.turn(self.patron, "a rotgut",
                  {"speech": "Coming up.", "tool": "none"})
        (turn,) = self.turns()
        self.assertEqual(turn["subject"], self.bare)
        self.assertNotIn("named_by", turn)
        (rec,) = self.npc._load_memories()
        self.assertEqual(rec["subject"], self.bare)
        self.assertNotIn("named_by", rec)

    def test_somebody_known_is_filed_under_their_own_name(self):
        self.name(self.patron, "Moth")
        self.turn(self.patron, "a rotgut",
                  {"speech": "Coming up.", "tool": "none"})
        (turn,) = self.turns()
        self.assertEqual(turn["user"], 'Moth says to you: "a rotgut"')
        self.assertEqual(turn["named_by"], self.bare)
        (rec,) = self.npc._load_memories()
        self.assertEqual(rec["named_by"], self.bare)

    def test_a_name_coined_in_the_turn_does_not_change_whose_it_was(self):
        """Sully is handed "Moth" for the masked figure, and in his
        reply names them Ghost. The turn was written as Moth's, so it
        is marked as Moth's, though by the time it is filed the look
        has a name of its own. Forgetting Moth then takes it."""
        self.name(self.patron, "Moth")
        self.patron.execute_cmd("wear ski mask")
        masked = get_apparent_uid(self.patron)
        self.turn(self.patron, "another",
                  {"speech": "Coming up.", "tool": "remember",
                   "tool_argument": "Ghost"})
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Ghost")
        (turn,) = self.turns()
        self.assertEqual(turn["user"], 'Moth says to you: "another"')
        self.assertEqual((turn["subject"], turn["named_by"]),
                         (masked, self.bare))
        self.forget("moth")
        self.assertEqual(self.turns(), [])
        self.assertEqual(self.npc._load_memories(), [])
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Ghost")


# ----------------------------------------------------------------------
# The voice learned with the look
# ----------------------------------------------------------------------

class _OnTheAir(_AtTheBar):
    def held(self, key):
        return {k: v for k, v in self.filed_under(key).items()
                if k in ("memory", "thread")}


class TestTheVoiceOnTheAir(_OnTheAir):
    """Naming somebody in person names their voice (#3825), and what an
    NPC hears from that voice on the radio is filed under the voice.
    The voice goes with the look it was named with, and so does what
    was filed under it."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.name(self.other, "Wren")
        self.voice = self.npc._radio_subject(self.patron)
        self.other_voice = self.npc._radio_subject(self.other)
        self.talk(self.patron, "copy, on my way", subject=self.voice)
        self.talk(self.other, "holding at the gate", subject=self.other_voice)

    def test_the_setup_is_what_it_says(self):
        """The control: both voices are named, each with its look, and
        each has a thread and a memory filed under it."""
        self.assertTrue(self.voice.startswith("voice:"))
        named_with = sorted(entry.get("named_with")
                            for entry in self.npc.voice_memory.values())
        self.assertEqual(
            named_with, sorted([self.bare, get_apparent_uid(self.other)]))
        self.assertEqual(self.held(self.voice),
                         {"memory": True, "thread": True})
        self.assertEqual(self.held(self.other_voice),
                         {"memory": True, "thread": True})
        self.assertEqual(
            self.thread(self.patron, subject=self.voice),
            ['Moth says to you: "copy, on my way"'])

    def test_the_voices_thread_and_memory_go_with_the_look(self):
        self.forget("moth")
        self.assertEqual(len(self.npc.voice_memory), 1)
        self.assertEqual(self.held(self.voice),
                         {"memory": False, "thread": False})
        self.assertEqual(self.thread(self.patron, subject=self.voice), [])
        self.assertEqual(self.recalled(self.patron, subject=self.voice), "")

    def test_another_voice_keeps_its_own(self):
        self.forget("moth")
        self.assertEqual(self.held(self.other_voice),
                         {"memory": True, "thread": True})
        self.assertEqual(
            self.thread(self.other, subject=self.other_voice),
            ['Wren says to you: "holding at the gate"'])


class TestADisguisedVoicePlacedByTheForgottenOne(_OnTheAir):
    """Sully named Moth in person, so he holds Moth's natural voice.
    Later a disguised voice comes over the air and he places it as
    Moth's. He holds no entry for the disguised voice: what he hears
    is filed under it, written as "Moth said ...". Forgetting Moth
    erases the natural voice and nothing under the disguised one, and
    takes those records because of the name they were written under."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.name(self.other, "Wren")
        (self.natural,) = [uid for uid, entry in self.npc.voice_memory.items()
                           if entry.get("named_with") == self.bare]
        from world import voice as voice_mod
        real = voice_mod.get_apparent_voice_uid

        def disguised(char):
            return "disguised-voice" if char is self.patron else real(char)

        for target, stand_in in (
                ("world.voice.get_apparent_voice_uid", disguised),
                ("world.combat.dice.opposed_roll",
                 lambda *args, **kwargs: (20, 1, True))):
            patcher = mock.patch(target, stand_in)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.voice = self.npc._radio_subject(self.patron)
        self.other_voice = self.npc._radio_subject(self.other)
        self.talk(self.patron, "copy, on my way", subject=self.voice)
        self.talk(self.other, "holding at the gate", subject=self.other_voice)

    def test_the_setup_is_what_it_says(self):
        """The control: the disguised voice is not one he holds, he
        places it as Moth's, and what he heard is filed under it and
        marked with the natural voice the name came from."""
        self.assertEqual(self.voice, "voice:disguised-voice")
        self.assertNotIn("disguised-voice", self.npc.voice_memory)
        self.assertEqual(self.npc._radio_voice_handle(self.patron), "Moth")
        self.assertEqual(self.npc._name_source(self.patron, radio=True),
                         f"voice:{self.natural}")
        self.assertEqual(self.thread(self.patron, subject=self.voice),
                         ['Moth says to you: "copy, on my way"'])
        self.assertEqual(
            {turn.get("named_by") for turn in self.turns()
             if turn["subject"] == self.voice},
            {f"voice:{self.natural}"})

    def test_what_was_heard_as_moth_goes_with_moth(self):
        self.forget("moth")
        self.assertNotIn(self.natural, self.npc.voice_memory)
        self.assertEqual(self.held(self.voice),
                         {"memory": False, "thread": False})

    def test_another_voice_keeps_its_own(self):
        self.forget("moth")
        self.assertEqual(self.held(self.other_voice),
                         {"memory": True, "thread": True})


class TestNamedVoiceEntry(_AtTheBar):
    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        (self.natural,) = list(self.npc.voice_memory)

    def test_the_heard_voices_own_entry(self):
        uid, entry = named_voice_entry(self.npc, self.patron)
        self.assertEqual((uid, entry["assigned_name"]),
                         (self.natural, "Moth"))

    def test_another_named_voice_of_the_same_body(self):
        with mock.patch("world.voice.get_apparent_voice_uid",
                        return_value="disguised-voice"):
            uid, entry = named_voice_entry(self.npc, self.patron)
        self.assertEqual((uid, entry["assigned_name"]),
                         (self.natural, "Moth"))

    def test_nobody_named(self):
        self.assertEqual(named_voice_entry(self.npc, self.other),
                         (None, None))


# ----------------------------------------------------------------------
# The door itself
# ----------------------------------------------------------------------

class TestWhatTheObserverIsTold(_AtTheBar):
    """`erase_look` knows nothing of an NPC's records. It tells the
    observer which looks and which voices have just left its memory."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.patron.execute_cmd("wear ski mask")
        self.masked = get_apparent_uid(self.patron)
        self.voices = set(self.npc.voice_memory)
        self.assertEqual(len(self.voices), 1)

    def test_the_looks_and_the_voices_that_went(self):
        with mock.patch.object(type(self.npc), "at_looks_erased",
                               autospec=True) as told:
            self.assertEqual(erase_look(self.npc, self.bare), "Moth")
        told.assert_called_once_with(
            self.npc, {self.bare, self.masked}, self.voices)

    def test_nothing_is_said_when_nothing_was_forgotten(self):
        with mock.patch.object(type(self.npc), "at_looks_erased",
                               autospec=True) as told:
            self.assertEqual(erase_look(self.npc, "no-such-look"), "")
        told.assert_not_called()

    def test_a_player_has_no_records_of_their_own_to_drop(self):
        """And is not asked: forgetting works for an observer with no
        such door, as it did."""
        self.assertFalse(hasattr(self.other, "at_looks_erased"))
        self.other.execute_cmd("remember masked man as Shade")
        self.assertEqual(get_assigned_name(self.other, self.patron), "Shade")
        self.assertEqual(erase_look(self.other, self.masked), "Shade")
        self.assertIsNone(get_assigned_name(self.other, self.patron))


# ----------------------------------------------------------------------
# The thread, turn by turn
# ----------------------------------------------------------------------

class TestATurnSaysWhatItWasSaidUnder(_AtTheBar):
    def test_it_does(self):
        self.talk(self.patron, "a rotgut")
        (turn,) = self.npc.ndb.llm_history[self.bare]
        self.assertEqual(turn["subject"], self.bare)

    def test_a_turn_with_no_record_counts_as_said_where_it_is_filed(self):
        """A thread put back by the developer console may have been
        saved before turns carried this record."""
        self.name(self.patron, "Moth")
        self.npc.ndb.llm_history = {
            self.bare: [{"user": 'Moth says to you: "a rotgut"',
                         "assistant": "Coming up.", "n": 1}],
            "#ambient": [{"user": 'someone says to you: "last call"',
                          "assistant": "Last call.", "n": 2}],
        }
        self.forget("moth")
        self.assertEqual(list(self.npc.ndb.llm_history), ["#ambient"])


class TestAThreadNothingForgottenTouches(_AtTheBar):
    """Is left as it is, in the order it is in, whatever numbers its
    turns carry: the developer console puts a thread back without the
    count the numbers come from, so new turns can be numbered below
    old ones."""

    def test_it_is_not_sorted_or_cut(self):
        self.know_both()
        wren = get_apparent_uid(self.other)
        out_of_order = [
            {"user": f'Wren says to you: "{n}"', "assistant": "Mm.",
             "n": n, "subject": wren}
            for n in (9, 8, 7, 3, 2, 1, 6, 5, 4)]
        self.npc.ndb.llm_history[wren] = list(out_of_order)
        self.forget("moth")
        self.assertEqual(self.npc.ndb.llm_history[wren], out_of_order)
        self.assertNotIn(self.bare, self.npc.ndb.llm_history)


# ----------------------------------------------------------------------
# The mark on a long-term record
# ----------------------------------------------------------------------

class TestALongTermRecordSaysWhoseNameItUses(TestCase):
    def test_a_new_record_keeps_it(self):
        (rec,) = mem.remember([], 'Moth said: "hi"', VEC, subject="look",
                              named_by="other-look")
        self.assertEqual(rec["named_by"], "other-look")

    def test_a_record_with_no_name_in_it_carries_none(self):
        (rec,) = mem.remember([], 'a gaunt man said: "hi"', VEC,
                              subject="look")
        self.assertNotIn("named_by", rec)

    def test_remembering_it_again_fills_in_a_missing_one(self):
        recs = mem.remember([], 'Moth said: "hi"', VEC, subject="look")
        (rec,) = mem.remember(recs, 'Moth said: "hi"', VEC, subject="look",
                              named_by="other-look")
        self.assertEqual((rec["uses"], rec["named_by"]), (1, "other-look"))

    def test_and_leaves_one_that_is_there(self):
        recs = mem.remember([], 'Moth said: "hi"', VEC, subject="look",
                            named_by="first")
        (rec,) = mem.remember(recs, 'Moth said: "hi"', VEC, subject="look",
                              named_by="second")
        self.assertEqual(rec["named_by"], "first")
