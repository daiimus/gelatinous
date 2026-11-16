"""An AI NPC that forgets somebody loses what a player loses (#3841).

Owner, 2026-11-15: "This should be identical to what a player loses.
Their behavior is ideally identical to avoid cheating/hacking."

`forget` is a real erase of a look from one observer (#3825). A player
who forgets a look is left holding nothing about it. An AI NPC is an
observer like any other, and it also files four things of its own
under each look it deals with, each of which is put back in front of
the model on the next turn:

* the names it knew them by (`db.llm_dossiers`);
* what was said between them (`db.llm_memories`);
* the conversation thread (`ndb.llm_history`);
* its read on them, with the reason (`db.soul_opinions`).

None of them went when the NPC forgot, so it was still handed the name
and the talk. They now go at the one door forgetting goes through,
`world.identity.erase_look`, which tells the observer which looks and
voices have just left its memory (`at_looks_erased`).

The NPC here is made by the test and types the real `remember` and
`forget` commands. Every "is gone" below has a control beside it: the
same thing is shown to be there before, and the same thing held about
ANOTHER person is shown to be there after.
"""
from unittest import mock

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.identity import erase_look, get_apparent_uid, get_assigned_name
from world.llm import memory as mem
from world.souls import thoughts

VEC = [1.0, 0.0]


def _embed_at_once(text, on_done, on_fail=None):
    """Stands in for the embedding service: answers in the same call."""
    on_done(list(VEC))


class _AtTheBar(EvenniaTest):
    """Sully keeps bar. Two people come in: one he calls Moth, one he
    calls Wren. He has talked to both and both have wronged him."""

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
        """One finished turn: the thread and the long-term record."""
        handle = self.npc._address_handle(who)
        self.npc._remember_turn(who, line, handle, "Coming up.", None,
                                subject=subject)
        with mock.patch("typeclasses.llm_npc.request_embedding",
                        _embed_at_once):
            self.npc._store_memory(who, handle, line, "Coming up.",
                                   subject=subject)

    def wrong(self, who, note):
        thoughts.add_opinion(self.npc, self.npc._memory_subject(who),
                             "attacked_me", -0.80, note, mood_share=0)

    def forget(self, words):
        self.npc.execute_cmd(f"forget {words}")

    def know_both(self):
        self.name(self.patron, "Moth")
        self.talk(self.patron, "a rotgut")
        self.wrong(self.patron, "they pulled a knife on me")
        self.name(self.other, "Wren")
        self.talk(self.other, "a clean glass")
        self.wrong(self.other, "they walked out on a tab")

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
        return " | ".join(mem.memory_texts(hits))

    def filed_under(self, key):
        """Everything of the NPC's own that is filed under one key."""
        return {
            "alias": key in self.npc._dossiers(),
            "memory": any(rec.get("subject") == key
                          for rec in self.npc._load_memories()),
            "thread": any(
                (turn.get("subject") or filed) == key
                for filed, turns in (self.npc.ndb.llm_history or {}).items()
                for turn in turns),
            "opinion": key in thoughts._opinions(self.npc),
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


ALL = {"alias": True, "memory": True, "thread": True, "opinion": True}
NONE = {"alias": False, "memory": False, "thread": False, "opinion": False}


# ----------------------------------------------------------------------
# Before: the control every "is gone" below stands on
# ----------------------------------------------------------------------

class TestWhatTheNpcHoldsBeforeItForgets(_AtTheBar):
    def setUp(self):
        super().setUp()
        self.know_both()

    def test_all_four_are_filed_under_the_look(self):
        self.assertEqual(self.filed_under(self.bare), ALL)

    def test_the_who_line_has_the_name_and_the_grievance(self):
        line = self.who_line(self.patron)
        self.assertIn("you know them as 'Moth'", line)
        self.assertIn("because they pulled a knife on me", line)

    def test_the_thread_and_the_memory_are_read_back(self):
        self.assertEqual(self.thread(self.patron),
                         ['Moth says to you: "a rotgut"'])
        self.assertIn('Moth said: "a rotgut"', self.recalled(self.patron))

    def test_the_model_is_handed_all_of_it(self):
        prompt = self.prompt(self.patron)
        for words in ("Moth", "a rotgut", "pulled a knife"):
            self.assertIn(words, prompt)


# ----------------------------------------------------------------------
# The two doors of `forget`
# ----------------------------------------------------------------------

class _TheNpcForgetsMoth:
    """Mixed in ahead of `_AtTheBar`. `leave` says whether the patron is
    still in the room when the NPC forgets: `forget` takes a different
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

    def test_the_read_on_them_is_neutral_again(self):
        self.assertEqual(thoughts.opinion_of(self.npc, self.bare), 0.0)

    def test_the_model_is_handed_none_of_it(self):
        prompt = self.prompt(self.patron)
        for words in ("Moth", "a rotgut", "pulled a knife"):
            self.assertNotIn(words, prompt)

    def test_everything_about_somebody_else_is_where_it_was(self):
        self.assertEqual(self.filed_under(self.wren), ALL)
        line = self.who_line(self.other)
        self.assertIn("you know them as 'Wren'", line)
        self.assertIn("because they walked out on a tab", line)
        self.assertEqual(self.thread(self.other),
                         ['Wren says to you: "a clean glass"'])
        self.assertIn('Wren said: "a clean glass"', self.recalled(self.other))

    def test_and_the_model_is_still_handed_it(self):
        prompt = self.prompt(self.other)
        for words in ("Wren", "a clean glass", "walked out on a tab"):
            self.assertIn(words, prompt)


class TestForgettingSomebodyInTheRoom(_TheNpcForgetsMoth, _AtTheBar):
    LEAVES = False


class TestForgettingSomebodyWhoHasLeft(_TheNpcForgetsMoth, _AtTheBar):
    LEAVES = True


# ----------------------------------------------------------------------
# What stays
# ----------------------------------------------------------------------

class TestWhatIsFiledUnderNobodyStays(_AtTheBar):
    """A mood, and the general memory a mood writes, say what happened
    to the NPC. They are not filed under anybody, so there is nothing
    to tell whose they are."""

    def setUp(self):
        super().setUp()
        self.name(self.patron, "Moth")
        self.talk(self.patron, "a rotgut")
        self.npc.db.llm_memories = mem.remember(
            self.npc._load_memories(), "I remember: they put hands on me.",
            list(VEC), subject="")
        thoughts.add_thought(self.npc, "attacked_me", -0.28,
                             "they put hands on me")
        self.forget("moth")

    def test_the_general_memory_is_still_recalled(self):
        self.assertEqual(self.recalled(self.patron),
                         "I remember: they put hands on me.")

    def test_the_mood_is_as_it_was(self):
        self.assertEqual(
            [entry[1] for entry in self.npc.db.soul_thoughts],
            ["attacked_me"])


class TestSomebodyNeverNamedCannotBeForgotten(_AtTheBar):
    """As for a player: `forget` forgets a name. An NPC that talked to
    a stranger and never named them has no name to forget, and keeps
    what it filed under that look."""

    def setUp(self):
        super().setUp()
        self.talk(self.patron, "a rotgut")
        self.wrong(self.patron, "they pulled a knife on me")
        self.forget("gaunt man")

    def test_what_it_filed_is_still_there(self):
        self.assertEqual(
            self.filed_under(self.bare),
            {"alias": False, "memory": True, "thread": True,
             "opinion": True})

    def test_erasing_a_look_it_has_no_entry_for_does_nothing(self):
        self.assertEqual(erase_look(self.npc, self.bare), "")
        self.assertTrue(self.filed_under(self.bare)["memory"])


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
        self.wrong(self.patron, "they pulled a knife on me")
        self.assertEqual(
            self.filed_under(self.masked),
            {"alias": False, "memory": True, "thread": True,
             "opinion": True})
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
        for words in ("Moth", "a rotgut", "another", "pulled a knife"):
            self.assertNotIn(words, prompt)


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
        self.wrong(self.patron, "they pulled a knife on me")
        self.patron.execute_cmd("wear ski mask")
        self.masked = get_apparent_uid(self.patron)
        self.name(self.patron, "Ghost")
        self.talk(self.patron, "another")
        self.wrong(self.patron, "they spat on the bar")


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

    def test_the_face_still_reads_as_moth_with_its_grievance(self):
        line = self.npc._relationship_line(self.bare, self.patron) or ""
        self.assertIn("you know them as 'Moth'", line)
        self.assertIn("because they pulled a knife on me", line)
        self.assertNotIn("Ghost", line)
        self.assertNotIn("spat on the bar", line)


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
        for words in ("Ghost", "another", "spat on the bar"):
            self.assertIn(words, prompt)
        for words in ("Moth", "a rotgut", "pulled a knife"):
            self.assertNotIn(words, prompt)


# ----------------------------------------------------------------------
# The voice learned with the look
# ----------------------------------------------------------------------

class TestTheVoiceOnTheAir(_AtTheBar):
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

    def held(self, key):
        return {k: v for k, v in self.filed_under(key).items()
                if k in ("memory", "thread")}

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


class TestATurnSaysWhatItWasSaidUnder(_AtTheBar):
    def test_it_does(self):
        self.talk(self.patron, "a rotgut")
        (turn,) = self.npc.ndb.llm_history[self.bare]
        self.assertEqual(turn["subject"], self.bare)

    def test_a_turn_with_no_record_counts_as_said_where_it_is_filed(self):
        """A thread put back by the developer console has turns written
        before this record existed."""
        self.name(self.patron, "Moth")
        self.npc.ndb.llm_history = {
            self.bare: [{"user": 'Moth says to you: "a rotgut"',
                         "assistant": "Coming up.", "n": 1}],
            "#ambient": [{"user": 'someone says to you: "last call"',
                          "assistant": "Last call.", "n": 2}],
        }
        self.forget("moth")
        self.assertEqual(list(self.npc.ndb.llm_history), ["#ambient"])


class TestForgetOpinions(_AtTheBar):
    def setUp(self):
        super().setUp()
        thoughts.add_opinion(self.npc, "one", "attacked_me", -0.8, "a",
                             mood_share=0)
        thoughts.add_opinion(self.npc, "two", "was_civil", 0.1, "b",
                             mood_share=0)

    def test_it_drops_the_people_named_and_says_how_many(self):
        self.assertEqual(
            thoughts.forget_opinions(self.npc, {"one", "nobody"}), 1)
        self.assertEqual(list(thoughts._opinions(self.npc)), ["two"])

    def test_it_leaves_the_book_alone_when_nobody_matches(self):
        self.assertEqual(thoughts.forget_opinions(self.npc, {"nobody"}), 0)
        self.assertEqual(sorted(thoughts._opinions(self.npc)),
                         ["one", "two"])
