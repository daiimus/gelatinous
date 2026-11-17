"""An AI NPC that forgets somebody also forgets a voice it knew only by
having placed it as theirs (#3861).

The voice twin of `test_an_npc_forgets_a_look_it_saw_through` (#3859).

Naming somebody in person names their voice. A person can then sound
different on the air than the voice the NPC named: they changed it
with `@voice`, or use a voice modulator. The NPC has no voice entry
for the changed voice. If it places it as theirs (one roll, stored),
what it hears from then on is written under Moth's name and goes with
the name (#3841). What it had filed under that voice BEFORE it placed
it carries nobody's name, and stayed.

The owner was shown both, with an NPC that hears an unfamiliar voice,
later learns the person's name and voice, then recognises the
unfamiliar voice as theirs, and is then made to forget them, and was
asked whether the second should go too, as it does for a mask. Owner,
2026-11-16: "You recommendation is fine."

So `world.identity.erase_look` now also reports the voices the
observer holds no entry for whose stored placing (a won verdict in
`voice_discern_cache`) has just gone, and the NPC drops what it filed
under them.

The NPC is made by the test and types the real `forget`. The person
changes their voice with the real `@voice`. The placing is made the
way the game makes it: the NPC is asked how it knows the voice on the
air (`_radio_voice_handle`), with the dice fixed. Every "is gone" has
a control beside it: the same thing is there before, and the same
thing held about ANOTHER voice, or about a voice the NPC did NOT
place, is there after.
"""
from unittest import mock

from world.identity import erase_look, get_apparent_uid, get_assigned_name
from world.tests.test_an_npc_that_forgets import _OnTheAir
from world.voice import get_apparent_voice_uid

ROLL = "world.combat.dice.opposed_roll"
WON, LOST = (20, 1, True), (1, 20, False)

HELD = {"memory": True, "thread": True}
NOTHING = {"memory": False, "thread": False}


class _AVoiceBeforeItHasAName(_OnTheAir):
    """An unfamiliar gravelly voice calls Sully on the air and he notes
    what it said. Later he meets Moth, whose voice is plain, and names
    them. Then the gravelly voice calls again. `DICE` says whether he
    places it as Moth's. Wren is on the air too, under her own voice."""

    DICE = WON

    def setUp(self):
        super().setUp()
        self.changes_voice("description gravelly")
        self.gravelly = self.npc._radio_subject(self.patron)
        self.on_the_air(self.patron, "anyone on this band?")
        self.changes_voice("clear")
        self.plain = self.npc._radio_subject(self.patron)
        self.assertNotEqual(self.plain, self.gravelly)
        self.name(self.patron, "Moth")
        self.name(self.other, "Wren")
        self.wren_voice = self.npc._radio_subject(self.other)
        self.on_the_air(self.other, "holding at the gate")
        self.changes_voice("description gravelly")
        self.assertEqual(self.npc._radio_subject(self.patron), self.gravelly)
        self.heard_as = self.on_the_air(self.patron, "copy, on my way")

    def changes_voice(self, words):
        self.patron.execute_cmd(f"@voice {words}")

    def on_the_air(self, who, line):
        """One finished radio turn. Returns how Sully knew the voice,
        which is where a changed voice is placed or not."""
        with mock.patch(ROLL, return_value=self.DICE):
            handle = self.npc._radio_voice_handle(who)
            self.talk(who, line, subject=self.npc._radio_subject(who))
        return handle

    def uid(self, subject):
        return subject[len("voice:"):]

    def verdict(self, observer=None):
        """True for a won placing of the gravelly voice, False for a
        failed one, None when the observer (Sully) holds neither."""
        cache = dict((observer or self.npc).db.voice_discern_cache or {})
        return cache.get((self.patron.dbref, self.uid(self.gravelly)))

    def said_under(self, subject):
        return [turn["user"] for turn in self.turns()
                if turn.get("subject") == subject]

    def assert_wren_is_where_she_was(self):
        self.assertEqual(get_assigned_name(self.npc, self.other), "Wren")
        self.assertIn(self.uid(self.wren_voice), self.npc.voice_memory)
        self.assertEqual(self.held(self.wren_voice), HELD)
        self.assertEqual(self.said_under(self.wren_voice),
                         ['Wren says to you: "holding at the gate"'])


# ----------------------------------------------------------------------
# Before: the control every "is gone" below stands on
# ----------------------------------------------------------------------

class TestWhatSullyHoldsAboutTheVoiceHePlaced(_AVoiceBeforeItHasAName):
    def test_he_placed_it_as_moths(self):
        self.assertEqual(self.heard_as, "Moth")
        self.assertIs(self.verdict(), True)

    def test_the_changed_voice_has_no_entry_of_its_own(self):
        voices = self.npc.voice_memory
        self.assertNotIn(self.uid(self.gravelly), voices)
        self.assertIn(self.uid(self.plain), voices)

    def test_both_calls_are_filed_under_the_changed_voice(self):
        said = self.said_under(self.gravelly)
        self.assertEqual(len(said), 2)
        self.assertIn("anyone on this band?", said[0])
        self.assertNotIn("Moth", said[0])
        self.assertEqual(said[1], 'Moth says to you: "copy, on my way"')
        self.assertEqual(self.held(self.gravelly), HELD)

    def test_only_the_second_is_written_under_moths_name(self):
        marks = [turn.get("named_by") for turn in self.turns()
                 if turn.get("subject") == self.gravelly]
        self.assertEqual(marks, [None, self.plain])

    def test_both_are_read_back(self):
        recalled = self.recalled(self.patron, subject=self.gravelly)
        self.assertIn("anyone on this band?", recalled)
        self.assertIn("copy, on my way", recalled)


# ----------------------------------------------------------------------
# He forgets Moth
# ----------------------------------------------------------------------

class TestForgettingMothTakesTheVoiceHePlaced(_AVoiceBeforeItHasAName):
    def setUp(self):
        super().setUp()
        self.forget("moth")

    def test_the_name_the_voice_and_the_placing_are_gone(self):
        """The control that `forget` ran, and what #3825 already did."""
        self.assertIsNone(get_assigned_name(self.npc, self.patron))
        self.assertNotIn(self.uid(self.plain), self.npc.voice_memory)
        self.assertIsNone(self.verdict())

    def test_what_he_noted_after_placing_it_is_gone(self):
        """True before this change: it was written under Moth's name."""
        self.assertNotIn('Moth says to you: "copy, on my way"',
                         self.said_under(self.gravelly))

    def test_what_he_noted_before_placing_it_is_gone_too(self):
        self.assertEqual(self.said_under(self.gravelly), [])
        self.assertEqual(self.held(self.gravelly), NOTHING)
        self.assertEqual(
            self.recalled(self.patron, subject=self.gravelly), "")

    def test_everything_about_wren_is_where_it_was(self):
        self.assert_wren_is_where_she_was()


class TestWhatTheVoiceSaysNextIsAStrangers(_AVoiceBeforeItHasAName):
    def setUp(self):
        super().setUp()
        self.forget("moth")
        self.heard_next = self.on_the_air(self.patron, "still there?")

    def test_it_is_not_placed_and_is_written_down(self):
        self.assertNotEqual(self.heard_next, "Moth")
        said = self.said_under(self.gravelly)
        self.assertEqual(len(said), 1)
        self.assertIn("still there?", said[0])
        self.assertNotIn("Moth", said[0])


# ----------------------------------------------------------------------
# Controls: voices that do NOT go
# ----------------------------------------------------------------------

class TestAVoiceHeFailedToPlaceKeepsItsRecords(_AVoiceBeforeItHasAName):
    """The same evening with the dice the other way. Sully never
    connected the gravelly voice to Moth, so forgetting Moth takes
    nothing of what that voice said. The failed attempt stays failed
    (#3817)."""

    DICE = LOST

    def setUp(self):
        super().setUp()
        self.assertNotEqual(self.heard_as, "Moth")
        self.assertIs(self.verdict(), False)
        self.forget("moth")

    def test_moth_is_forgotten(self):
        self.assertIsNone(get_assigned_name(self.npc, self.patron))
        self.assertNotIn(self.uid(self.plain), self.npc.voice_memory)

    def test_the_failed_attempt_is_still_failed(self):
        self.assertIs(self.verdict(), False)

    def test_what_the_strange_voice_said_is_all_there(self):
        said = self.said_under(self.gravelly)
        self.assertEqual(len(said), 2)
        self.assertIn("anyone on this band?", said[0])
        self.assertIn("copy, on my way", said[1])
        self.assertEqual(self.held(self.gravelly), HELD)


class TestAChangedVoiceWithANameOfItsOwnStays(_AVoiceBeforeItHasAName):
    """Sully meets the gravelly voice in person, under a mask, and
    names that figure Ghost. He never connects Ghost to Moth. The
    gravelly voice now has an entry and a name of its own, so
    forgetting Moth is not forgetting it, and what he noted from it
    before it had that name stays with it. What he wrote down while he
    took it for Moth's goes, as it did before (#3841)."""

    def setUp(self):
        super().setUp()
        self.patron.move_to(self.room2, quiet=True, move_hooks=False)
        self.patron.execute_cmd("wear ski mask")
        self.patron.move_to(self.room1, quiet=True, move_hooks=False)
        self.masked = get_apparent_uid(self.patron)
        with mock.patch(ROLL, return_value=LOST):
            self.name(self.patron, "Ghost")
        self.assertEqual(
            self.npc.voice_memory[self.uid(self.gravelly)]["named_with"],
            self.masked)
        self.forget("moth")

    def test_moth_went_and_ghost_did_not(self):
        self.assertNotIn(self.bare, self.npc.recognition_memory)
        self.assertEqual(get_assigned_name(self.npc, self.patron), "Ghost")
        voices = self.npc.voice_memory
        self.assertNotIn(self.uid(self.plain), voices)
        self.assertEqual(
            voices[self.uid(self.gravelly)]["assigned_name"], "Ghost")

    def test_what_the_voice_said_before_it_had_a_name_is_still_there(self):
        said = self.said_under(self.gravelly)
        self.assertEqual(len(said), 1)
        self.assertIn("anyone on this band?", said[0])

    def test_what_was_written_as_moth_is_gone(self):
        self.assertNotIn('Moth says to you: "copy, on my way"',
                         self.said_under(self.gravelly))


class TestAPlacedVoiceWithABlankEntryIsLeftAlone(_AVoiceBeforeItHasAName):
    """Not part of the ruling. This is what the code does, pinned so
    that a change to it is made on purpose.

    A voice entry can be blank: it has no name, and tells Sully
    nothing. A voice that has one is still in his voice memory, so it
    is not reported with a placing that goes, and what is filed under
    it stays, as for a look with a blank entry (#3859). What he wrote
    down under Moth's name goes, as it did before (#3841)."""

    def setUp(self):
        super().setUp()
        voices = self.npc.voice_memory
        voices[self.uid(self.gravelly)] = {
            "assigned_name": "", "real_sleeve_uid": self.patron.sleeve_uid}
        self.npc.voice_memory = voices
        self.forget("moth")

    def test_the_placing_went_and_the_blank_entry_did_not(self):
        self.assertIsNone(self.verdict())
        self.assertIn(self.uid(self.gravelly), self.npc.voice_memory)
        self.assertNotIn(self.uid(self.plain), self.npc.voice_memory)

    def test_what_he_noted_before_placing_it_stays(self):
        (said,) = self.said_under(self.gravelly)
        self.assertIn("anyone on this band?", said)


class TestAVerdictOnABodyThatIsGoneDoesNotHideTheVoice(
        _AVoiceBeforeItHasAName):
    """A verdict is kept per body object. One made on a body that no
    longer exists is never erased, because the body cannot be looked
    up, and a new body of the same person can sound the same. Sully
    holds such a leftover for the gravelly voice beside the verdict on
    the body in front of him. Forgetting Moth takes the second, and
    the leftover does not make the voice count as still known."""

    GONE = "#999999999"

    def setUp(self):
        super().setUp()
        cache = self.npc.db.voice_discern_cache
        cache[(self.GONE, self.uid(self.gravelly))] = True
        self.npc.db.voice_discern_cache = cache
        self.forget("moth")

    def test_the_verdict_on_the_body_in_front_of_him_went(self):
        self.assertIsNone(self.verdict())

    def test_the_leftover_is_still_there(self):
        """Nothing erases it, before this change or after."""
        cache = dict(self.npc.db.voice_discern_cache or {})
        self.assertIs(cache.get((self.GONE, self.uid(self.gravelly))), True)

    def test_what_he_noted_under_the_voice_is_gone(self):
        self.assertEqual(self.said_under(self.gravelly), [])
        self.assertEqual(self.held(self.gravelly), NOTHING)


class TestALateReplyToTheVoiceHePlaced(_AVoiceBeforeItHasAName):
    """A reply on the air takes time. If Sully is made to forget Moth
    while his reply to the gravelly voice is on its way, the reply is
    not written down. This was so before the change as well, for the
    reply itself: it is written under Moth's name. It is here so that
    the whole of what is filed under the voice is shown to go."""

    REPLY = {"speech": "Copy.", "tool": "none"}

    def noted_under(self, subject):
        """The long-term records filed under one voice. Sully has no
        radio here, so his answer is refused and the turn leaves no
        line in the thread; what he heard is still written down."""
        return [rec["text"] for rec in self.npc._load_memories()
                if rec.get("subject") == subject]

    def test_with_no_forget_it_is_written_down(self):
        """The control."""
        self.assertEqual(len(self.noted_under(self.gravelly)), 2)
        self.real_turn(self.patron, "one more thing", self.REPLY,
                       mode="radio")
        noted = self.noted_under(self.gravelly)
        self.assertEqual(len(noted), 3)
        self.assertTrue(noted[2].startswith('Moth said: "one more thing"'),
                        noted[2])

    def test_forgotten_before_the_reply_arrives(self):
        self.real_turn(self.patron, "one more thing", self.REPLY,
                       while_replying=lambda: self.forget("moth"),
                       mode="radio")
        self.assertIsNone(get_assigned_name(self.npc, self.patron))
        self.assertEqual(self.noted_under(self.gravelly), [])
        self.assertEqual(self.held(self.gravelly), NOTHING)


class TestAReplyThatBeganBeforeHePlacedTheVoice(_OnTheAir):
    """The one late reply that only this change stops. An unfamiliar
    gravelly voice calls, and Sully's answer takes time. While it is
    on its way he meets Moth and names them, hears the gravelly voice
    again and places it, and is then made to forget Moth. The reply
    that was on its way was written for a stranger: it carries nobody's
    name, so the check on the name has nothing to ask. It is filed
    under a voice he has just forgotten, and is not written down."""

    REPLY = {"speech": "Go ahead.", "tool": "none"}

    def setUp(self):
        super().setUp()
        self.patron.execute_cmd("@voice description gravelly")
        self.gravelly = self.npc._radio_subject(self.patron)

    def meets_moth_and_places_the_voice(self):
        self.patron.execute_cmd("@voice clear")
        self.name(self.patron, "Moth")
        self.patron.execute_cmd("@voice description gravelly")
        self.assertEqual(self.npc._radio_subject(self.patron), self.gravelly)
        with mock.patch(ROLL, return_value=WON):
            self.assertEqual(self.npc._radio_voice_handle(self.patron),
                             "Moth")

    def noted_under_the_voice(self):
        return [rec["text"] for rec in self.npc._load_memories()
                if rec.get("subject") == self.gravelly]

    def test_with_no_forget_it_is_written_down_as_a_strangers(self):
        """The control: he placed the voice meanwhile and forgot
        nobody."""
        self.real_turn(self.patron, "anyone on this band?", self.REPLY,
                       while_replying=self.meets_moth_and_places_the_voice,
                       mode="radio")
        (noted,) = self.noted_under_the_voice()
        self.assertIn("anyone on this band?", noted)
        self.assertNotIn("Moth", noted)

    def test_forgotten_before_the_reply_arrives(self):
        def meanwhile():
            self.meets_moth_and_places_the_voice()
            self.forget("moth")

        self.real_turn(self.patron, "anyone on this band?", self.REPLY,
                       while_replying=meanwhile, mode="radio")
        self.assertIsNone(get_assigned_name(self.npc, self.patron))
        self.assertEqual(self.noted_under_the_voice(), [])


# ----------------------------------------------------------------------
# What the observer is told, and who is asked
# ----------------------------------------------------------------------

class TestWhatTheObserverIsToldAboutAPlacedVoice(_AVoiceBeforeItHasAName):
    def voices_told_on_erasing(self, uid):
        with mock.patch.object(type(self.npc), "at_looks_erased",
                               autospec=True) as told:
            erase_look(self.npc, uid)
        return told.call_args.args[2]

    def test_the_voice_he_placed_is_among_the_voices_that_went(self):
        self.assertEqual(
            self.voices_told_on_erasing(self.bare),
            {self.uid(self.plain), self.uid(self.gravelly)})

    def test_forgetting_somebody_else_does_not_report_it(self):
        self.assertEqual(
            self.voices_told_on_erasing(get_apparent_uid(self.other)),
            {self.uid(self.wren_voice)})


class TestAVoiceHeFailedToPlaceIsNotReported(_AVoiceBeforeItHasAName):
    DICE = LOST

    def test_only_the_named_voice_is(self):
        with mock.patch.object(type(self.npc), "at_looks_erased",
                               autospec=True) as told:
            erase_look(self.npc, self.bare)
        self.assertEqual(told.call_args.args[2], {self.uid(self.plain)})


class TestAPlayerWhoPlacedAVoiceForgetsAsBefore(_AVoiceBeforeItHasAName):
    """A player keeps no records of their own, and has no door to be
    told at. Wren names Moth, hears the gravelly voice and places it;
    forgetting the name works for her as it did."""

    def setUp(self):
        super().setUp()
        self.changes_voice("clear")
        self.other.voice_memory = {}
        self.other.db.voice_discern_cache = None
        self.other.execute_cmd("remember gaunt man as Moth")
        self.assertEqual(get_assigned_name(self.other, self.patron), "Moth")
        self.changes_voice("description gravelly")
        from world.voice import attempt_voice_discern
        with mock.patch(ROLL, return_value=WON):
            self.assertEqual(
                attempt_voice_discern(self.other, self.patron), "Moth")

    def test_she_forgets_and_nothing_else_is_asked_of_her(self):
        self.assertFalse(hasattr(self.other, "at_looks_erased"))
        self.assertEqual(self.uid(self.gravelly),
                         get_apparent_voice_uid(self.patron))
        self.assertIs(self.verdict(self.other), True)
        self.assertEqual(erase_look(self.other, self.bare), "Moth")
        self.assertIsNone(self.verdict(self.other))
        self.assertEqual(dict(self.other.voice_memory), {})
        self.assertEqual(dict(self.other.recognition_memory), {})


class TestWonVoiceVerdicts(_AVoiceBeforeItHasAName):
    """`world.voice.won_voice_verdicts`, by itself. It is imported
    where it is used: the function is new with this change, and the
    rest of this module has to load without it to be run against the
    code as it was."""

    def won(self, observer):
        from world.voice import won_voice_verdicts
        return won_voice_verdicts(observer)

    def test_the_changed_voice_he_placed(self):
        self.assertIn((self.patron.dbref, self.uid(self.gravelly)),
                      self.won(self.npc))

    def test_a_named_voice_he_heard_on_the_air_has_one_too(self):
        """A verdict is not only for a changed voice: Wren's own
        voice was told on the air by the entry that names it."""
        self.assertIn(self.uid(self.wren_voice), self.npc.voice_memory)
        self.assertIn((self.other.dbref, self.uid(self.wren_voice)),
                      self.won(self.npc))

    def test_a_named_voice_he_never_heard_unseen_has_none(self):
        self.assertIn(self.uid(self.plain), self.npc.voice_memory)
        self.assertNotIn(self.uid(self.plain),
                         {voice for _dbref, voice in self.won(self.npc)})

    def test_somebody_who_holds_none(self):
        self.assertEqual(self.won(self.other), set())


class TestAFailedAttemptIsNotAWonVerdict(_AVoiceBeforeItHasAName):
    DICE = LOST

    def test_it_is_not(self):
        from world.voice import won_voice_verdicts
        self.assertIs(self.verdict(), False)
        self.assertEqual(won_voice_verdicts(self.npc), set())
