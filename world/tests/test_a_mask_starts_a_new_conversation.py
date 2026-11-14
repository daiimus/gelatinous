"""A mask starts a new conversation (#3820).

An AI-driven NPC files its long-term memory under the LOOK it met,
"so a disguise reads as a stranger" (NPC_MEMORY_AND_IDENTITY_SPEC §1).
Its short-term thread (the last few turns, fed back into the prompt) and
its sense of who it is in conversation with were filed under the OBJECT.

So somebody could talk to an NPC bare-faced, mask up in another room and
come back: the prompt then held the earlier turns under the old name
beside the new ones under the masked description, and the masked
speaker's lines went on being treated as addressed to the NPC. The
object knew who it was. The NPC did not.

The thread is now filed under the same subject as the memory. Pinned:

* a look that changed out of the NPC's sight starts a fresh thread and
  is not the partner the NPC was talking to;
* a look that changed IN FRONT of an NPC that knew them carries the
  thread on, because the NPC's own recognition memory connects the two;
* going back to the look the NPC knows finds the old thread again;
* a voice on the air has its own thread.
"""
from time import monotonic

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character


class _AtTheBar(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc", key="Sully",
                                 location=self.room1)
        self.npc.recognition_memory = {}
        self.patron = create_object(Character, key="Jorvik Ansel",
                                    location=self.room1)
        self.patron.sleeve_uid = "sleeve-jorvik"
        self.patron.height, self.patron.build = "tall", "lean"
        self.patron.sdesc_keyword = "man"
        self.patron.recognition_memory = {}
        spawn("SKI_MASK")[0].move_to(self.patron, quiet=True)

    def say(self, line):
        """One finished turn, filed where the NPC files it. No subject
        is passed, so the same call runs against the unfixed tree, which
        files by the object."""
        self.npc._remember_turn(self.patron, line, "a gaunt man",
                                "Coming up.", None)

    def thread(self):
        return [turn["user"] for turn in
                self.npc._recent_history(self.patron)]

    def engage(self):
        """Put the conversation hold on the patron, as a directed line
        does. The unfixed tree keyed the hold by the object, and the
        control has to be true there as well."""
        self.npc.ndb.llm_engaged_until = monotonic() + 60
        self.npc.ndb.llm_engaged_with = (
            self.npc._memory_subject(self.patron)
            if hasattr(self.npc, "_thread_keys")
            else self.npc._hist_key(self.patron))

    def mask_out_of_sight(self, command="wear ski mask"):
        self.patron.move_to(self.room2, quiet=True, move_hooks=False)
        self.patron.execute_cmd(command)
        self.patron.move_to(self.room1, quiet=True, move_hooks=False)


class TestMaskedOutOfSight(_AtTheBar):
    def setUp(self):
        super().setUp()
        self.say("a rotgut")
        self.engage()

    def test_the_setup_is_what_it_says(self):
        """The control: there is a thread, and a partner."""
        self.assertEqual(self.thread(),
                         ['a gaunt man says to you: "a rotgut"'])
        self.assertTrue(self.npc._is_engaged_with(self.patron))

    def test_the_masked_figure_has_no_thread(self):
        self.mask_out_of_sight()
        self.assertIn("masked", self.patron.get_sdesc())
        self.assertEqual(self.thread(), [])

    def test_and_is_not_who_the_npc_was_talking_to(self):
        self.mask_out_of_sight()
        self.assertFalse(self.npc._is_engaged_with(self.patron))

    def test_a_turn_under_the_mask_is_its_own_thread(self):
        self.mask_out_of_sight()
        self.say("another")
        self.assertEqual(self.thread(),
                         ['a gaunt man says to you: "another"'])

    def test_the_face_the_npc_knows_finds_the_old_thread_again(self):
        self.mask_out_of_sight()
        self.say("another")
        self.mask_out_of_sight("remove ski mask")
        self.assertEqual(self.thread(),
                         ['a gaunt man says to you: "a rotgut"'])
        self.assertTrue(self.npc._is_engaged_with(self.patron))


class TestMaskedInFrontOfAnNpcThatKnewThem(_AtTheBar):
    """The NPC has a name for the patron and watches the mask go on. Its
    recognition memory connects the two looks, and the conversation is
    one conversation."""

    def setUp(self):
        super().setUp()
        self.npc.execute_cmd("remember gaunt man as Jorvik")
        self.say("a rotgut")
        self.engage()
        self.patron.execute_cmd("wear ski mask")

    def test_the_npc_connected_the_two_looks(self):
        """The control: the unmasking hook wrote the link."""
        from world.identity import get_apparent_uid, linked_family
        family = linked_family(dict(self.npc.recognition_memory),
                               get_apparent_uid(self.patron))
        self.assertEqual(len(family), 2)

    def test_the_thread_carries_on(self):
        self.assertEqual(self.thread(),
                         ['a gaunt man says to you: "a rotgut"'])

    def test_they_are_still_who_the_npc_is_talking_to(self):
        self.assertTrue(self.npc._is_engaged_with(self.patron))

    def test_and_the_next_turn_joins_the_same_thread(self):
        self.say("another")
        self.assertEqual(self.thread(),
                         ['a gaunt man says to you: "a rotgut"',
                          'a gaunt man says to you: "another"'])


class TestMaskOnAndOffAgainInFrontOfTheNpc(_AtTheBar):
    """One conversation, however many times the look changes in sight."""

    def setUp(self):
        super().setUp()
        self.npc.execute_cmd("remember gaunt man as Jorvik")
        self.say("one")
        self.patron.execute_cmd("wear ski mask")
        self.say("two")
        self.patron.execute_cmd("remove ski mask")

    def test_the_face_reads_everything_said_under_the_mask_too(self):
        """A copy of the thread was left under the face when the mask
        went on, and was read first when it came off: the NPC lost
        what it had just said."""
        self.assertEqual(self.thread(),
                         ['a gaunt man says to you: "one"',
                          'a gaunt man says to you: "two"'])

    def test_and_goes_on_from_there(self):
        self.say("three")
        self.patron.execute_cmd("wear ski mask")
        self.assertEqual([t.rsplit(" ", 1)[1] for t in self.thread()],
                         ['"one"', '"two"', '"three"'])

    def test_there_is_one_thread_and_not_two(self):
        self.say("three")
        held = [key for key, turns in
                (self.npc.ndb.llm_history or {}).items() if turns]
        self.assertEqual(len(held), 1)


class TestTheConsoleKeepsItsThread(_AtTheBar):
    """`world/llm/npc_console.py --state` saves the thread between runs.
    It read and wrote it under the object id, where the NPC no longer
    looks."""

    def test_a_saved_thread_is_the_one_the_npc_reads(self):
        import json
        import os
        import tempfile
        from world.llm import npc_console
        self.say("a rotgut")
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        self.addCleanup(os.remove, path)
        npc_console.save_state(self.npc, self.patron, path)
        with open(path) as fh:
            saved = json.load(fh)["history"]
        self.assertEqual([t["user"] for t in saved],
                         ['a gaunt man says to you: "a rotgut"'])
        self.npc.ndb.llm_history = {}
        self.assertEqual(self.thread(), [])
        npc_console.restore_state(self.npc, self.patron, path)
        self.assertEqual(self.thread(),
                         ['a gaunt man says to you: "a rotgut"'])


class TestAVoiceOnTheAir(_AtTheBar):
    def test_it_has_its_own_thread(self):
        self.say("a rotgut")
        voice = self.npc._radio_subject(self.patron)
        self.assertEqual(
            self.npc._recent_history(self.patron, subject=voice), [])
        self.npc._remember_turn(self.patron, "copy", "a voice", "Go ahead.",
                                None, subject=voice)
        self.assertEqual(
            [t["user"] for t in
             self.npc._recent_history(self.patron, subject=voice)],
            ['a voice says to you: "copy"'])
        self.assertEqual(self.thread(),
                         ['a gaunt man says to you: "a rotgut"'])
