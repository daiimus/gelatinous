"""Addressing an NPC asks what targeting asks (#2429, #2451).

`_mentions_self` tested `self.key` as a bare substring, which was wrong
in both directions at once.

TOO LITTLE: only the COMPLETE key counted. "Jordan, what's worth drinking
here?" was ignored; "Jordan St. Rivera, ..." got an immediate answer.
53 of 78 LLM NPCs were in that state. Mononyms worked because the whole
key IS the first name -- Sable, Sully, Petra, Vesper -- and those are the
ones that get demoed, which is why it went unnoticed.

This change is ADDITIVE: the key, the keyword and the job's words all
still count, and on top of them a speaker may use any handle the game
already lets them TARGET with -- `world.search.is_identity_match`, the
resolver behind `look` and `attack`.

A second finding came out of the same reading and is deliberately NOT
fixed here. The bare-key match means a stranger can address an NPC by a
true name they cannot know; live, only 6 of 78 of these NPCs present
their name at all. `IDENTITY_RECOGNITION_SPEC` blocks real keys for
non-Builders, while `test_bar` asserts the opposite for address in as
many words. A spec and a deliberate test disagree -- that is a ruling,
not a bugfix.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest


class _AddressCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = self.char1
        self.npc.swap_typeclass("typeclasses.llm_npc.LLMNpc",
                                clean_attributes=False,
                                run_start_hooks="all")
        self.npc.key = "Jordan St. Rivera"
        self.speaker = self.char2
        for c in (self.npc, self.speaker):
            c.location = self.room1
        # the post's words are public; the person's name is not
        self.aliases = ["bartender", "barkeep"]
        patcher = mock.patch.object(type(self.npc), "_name_aliases",
                                    return_value=self.aliases)
        patcher.start()
        self.addCleanup(patcher.stop)

    def named(self, line, known=None, sdesc=None):
        """Does *line* address the NPC, given what the speaker knows?"""
        with mock.patch("world.identity.get_assigned_name",
                        return_value=known), \
             mock.patch.object(type(self.npc), "get_sdesc",
                               return_value=(sdesc or "a lean man in a "
                                             "canvas apron")):
            return self.npc._mentions_self(line, self.speaker)


class TestTheJobsWordsArePublic(_AddressCase):
    def test_bartender_reaches_whoever_stands_the_bar(self):
        self.assertTrue(self.named("bartender, a drink"))

    def test_so_does_an_alias(self):
        self.assertTrue(self.named("hey barkeep, what's good"))

    def test_an_unrelated_line_does_not(self):
        self.assertFalse(self.named("this place is loud"))


class TestANameYouKnowWorks(_AddressCase):
    """The reported complaint: a first name has to work for someone who
    knows the name."""

    KNOWN = "Jordan St. Rivera"

    def test_the_first_name_alone(self):
        self.assertTrue(self.named("Jordan, what's worth drinking here?",
                                   known=self.KNOWN))

    def test_the_surname_alone(self):
        self.assertTrue(self.named("hey st. rivera", known=self.KNOWN))

    def test_the_full_name(self):
        self.assertTrue(self.named("Jordan St. Rivera, a drink",
                                   known=self.KNOWN))

    def test_the_name_at_the_end(self):
        self.assertTrue(self.named("what's worth drinking here, Jordan?",
                                   known=self.KNOWN))

    def test_a_different_name_does_not(self):
        self.assertFalse(self.named("Ottilie, over here", known=self.KNOWN))


class TestWhatTheSpeakerCanSeeAlsoWorks(_AddressCase):
    def test_a_descriptor_is_a_handle(self):
        """It is what the room shows them, so it is public."""
        self.assertTrue(self.named("hey, canvas apron",
                                   sdesc="a lean man in a canvas apron"))


class TestTheBareKeyStillMatches(_AddressCase):
    """NOT changed by this PR, and pinned so the change is visible if it
    ever is. A stranger can address an NPC by a true name they have no
    in-character way to know -- only 6 of 78 of these NPCs present their
    name at all. `IDENTITY_RECOGNITION_SPEC` §Target Resolution blocks
    real keys for non-Builders, while
    `test_bar.test_off_shift_the_role_word_is_not_theirs` asserts the
    opposite for address. That conflict is an owner ruling (#2451), not
    something to settle in a bugfix."""

    def test_a_stranger_can_still_use_the_full_true_name(self):
        self.assertTrue(self.named("Jordan St. Rivera, a drink"))

    def test_but_the_first_name_alone_needs_acquaintance(self):
        """Which is exactly the asymmetry that made this look broken."""
        self.assertFalse(self.named("Jordan, a drink"))


class TestItDoesNotOverReach(_AddressCase):
    """Scanning every word would make any sentence containing a sdesc
    word address everyone it describes."""

    def test_a_sdesc_word_buried_mid_sentence_is_not_address(self):
        self.assertFalse(self.named(
            "some man told me the pumps are out and nobody has fixed them",
            sdesc="a lean man in a canvas apron"))

    def test_a_long_clause_before_a_comma_is_not_a_vocative(self):
        self.assertFalse(self.named(
            "the man who came in here yesterday with the apron, was he ok",
            sdesc="a lean man in a canvas apron"))

    def test_an_empty_line_is_not_address(self):
        self.assertFalse(self.named(""))

    def test_no_speaker_falls_back_to_the_public_words_only(self):
        self.assertTrue(self.npc._mentions_self("bartender, a drink", None))
        self.assertFalse(self.npc._mentions_self("Jordan, a drink", None))
