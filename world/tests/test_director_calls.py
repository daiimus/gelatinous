"""A call is a record, not a moment (#2246).

A phoned-in report used to be a `WorldEvent` held alive only by the
assignment referencing it — no object anywhere represented "the
incident reported at 17:48". You could not point at it, ask about it,
or close it.

The visible cost: a witnessed crime handed responders `build_bolo(perp)`
to match against, while a radio report handed them nothing, so a unit
swept the scene and emoted "finds nothing that matches its report" —
truthfully, because it had no report. The caller's own words were in
the event payload the whole time, unread.

Fidelity is deliberate. A voice on the radio can offer a SILHOUETTE and
never a presentation hash — nobody says a 16-character hex digest out
loud — so hearsay reads as "low" confidence at best.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.director.calls import describe_suspect
from world.director.security import match_bolo


class TestWhatTheCallerSaw(EvenniaCommandTest):
    def test_a_silhouette_is_read_from_ordinary_words(self):
        got = describe_suspect("a tall heavyset guy just decked someone")
        self.assertEqual(got["bolo"]["height"], "tall")
        self.assertEqual(got["bolo"]["build"], "heavyset")

    def test_it_never_carries_a_uid(self):
        """Nobody phones in a presentation hash."""
        got = describe_suspect("a tall heavyset man with a knife")
        self.assertIsNone(got["bolo"]["uid"])

    def test_the_callers_own_words_are_kept(self):
        """So she repeats what she was told instead of inventing a
        description — she once put "white male inside welfare gate" on
        the air unprompted (#2240)."""
        said = "a svelte lady in a black trenchcoat is stabbing someone"
        self.assertEqual(describe_suspect(said)["text"], said)

    def test_someone_is_a_report_with_no_description(self):
        """"Someone" is a FACT, not a blank: a person was involved and
        the unit is going in blind. Distinguishable from silence."""
        got = describe_suspect("someone's stabbing a man outside the Kettle")
        self.assertTrue(got["anonymous"])
        self.assertIsNone(got["bolo"])

    def test_a_described_person_is_not_anonymous(self):
        got = describe_suspect("a tall stocky woman is stabbing someone")
        self.assertFalse(got["anonymous"])

    def test_no_person_mentioned_at_all(self):
        got = describe_suspect("there's a fire in the stairwell")
        self.assertIsNone(got["bolo"])
        self.assertFalse(got["anonymous"])

    def test_empty_traffic_describes_nothing(self):
        for said in ("", None):
            got = describe_suspect(said)
            self.assertIsNone(got["bolo"])
            self.assertEqual(got["text"], "")


class TestHearsayIsOnlyEverASilhouette(EvenniaCommandTest):
    """What a described BOLO is worth when a unit arrives."""

    def _suspect(self, height, build):
        self.char2.height = height
        self.char2.build = build
        return self.char2

    def test_a_full_description_gets_a_low_match(self):
        bolo = describe_suspect("a tall heavyset man, he's got a knife")["bolo"]
        self.assertEqual(match_bolo(bolo, self._suspect("tall", "heavyset")),
                         "low")

    def test_never_high_from_hearsay(self):
        """A uid means "this is the presentation I saw". A caller
        cannot supply one, so a phoned-in BOLO can never positively
        identify anybody."""
        bolo = describe_suspect("a tall heavyset man")["bolo"]
        self.assertNotEqual(match_bolo(bolo, self._suspect("tall", "heavyset")),
                            "high")

    def test_a_vague_description_matches_nobody(self):
        """"A svelte lady" is half a silhouette, and `match_bolo` wants
        both axes. Owner ruling: if the description is poor, the units
        are just hoping to catch the person in the act."""
        bolo = describe_suspect("a svelte lady stabbed him")["bolo"]
        self.assertIsNone(match_bolo(bolo, self._suspect("tall", "slight")))

    def test_the_wrong_silhouette_is_not_a_match(self):
        bolo = describe_suspect("a short stocky man did it")["bolo"]
        self.assertIsNone(match_bolo(bolo, self._suspect("tall", "slight")))


class TestTheLedger(EvenniaCommandTest):
    def test_a_call_opens_rolls_and_closes(self):
        from world.director import calls as mod
        call = mod.open_call(said="shots fired on Volta", kind="assault",
                             room=self.room1, caller=self.char1,
                             suspect=describe_suspect("a tall stocky man"))
        self.assertTrue(call.get("id"))
        self.assertEqual(call["status"], "open")
        self.assertEqual(call["room"], self.room1.id)

        mod.record_dispatch(call["id"], [self.char2])
        self.assertEqual(mod.get_call(call["id"])["status"], "rolling")
        self.assertIn(self.char2.id, mod.get_call(call["id"])["units"])

        # the half that never existed: a responder finding nothing had
        # nowhere to say so, so a false report left no trace at all
        mod.close_call(call["id"], "unfounded", by=self.char2)
        closed = mod.get_call(call["id"])
        self.assertEqual(closed["status"], "unfounded")
        self.assertEqual(closed["closed_by"], self.char2.key)
        self.assertNotIn(closed, mod.open_calls())

    def test_a_call_with_nobody_free_says_so(self):
        from world.director import calls as mod
        call = mod.open_call(said="fire", kind="fire", room=self.room1)
        mod.record_dispatch(call["id"], [])
        self.assertEqual(mod.get_call(call["id"])["status"], "no units")

    def test_the_caller_is_kept_by_voice_not_face(self):
        """Dispatch never SAW them — attribution must not leak a visual
        identity into a radio record."""
        from world.director import calls as mod
        call = mod.open_call(said="help", kind="assault", room=self.room1,
                             caller=self.char1)
        self.assertNotEqual(call.get("voice"), self.char1.key)
