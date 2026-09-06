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

The second half landed on OWNER RULING #2928: a stranger must NOT be
able to address an NPC by a true name they cannot know -- "that makes no
sense for RP". Real keys are now Builder-only, which is what
`IDENTITY_RECOGNITION_SPEC` §Target Resolution said all along; the
`test_bar` assertion that disagreed has been updated.
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


class TestANameYouCannotKnowDoesNot(_AddressCase):
    """OWNER RULING #2928: a stranger addressing an NPC by a true name
    they have no in-character way to know "makes no sense for RP".

    Live, only 6 of 78 of these NPCs present their name at all -- the
    rest read as "a lean woman in a thermal shirt" -- so the bare-key
    match let anyone first-name someone they had never met.
    `IDENTITY_RECOGNITION_SPEC` §Target Resolution blocks real keys for
    non-Builders; `test_bar` asserted the opposite for address, and the
    spec won."""

    def test_the_true_name_is_not_a_handle_for_a_stranger(self):
        self.assertFalse(self.named("Jordan St. Rivera, a drink"))

    def test_nor_the_first_name(self):
        self.assertFalse(self.named("Jordan, a drink"))

    def test_but_a_name_they_have_assigned_is(self):
        self.assertTrue(self.named("Jordan, a drink",
                                   known="Jordan St. Rivera"))


class TestBuildersKeepTheRealKey(_AddressCase):
    """The carve-out the spec reserves, so staff can drive NPCs while
    testing."""

    def _make_builder(self):
        # On the ACCOUNT: `perm()` resolves against the puppeting
        # account, so granting the character alone leaves the check
        # false and the test green for the wrong reason.
        self.speaker.permissions.add("Builder")
        if self.speaker.account:
            self.speaker.account.permissions.add("Builder")

    def test_a_builder_can_use_the_true_name(self):
        self._make_builder()
        self.assertTrue(self.named("Jordan St. Rivera, a drink"))

    def test_a_player_cannot(self):
        self.assertFalse(self.named("Jordan St. Rivera, a drink"))


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
