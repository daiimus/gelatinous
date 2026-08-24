"""A BOLO is a claim, and what it's worth depends on who made it
(#2247).

`uid` is a 16-character hex digest of a presentation. `match_bolo` read
it as `high` — a positive identification — and there was exactly one
producer: `crime.py` called `build_bolo(perp)` and dropped it in the
event payload, where the responder read it directly. The identity never
travelled through any channel at all.

Which is the question that found this: how would anybody communicate a
uid over the radio? Nobody says a hex digest out loud. A witness can't.
Dispatch can't relay it. And crime witnesses are always CIVILIANS
(`spawn_witness`), so a bystander's glimpse was identifying people as
positively as a camera would.

Three tiers now, and only one of them may carry a hash:

    machine   a unit that saw it — data, not description. The precursor
              to the photo/video record that feeds cases and decking.
    witness   an NPC who really saw it — accurate, but still words.
    radio     a voice phoning in — vague, mistaken, or lying.

And separately: the SYSTEM still knows who actually did it, so a
wrong-person grab is legible to us and invisible to the robot.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.director.security import (
    build_bolo, is_the_right_person, match_bolo,
)


class _Case(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.perp = self.char1
        self.perp.height, self.perp.build = "tall", "heavyset"


class TestOnlyAMachineCarriesAHash(_Case):
    def test_a_machine_records_the_presentation(self):
        bolo = build_bolo(self.perp, via="machine")
        self.assertIsNotNone(bolo["uid"])
        self.assertEqual(bolo["via"], "machine")

    def test_a_witness_describes_and_does_not_identify(self):
        """An NPC who really saw it is ACCURATE — right height, right
        build — but a person cannot recite a hash."""
        bolo = build_bolo(self.perp, via="witness", by=self.char2)
        self.assertIsNone(bolo["uid"])
        self.assertEqual(bolo["height"], "tall")
        self.assertEqual(bolo["build"], "heavyset")
        self.assertEqual(bolo["by"], self.char2.key)

    def test_a_voice_on_the_radio_carries_least(self):
        bolo = build_bolo(self.perp, via="radio")
        self.assertIsNone(bolo["uid"])

    def test_an_unknown_channel_is_treated_as_the_weakest(self):
        self.assertEqual(build_bolo(self.perp, via="telepathy")["via"],
                         "radio")


class TestWhatAClaimIsWorth(_Case):
    def _suspect(self):
        self.char2.height, self.char2.build = "tall", "heavyset"
        return self.char2

    def test_a_machine_claim_can_identify(self):
        bolo = build_bolo(self.perp, via="machine")
        self.assertEqual(match_bolo(bolo, self.perp), "high")

    def test_a_witness_claim_never_identifies(self):
        """Same person, same silhouette — but a bystander's word is not
        an ID, and the unit gets a challenge rather than a certainty."""
        bolo = build_bolo(self.perp, via="witness")
        self.assertEqual(match_bolo(bolo, self.perp), "low")

    def test_a_forged_hash_off_a_person_is_refused(self):
        """A uid arriving by a channel that could not have carried it is
        a bug or a forgery. Forgery is meant to be the attack surface,
        not an accident."""
        bolo = build_bolo(self.perp, via="machine")
        bolo["via"] = "radio"                 # same hash, wrong mouth
        self.assertNotEqual(match_bolo(bolo, self.perp), "high")

    def test_a_lookalike_is_only_ever_a_low_match(self):
        bolo = build_bolo(self.perp, via="witness")
        self.assertEqual(match_bolo(bolo, self._suspect()), "low")


class TestTheSystemStillKnows(_Case):
    """The game's question, never the robot's."""

    class _Event:
        def __init__(self, source):
            self.source = source

    def test_it_knows_when_they_got_the_right_one(self):
        self.assertTrue(
            is_the_right_person(self._Event(self.perp), self.perp))

    def test_it_knows_when_they_got_a_lookalike(self):
        """The unit cannot tell — same height, same build, and a
        witness's word. The system can."""
        self.char2.height, self.char2.build = "tall", "heavyset"
        event = self._Event(self.perp)
        self.assertEqual(match_bolo(build_bolo(self.perp, via="witness"),
                                    self.char2), "low")
        self.assertFalse(is_the_right_person(event, self.char2))

    def test_a_sourceless_incident_is_unknowable_not_wrong(self):
        self.assertIsNone(is_the_right_person(self._Event(None), self.perp))


class TestTheRadioLaneAgrees(_Case):
    def test_a_phoned_in_description_declares_its_channel(self):
        from world.director.calls import describe_suspect
        bolo = describe_suspect("a tall heavyset guy did it")["bolo"]
        self.assertEqual(bolo["via"], "radio")
        self.assertIsNone(bolo["uid"])


class TestAUnitOnTheSpot(EvenniaCommandTest):
    """The one witness that can positively identify anybody.

    Crime witnesses were always civilians, so after provenance landed
    NOTHING could reach `high` — security could no longer identify
    anyone at all. A unit standing where it happened records the
    presentation instead of describing it, which is the precursor to
    the photo/video record that will feed cases and decking.
    """

    def setUp(self):
        super().setUp()
        self.perp = self.char1
        self.perp.height, self.perp.build = "tall", "heavyset"
        self.bot = self.char2
        self.bot.db.role = "security"
        self.bot.location = self.room1
        self.perp.location = self.room1

    def _report(self):
        from unittest import mock
        import world.director.crime as cmod
        cmod._RECENT.clear()
        with mock.patch("world.director.dispatch.raise_event",
                        return_value=[]) as raised, \
             mock.patch.object(cmod, "spawn_witness") as spawned:
            cmod.report_crime("assault", self.room1, perp=self.perp)
        return raised, spawned

    def test_a_unit_present_records_the_presentation(self):
        raised, _ = self._report()
        raised.assert_called_once()
        bolo = raised.call_args[0][0].payload["bolo"]
        self.assertEqual(bolo["via"], "machine")
        self.assertIsNotNone(bolo["uid"])
        self.assertEqual(bolo["by"], self.bot.key)

    def test_it_does_not_wait_for_a_crowd(self):
        """No witness roll, no report window: a machine standing there
        sees it, and does not hesitate or need to find a radio."""
        _, spawned = self._report()
        spawned.assert_not_called()

    def test_a_downed_unit_witnesses_nothing(self):
        self.bot.is_dead = lambda: True
        raised, spawned = self._report()
        raised.assert_not_called()
        spawned.assert_called_once()

    def test_the_perpetrator_is_not_its_own_witness(self):
        self.bot.db.role = None
        self.perp.db.role = "security"
        import world.director.crime as cmod
        cmod._RECENT.clear()
        # lawful force reports nothing at all
        self.assertFalse(cmod.report_crime("assault", self.room1,
                                           perp=self.perp))

    def test_with_no_unit_a_person_still_describes_it(self):
        self.bot.db.role = None
        raised, spawned = self._report()
        raised.assert_not_called()
        spawned.assert_called_once()


class TestWhatTheyWereWearing(EvenniaCommandTest):
    """The thing every witness leads with, and the thing a BOLO had
    nowhere to put (#2250).

    "A svelte lady in a black trenchcoat" gives ONE silhouette axis and
    a coat. Both axes were required, so the most recognisable fact
    about somebody counted for nothing and the units went in blind.
    """

    def setUp(self):
        super().setUp()
        self.perp = self.char1
        self.perp.height, self.perp.build = None, "slight"

    def _wearing(self, char, key, colour):
        from evennia import create_object
        item = create_object("typeclasses.items.Item", key=key,
                             location=char)
        item.color = colour
        char.get_worn_items = lambda location=None, _i=item: [_i]
        return item

    def test_a_caller_naming_a_coat_is_heard(self):
        from world.director.calls import describe_suspect
        bolo = describe_suspect(
            "a svelte lady in a black trenchcoat stabbed him")["bolo"]
        self.assertIn(("black", "trenchcoat"), bolo["worn"])
        self.assertEqual(bolo["build"], "slight")

    def test_half_a_silhouette_plus_the_coat_matches(self):
        """The exact case that was worthless before."""
        from world.director.calls import describe_suspect
        self._wearing(self.perp, "a battered trenchcoat", "black")
        bolo = describe_suspect(
            "a svelte lady in a black trenchcoat stabbed him")["bolo"]
        self.assertEqual(match_bolo(bolo, self.perp), "low")

    def test_the_wrong_coat_is_not_a_match(self):
        from world.director.calls import describe_suspect
        self._wearing(self.perp, "a battered trenchcoat", "red")
        bolo = describe_suspect(
            "a svelte lady in a black trenchcoat stabbed him")["bolo"]
        self.assertIsNone(match_bolo(bolo, self.perp))

    def test_changing_your_coat_defeats_it(self):
        """Clothes come off — that IS the point. This is the
        description a change of coat is supposed to beat."""
        from world.director.calls import describe_suspect
        bolo = describe_suspect(
            "a svelte lady in a black trenchcoat stabbed him")["bolo"]
        self._wearing(self.perp, "a grey cardigan", "grey")
        self.assertIsNone(match_bolo(bolo, self.perp))

    def test_a_colour_alone_is_not_a_description(self):
        """"Black" on its own is a mood, a night, or a joke."""
        from world.director.calls import describe_suspect
        got = describe_suspect("it's black as hell out here")
        self.assertFalse(got["bolo"])

    def test_a_bare_garment_still_counts(self):
        from world.director.calls import describe_suspect
        bolo = describe_suspect("a tall guy, he had a helmet on")["bolo"]
        self.assertIn(("", "helmet"), bolo["worn"])

    def test_a_machine_records_the_wardrobe_too(self):
        self._wearing(self.perp, "a battered trenchcoat", "black")
        bolo = build_bolo(self.perp, via="machine")
        self.assertIn(("black", "trenchcoat"), bolo["worn"])

    def test_both_axes_still_win_without_any_clothing(self):
        self.perp.height = "tall"
        bolo = build_bolo(self.perp, via="witness")
        self.assertEqual(match_bolo(bolo, self.perp), "low")
