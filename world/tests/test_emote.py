"""
Tests for the Dot-Pose Emote Engine (``world/emote.py``).

Unit tests for the tokenizer and per-observer renderer.  Uses mock
character objects to avoid Evennia dependencies, following the same
pattern as ``world/tests/test_communication.py``.

Run via::

    evennia test world.tests.test_emote

All test cases match the specification in ``specs/EMOTE_POSE_SPEC.md``
§Dot-Pose, §Token Model, and §Per-Observer Rendering Pipeline.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from world.emote import (
    CharRefToken,
    PronounToken,
    SpeechToken,
    TextToken,
    VerbToken,
    _find_char_ref_spans,
    _find_ordinal_char_ref_spans,
    _find_pronoun_spans,
    _should_conjugate,
    _split_speech_segments,
    build_char_candidates,
    render_dot_pose,
    render_emote,
    render_emote_for_observer,
    render_for_observer,
    tokenize_dot_pose,
    tokenize_emote,
)


# ===================================================================
# Helpers — lightweight character / room stand-in
# ===================================================================


def _make_character(
    *,
    key="Jorge Jackson",
    sex="male",
    height="tall",
    build="lean",
    sdesc_keyword=None,
    hair_color=None,
    hair_style=None,
    sleeve_uid="uid-abc-123",
    recognition_memory=None,
    is_builder=False,
):
    """Build a mock character with identity methods bound."""
    from typeclasses.characters import Character

    char = MagicMock(spec=Character)
    char.key = key
    char.sex = sex
    char.height = height
    char.build = build
    char.sdesc_keyword = sdesc_keyword
    char.hair_color = hair_color
    char.hair_style = hair_style
    char.sleeve_uid = sleeve_uid
    char.recognition_memory = (
        recognition_memory if recognition_memory is not None else {}
    )

    # Hands / clothing
    char.hands = {"left": None, "right": None}
    char.worn_items = {}

    def _coverage_map():
        coverage = {}
        if char.worn_items:
            for loc, items in char.worn_items.items():
                if items:
                    coverage[loc] = items[0]
        return coverage

    char._build_clothing_coverage_map = _coverage_map

    # Bind real methods
    char.get_distinguishing_feature = (
        lambda: Character.get_distinguishing_feature(char)
    )
    char.get_sdesc = lambda: Character.get_sdesc(char)
    char.get_display_name = (
        lambda looker=None, **kw: Character.get_display_name(
            char, looker, **kw
        )
    )

    # gender property
    sex_val = (sex or "ambiguous").lower().strip()
    if sex_val in ("male", "man", "masculine", "m"):
        type(char).gender = PropertyMock(return_value="male")
    elif sex_val in ("female", "woman", "feminine", "f"):
        type(char).gender = PropertyMock(return_value="female")
    else:
        type(char).gender = PropertyMock(return_value="neutral")

    # Builder permission mock
    if is_builder:
        char.locks.check_lockstring.return_value = True
    else:
        char.locks.check_lockstring.return_value = False

    return char


def _make_room(contents):
    """Build a mock room with the given contents list."""
    room = MagicMock()
    room.contents = contents
    return room


# ===================================================================
# Tests: Speech Splitting
# ===================================================================


class TestSplitSpeechSegments(TestCase):
    """Tests for _split_speech_segments."""

    def test_no_speech(self) -> None:
        result = _split_speech_segments("lean back and sigh.")
        self.assertEqual(result, [("lean back and sigh.", False)])

    def test_single_speech_block(self) -> None:
        result = _split_speech_segments('lean back. "Hello there."')
        self.assertEqual(
            result,
            [("lean back. ", False), ("Hello there.", True)],
        )

    def test_speech_first(self) -> None:
        result = _split_speech_segments('"Get down!" I shout.')
        self.assertEqual(
            result,
            [("Get down!", True), (" I shout.", False)],
        )

    def test_multiple_speech_blocks(self) -> None:
        result = _split_speech_segments('"Hey," I say, waving. "Over here!"')
        self.assertEqual(
            result,
            [
                ("Hey,", True),
                (" I say, waving. ", False),
                ("Over here!", True),
            ],
        )

    def test_unmatched_quote(self) -> None:
        """Unmatched opening quote treats rest as speech."""
        result = _split_speech_segments('lean back. "Hello there.')
        self.assertEqual(
            result,
            [("lean back. ", False), ("Hello there.", True)],
        )

    def test_empty_input(self) -> None:
        result = _split_speech_segments("")
        self.assertEqual(result, [])


# ===================================================================
# Tests: -ing Participle Detection
# ===================================================================


class TestShouldConjugate(TestCase):
    """Tests for _should_conjugate."""

    def test_regular_verb(self) -> None:
        self.assertTrue(_should_conjugate("lean"))

    def test_participle_not_conjugated(self) -> None:
        self.assertFalse(_should_conjugate("diving"))

    def test_participle_running(self) -> None:
        self.assertFalse(_should_conjugate("running"))

    def test_participle_waving(self) -> None:
        self.assertFalse(_should_conjugate("waving"))

    def test_ing_base_verb_bring(self) -> None:
        """'bring' ends in -ing but is a real verb — should conjugate."""
        self.assertTrue(_should_conjugate("bring"))

    def test_ing_base_verb_sing(self) -> None:
        self.assertTrue(_should_conjugate("sing"))

    def test_ing_base_verb_ring(self) -> None:
        self.assertTrue(_should_conjugate("ring"))

    def test_ing_base_verb_swing(self) -> None:
        self.assertTrue(_should_conjugate("swing"))


# ===================================================================
# Tests: Pronoun Span Detection
# ===================================================================


class TestFindPronounSpans(TestCase):
    """Tests for _find_pronoun_spans."""

    def test_finds_capital_I(self) -> None:
        spans = _find_pronoun_spans("text I say", [])
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0][2], "i")
        self.assertEqual(spans[0][3], "subject")

    def test_lowercase_i_ignored(self) -> None:
        """Lowercase 'i' should not match (only capital I)."""
        spans = _find_pronoun_spans("text i say", [])
        self.assertEqual(len(spans), 0)

    def test_finds_my(self) -> None:
        spans = _find_pronoun_spans("scratch my jaw", [])
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0][2], "my")
        self.assertEqual(spans[0][3], "possessive_adj")

    def test_finds_myself(self) -> None:
        spans = _find_pronoun_spans("dust myself off", [])
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0][2], "myself")
        self.assertEqual(spans[0][3], "reflexive")

    def test_word_boundary_prevents_partial(self) -> None:
        """'mine' inside 'undermine' should NOT match."""
        spans = _find_pronoun_spans("I undermine the argument", [])
        # Should find "I" but NOT "mine" inside "undermine"
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0][2], "i")

    def test_skips_claimed_spans(self) -> None:
        """Pronouns in already-claimed spans are skipped."""
        # "I" is at position 0-1; claim that span
        spans = _find_pronoun_spans("I lean", [(0, 1)])
        self.assertEqual(len(spans), 0)


# ===================================================================
# Tests: Tokenizer
# ===================================================================


class TestTokenizer(TestCase):
    """Tests for tokenize_dot_pose."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )

    def test_simple_verb_first(self) -> None:
        """'.lean back.' → VerbToken + TextToken."""
        tokens = tokenize_dot_pose("lean back.", self.actor)
        assert isinstance(tokens[0], VerbToken)
        self.assertEqual(tokens[0].base_form, "lean")
        assert isinstance(tokens[1], TextToken)
        self.assertEqual(tokens[1].text, " back.")

    def test_multiple_verbs(self) -> None:
        """'lean back and .sigh.' has two verbs."""
        tokens = tokenize_dot_pose("lean back and .sigh.", self.actor)
        verbs = [t for t in tokens if isinstance(t, VerbToken)]
        self.assertEqual(len(verbs), 2)
        self.assertEqual(verbs[0].base_form, "lean")
        self.assertEqual(verbs[1].base_form, "sigh")

    def test_speech_extraction(self) -> None:
        """Speech blocks become SpeechTokens."""
        tokens = tokenize_dot_pose(
            'lean back. "Hello there."', self.actor
        )
        speech_tokens = [t for t in tokens if isinstance(t, SpeechToken)]
        self.assertEqual(len(speech_tokens), 1)
        self.assertEqual(speech_tokens[0].text, "Hello there.")
        self.assertIs(speech_tokens[0].speaker, self.actor)

    def test_speech_first(self) -> None:
        """'"Get down!" I .shout' → speech, then pronoun, then verb."""
        tokens = tokenize_dot_pose(
            '"Get down!" I .shout', self.actor
        )
        # Should start with SpeechToken
        self.assertIsInstance(tokens[0], SpeechToken)
        # Should have a PronounToken for "I"
        pronouns = [t for t in tokens if isinstance(t, PronounToken)]
        self.assertEqual(len(pronouns), 1)
        self.assertEqual(pronouns[0].case, "subject")
        # Should have a VerbToken for "shout"
        verbs = [t for t in tokens if isinstance(t, VerbToken)]
        self.assertEqual(len(verbs), 1)
        self.assertEqual(verbs[0].base_form, "shout")

    def test_pronoun_detection(self) -> None:
        """'scratch at the stubble on my jaw' finds 'my'."""
        tokens = tokenize_dot_pose(
            "scratch at the stubble on my jaw", self.actor
        )
        pronouns = [t for t in tokens if isinstance(t, PronounToken)]
        self.assertEqual(len(pronouns), 1)
        self.assertEqual(pronouns[0].original, "my")
        self.assertEqual(pronouns[0].case, "possessive_adj")

    def test_verb_marker_vs_punctuation(self) -> None:
        """Final period is punctuation, not a verb marker."""
        tokens = tokenize_dot_pose("lean back.", self.actor)
        # Should NOT have a verb for the trailing period
        verbs = [t for t in tokens if isinstance(t, VerbToken)]
        self.assertEqual(len(verbs), 1)
        self.assertEqual(verbs[0].base_form, "lean")

    def test_empty_input(self) -> None:
        tokens = tokenize_dot_pose("", self.actor)
        self.assertEqual(tokens, [])

    def test_whitespace_only(self) -> None:
        tokens = tokenize_dot_pose("   ", self.actor)
        self.assertEqual(tokens, [])

    def test_char_reference_detection(self) -> None:
        """Character names in the room should produce CharRefTokens."""
        maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        # Actor knows Maria
        self.actor.recognition_memory = {
            "uid-maria": {"assigned_name": "Maria"},
        }
        tokens = tokenize_dot_pose(
            "nod at Maria", self.actor, [self.actor, maria]
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, maria)

    def test_multiple_speech_blocks(self) -> None:
        """Multiple speech blocks are each tokenized independently."""
        tokens = tokenize_dot_pose(
            '"Hey," I .say, .waving my hand. "Over here!"',
            self.actor,
        )
        speech_tokens = [t for t in tokens if isinstance(t, SpeechToken)]
        self.assertEqual(len(speech_tokens), 2)
        self.assertEqual(speech_tokens[0].text, "Hey,")
        self.assertEqual(speech_tokens[1].text, "Over here!")

    def test_pronoun_I_requires_uppercase(self) -> None:
        """Only capital 'I' matches as a pronoun, not lowercase 'i'."""
        tokens = tokenize_dot_pose("lean back, i think", self.actor)
        pronouns = [t for t in tokens if isinstance(t, PronounToken)]
        self.assertEqual(len(pronouns), 0)

    def test_first_word_pronoun_not_auto_verbed(self) -> None:
        """If first word is a pronoun like 'I', it's not auto-verbed."""
        tokens = tokenize_dot_pose("I .lean back", self.actor)
        # First token should be a PronounToken, not a VerbToken
        assert isinstance(tokens[0], PronounToken)
        self.assertEqual(tokens[0].case, "subject")


# ===================================================================
# Tests: Renderer — Actor Self-View
# ===================================================================


class TestRendererActorView(TestCase):
    """Tests for render_for_observer when observer is the actor."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )

    def test_simple_verb_first(self) -> None:
        """Actor sees 'You lean back.'"""
        tokens = tokenize_dot_pose("lean back.", self.actor)
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, "You lean back.")

    def test_multiple_verbs(self) -> None:
        """Actor sees 'You lean back and sigh.'"""
        tokens = tokenize_dot_pose(
            "lean back and .sigh.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, "You lean back and sigh.")

    def test_pronoun_transformation(self) -> None:
        """Actor sees 'your' for 'my'."""
        tokens = tokenize_dot_pose(
            "scratch at the stubble on my jaw.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(
            result, "You scratch at the stubble on your jaw."
        )

    def test_speech_preserved(self) -> None:
        """Speech content preserved verbatim."""
        tokens = tokenize_dot_pose(
            'lean back. "What a day."', self.actor
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertIn('"What a day."', result)

    def test_speech_first(self) -> None:
        """Actor sees '"Get down!" you shout.' (lowercase after speech)."""
        tokens = tokenize_dot_pose(
            '"Get down!" I .shout.', self.actor
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, '"Get down!" you shout.')

    def test_subsequent_I_becomes_lowercase_you(self) -> None:
        """First I → 'You', subsequent I → 'you'."""
        tokens = tokenize_dot_pose(
            'lean back and .sigh. "What a day," I .mutter.', self.actor
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(
            result,
            'You lean back and sigh. "What a day," you mutter.',
        )

    def test_auto_punctuation(self) -> None:
        """Period appended when missing."""
        tokens = tokenize_dot_pose("lean back", self.actor)
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, "You lean back.")

    def test_no_double_punctuation(self) -> None:
        """No extra period if input already ends with one."""
        tokens = tokenize_dot_pose("lean back.", self.actor)
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, "You lean back.")

    def test_exclamation_preserved(self) -> None:
        """Exclamation mark is terminal — no period added."""
        tokens = tokenize_dot_pose("lean back!", self.actor)
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, "You lean back!")

    def test_ing_participle_not_conjugated(self) -> None:
        """Participles pass through unconjugated."""
        tokens = tokenize_dot_pose(
            ".diving behind cover.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, "You diving behind cover.")

    def test_myself_becomes_yourself(self) -> None:
        """'myself' → 'yourself' for actor."""
        tokens = tokenize_dot_pose(
            "dust myself off.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, "You dust yourself off.")

    def test_char_ref_per_observer(self) -> None:
        """Actor sees character reference resolved from their perspective."""
        maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        self.actor.recognition_memory = {
            "uid-maria": {"assigned_name": "Maria"},
        }
        tokens = tokenize_dot_pose(
            "nod at Maria.", self.actor, [self.actor, maria]
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        self.assertEqual(result, "You nod at Maria.")


# ===================================================================
# Tests: Renderer — Observer View (known actor)
# ===================================================================


class TestRendererObserverKnown(TestCase):
    """Tests for render_for_observer when observer knows the actor."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.observer = _make_character(
            key="Alice Smith",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
            },
        )

    def test_simple_verb_conjugated(self) -> None:
        """Observer sees 'Jorge leans back.'"""
        tokens = tokenize_dot_pose("lean back.", self.actor)
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(result, "Jorge leans back.")

    def test_multiple_verbs_conjugated(self) -> None:
        """Observer sees 'Jorge leans back and sighs.'"""
        tokens = tokenize_dot_pose(
            "lean back and .sigh.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(result, "Jorge leans back and sighs.")

    def test_pronoun_third_person_male(self) -> None:
        """'my' → 'his' for male actor."""
        tokens = tokenize_dot_pose(
            "scratch at the stubble on my jaw.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(
            result, "Jorge scratches at the stubble on his jaw."
        )

    def test_subsequent_I_becomes_he(self) -> None:
        """First mention = name, subsequent I → 'he'."""
        tokens = tokenize_dot_pose(
            'lean back and .sigh. "What a day," I .mutter.',
            self.actor,
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(
            result,
            'Jorge leans back and sighs. "What a day," he mutters.',
        )

    def test_speech_first_known(self) -> None:
        """'"Get down!" Jorge shouts.'"""
        tokens = tokenize_dot_pose(
            '"Get down!" I .shout.', self.actor
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(result, '"Get down!" Jorge shouts.')

    def test_auto_punctuation_observer(self) -> None:
        tokens = tokenize_dot_pose("lean back", self.actor)
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(result, "Jorge leans back.")

    def test_ing_participle_not_conjugated_observer(self) -> None:
        """Participles pass through for observers too."""
        tokens = tokenize_dot_pose(
            '"Get down!" I .shout, .diving behind cover.',
            self.actor,
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(
            result, '"Get down!" Jorge shouts, diving behind cover.'
        )


# ===================================================================
# Tests: Renderer — Observer View (unknown actor, sees sdesc)
# ===================================================================


class TestRendererObserverUnknown(TestCase):
    """Tests when observer doesn't know the actor (sees sdesc)."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.observer = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    def test_sdesc_with_article_capitalized(self) -> None:
        """Observer sees 'A gaunt man leans back.'"""
        tokens = tokenize_dot_pose("lean back.", self.actor)
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(result, "A gaunt man leans back.")

    def test_subsequent_I_becomes_he_unknown(self) -> None:
        """First mention = sdesc, subsequent I → 'he'."""
        tokens = tokenize_dot_pose(
            'lean back and .sigh. "What a day," I .mutter.',
            self.actor,
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(
            result,
            'A gaunt man leans back and sighs. "What a day," he mutters.',
        )

    def test_speech_first_unknown(self) -> None:
        """'"Get down!" A gaunt man shouts.'"""
        tokens = tokenize_dot_pose(
            '"Get down!" I .shout.', self.actor
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(result, '"Get down!" A gaunt man shouts.')

    def test_pronoun_his_for_unknown_male(self) -> None:
        """'my' → 'his' regardless of recognition."""
        tokens = tokenize_dot_pose(
            "scratch at the stubble on my jaw.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertEqual(
            result, "A gaunt man scratches at the stubble on his jaw."
        )


# ===================================================================
# Tests: Renderer — Female Actor
# ===================================================================


class TestRendererFemaleActor(TestCase):
    """Tests with a female actor for pronoun gender correctness."""

    def setUp(self):
        self.actor = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        self.observer = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    def test_female_pronoun_she(self) -> None:
        """Subsequent I → 'she' for female actor."""
        tokens = tokenize_dot_pose(
            'lean back and .sigh. "What a day," I .mutter.',
            self.actor,
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertIn("she mutters", result)

    def test_female_possessive_her(self) -> None:
        """'my' → 'her' for female actor."""
        tokens = tokenize_dot_pose(
            "tuck my hair behind my ear.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertIn("her hair", result)
        self.assertIn("her ear", result)


# ===================================================================
# Tests: Renderer — Neutral Actor
# ===================================================================


class TestRendererNeutralActor(TestCase):
    """Tests with a neutral-gender actor for pronoun correctness."""

    def setUp(self):
        self.actor = _make_character(
            key="Alex Quinn",
            sex="neutral",
            height="average",
            build="athletic",
            sdesc_keyword="person",
            sleeve_uid="uid-alex",
        )
        self.observer = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    def test_neutral_pronoun_they(self) -> None:
        """Subsequent I → 'they' for neutral actor."""
        tokens = tokenize_dot_pose(
            'lean back. "What a day," I .mutter.',
            self.actor,
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertIn("they mutter", result)

    def test_neutral_possessive_their(self) -> None:
        """'my' → 'their' for neutral actor."""
        tokens = tokenize_dot_pose(
            "fold my arms.", self.actor
        )
        result = render_for_observer(tokens, self.actor, self.observer)
        self.assertIn("their arms", result)


# ===================================================================
# Tests: Character Reference Resolution
# ===================================================================


class TestCharacterReferences(TestCase):
    """Tests for character reference detection and per-observer rendering."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        # Actor knows Maria
        self.actor.recognition_memory = {
            "uid-maria": {"assigned_name": "Maria"},
        }

    def test_char_ref_observer_sees_sdesc(self) -> None:
        """Observer who doesn't know Maria sees her sdesc."""
        observer = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )
        tokens = tokenize_dot_pose(
            "nod at Maria.", self.actor,
            [self.actor, self.maria, observer],
        )
        result = render_for_observer(tokens, self.actor, observer)
        # Observer doesn't know either character
        self.assertIn("compact woman", result)
        self.assertIn("gaunt man", result)

    def test_char_ref_observer_knows_target(self) -> None:
        """Observer who knows Maria sees her assigned name."""
        observer = _make_character(
            key="Alice Smith",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
                "uid-maria": {"assigned_name": "Maria"},
            },
        )
        tokens = tokenize_dot_pose(
            "nod at Maria.", self.actor,
            [self.actor, self.maria, observer],
        )
        result = render_for_observer(tokens, self.actor, observer)
        self.assertEqual(result, "Jorge nods at Maria.")

    def test_word_boundary_prevents_man_in_woman(self) -> None:
        """'man' should not match inside 'woman'."""
        # Create a character with keyword "man"
        dan = _make_character(
            key="Dan Smith",
            sex="male",
            height="average",
            build="average",
            sdesc_keyword="man",
            sleeve_uid="uid-dan",
        )
        # Actor knows neither
        self.actor.recognition_memory = {}
        tokens = tokenize_dot_pose(
            "nod at compact woman.", self.actor,
            [self.actor, self.maria, dan],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        # Should find Maria (via "compact woman") but NOT Dan via "man"
        # inside "woman"
        if char_refs:
            for ref in char_refs:
                self.assertIs(ref.character, self.maria)


# ===================================================================
# Tests: Full Spec Examples
# ===================================================================


class TestSpecExamples(TestCase):
    """End-to-end tests matching the spec's example table."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.observer_known = _make_character(
            key="Alice Smith",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
            },
        )
        self.observer_unknown = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    def test_spec_example_lean_back(self) -> None:
        """'.lean back.' from the spec."""
        tokens = tokenize_dot_pose("lean back.", self.actor)
        # Actor
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.actor),
            "You lean back.",
        )
        # Known observer
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.observer_known),
            "Jorge leans back.",
        )
        # Unknown observer — "A gaunt man leans back."
        # (tall + lean = gaunt)
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.observer_unknown),
            "A gaunt man leans back.",
        )

    def test_spec_example_scratch_jaw(self) -> None:
        """'.scratch at the stubble on my jaw, "What day is it?" I .ask.'"""
        tokens = tokenize_dot_pose(
            'scratch at the stubble on my jaw, "What day is it?" I .ask.',
            self.actor,
        )
        # Actor
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.actor),
            'You scratch at the stubble on your jaw, "What day is it?" you ask.',
        )
        # Known observer
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.observer_known),
            'Jorge scratches at the stubble on his jaw, "What day is it?" he asks.',
        )
        # Unknown observer
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.observer_unknown),
            'A gaunt man scratches at the stubble on his jaw, "What day is it?" he asks.',
        )

    def test_spec_example_get_down(self) -> None:
        """'"Get down!" I .shout, .diving behind cover.'"""
        tokens = tokenize_dot_pose(
            '"Get down!" I .shout, .diving behind cover.',
            self.actor,
        )
        # Actor
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.actor),
            '"Get down!" you shout, diving behind cover.',
        )
        # Known observer
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.observer_known),
            '"Get down!" Jorge shouts, diving behind cover.',
        )
        # Unknown observer
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.observer_unknown),
            '"Get down!" A gaunt man shouts, diving behind cover.',
        )

    def test_spec_example_fold_arms(self) -> None:
        """'.fold my arms and .lean against the wall.'"""
        tokens = tokenize_dot_pose(
            "fold my arms and .lean against the wall.",
            self.actor,
        )
        # Actor
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.actor),
            "You fold your arms and lean against the wall.",
        )
        # Known observer
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.observer_known),
            "Jorge folds his arms and leans against the wall.",
        )

    def test_spec_example_hey_over_here(self) -> None:
        """'"Hey," I .say, .waving my hand. "Over here!"'"""
        tokens = tokenize_dot_pose(
            '"Hey," I .say, .waving my hand. "Over here!"',
            self.actor,
        )
        # Actor
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.actor),
            '"Hey," you say, waving your hand. "Over here!"',
        )
        # Known observer
        self.assertEqual(
            render_for_observer(tokens, self.actor, self.observer_known),
            '"Hey," Jorge says, waving his hand. "Over here!"',
        )


# ===================================================================
# Tests: Room Broadcast
# ===================================================================


class TestRenderDotPose(TestCase):
    """Tests for the render_dot_pose room broadcast function."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.observer = _make_character(
            key="Alice Smith",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
            },
        )

    def test_broadcast_sends_to_all(self) -> None:
        """All room occupants receive a message."""
        room = _make_room([self.actor, self.observer])
        tokens = tokenize_dot_pose("lean back.", self.actor)
        render_dot_pose(tokens, self.actor, room)
        self.actor.msg.assert_called_once()
        self.observer.msg.assert_called_once()

    def test_broadcast_respects_exclude(self) -> None:
        """Excluded characters don't receive messages."""
        room = _make_room([self.actor, self.observer])
        tokens = tokenize_dot_pose("lean back.", self.actor)
        render_dot_pose(tokens, self.actor, room, exclude=[self.actor])
        self.actor.msg.assert_not_called()
        self.observer.msg.assert_called_once()

    def test_broadcast_passes_type_pose(self) -> None:
        """Messages include type='pose' for death filter compat."""
        room = _make_room([self.observer])
        tokens = tokenize_dot_pose("lean back.", self.actor)
        render_dot_pose(tokens, self.actor, room)
        call_kwargs = self.observer.msg.call_args[1]
        self.assertEqual(call_kwargs.get("type"), "pose")
        self.assertIs(call_kwargs.get("from_obj"), self.actor)

    def test_broadcast_skips_non_msg_objects(self) -> None:
        """Objects without .msg() are silently skipped."""
        item = MagicMock(spec=[])  # No msg method
        room = _make_room([self.observer, item])
        tokens = tokenize_dot_pose("lean back.", self.actor)
        render_dot_pose(tokens, self.actor, room)
        self.observer.msg.assert_called_once()


# ===================================================================
# Tests: Build Char Candidates
# ===================================================================


class TestBuildCharCandidates(TestCase):
    """Tests for build_char_candidates."""

    def test_excludes_actor(self) -> None:
        """Actor should not appear in candidates."""
        actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        candidates = build_char_candidates(actor, [actor])
        self.assertEqual(len(candidates), 0)

    def test_includes_display_name(self) -> None:
        """Candidates include the display name as seen by actor."""
        actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        actor.recognition_memory = {
            "uid-maria": {"assigned_name": "Maria"},
        }
        candidates = build_char_candidates(actor, [actor, maria])
        names = [name for name, _char, _rc in candidates]
        self.assertIn("Maria", names)

    def test_sorted_longest_first(self) -> None:
        """Candidates are sorted by name length, longest first."""
        actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        candidates = build_char_candidates(actor, [actor, maria])
        lengths = [len(name) for name, _char, _rc in candidates]
        self.assertEqual(lengths, sorted(lengths, reverse=True))


# ===================================================================
# Tests: Edge Cases
# ===================================================================


class TestEdgeCases(TestCase):
    """Edge cases from the spec."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )

    def test_ellipsis_not_verb_marker(self) -> None:
        """'...' should not produce verb markers."""
        tokens = tokenize_dot_pose("lean back...", self.actor)
        verbs = [t for t in tokens if isinstance(t, VerbToken)]
        # Should only find "lean" (auto-verb), not anything from "..."
        self.assertEqual(len(verbs), 1)
        self.assertEqual(verbs[0].base_form, "lean")

    def test_speech_pronouns_not_detected(self) -> None:
        """Pronouns inside speech should not be tokenized."""
        tokens = tokenize_dot_pose(
            '.say "I am the best" to everyone.', self.actor
        )
        pronouns = [t for t in tokens if isinstance(t, PronounToken)]
        # The "I" inside quotes should NOT be detected
        self.assertEqual(len(pronouns), 0)

    def test_speech_verb_markers_not_detected(self) -> None:
        """Verb markers inside speech should not be tokenized."""
        tokens = tokenize_dot_pose(
            '.say "I .lean back" to everyone.', self.actor
        )
        verbs = [t for t in tokens if isinstance(t, VerbToken)]
        # Should only find "say" (auto-verb), not ".lean" inside speech
        self.assertEqual(len(verbs), 1)
        self.assertEqual(verbs[0].base_form, "say")

    def test_ending_with_quote_no_extra_period(self) -> None:
        """Emote ending with speech quote should not get extra period."""
        tokens = tokenize_dot_pose(
            '.say "Hello there."', self.actor
        )
        result = render_for_observer(tokens, self.actor, self.actor)
        # Should end with the closing quote, no extra period
        self.assertTrue(result.endswith('"'))

    def test_capitalization_of_sdesc_article(self) -> None:
        """Sdesc starting a sentence gets article capitalized."""
        observer = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )
        tokens = tokenize_dot_pose("lean back.", self.actor)
        result = render_for_observer(tokens, self.actor, observer)
        # Should start with "A" (capitalized article)
        self.assertTrue(result.startswith("A "))


# ===================================================================
# Tests: Traditional Emote — tokenize_emote / render_emote
# ===================================================================


class TestTokenizeEmote(TestCase):
    """Tests for tokenize_emote (char-ref-only tokenizer)."""

    def setUp(self) -> None:
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="stocky",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )

    def test_no_char_refs(self) -> None:
        """Plain text with no character references returns TextTokens."""
        tokens = tokenize_emote("leans back.", self.actor, [])
        self.assertTrue(all(isinstance(t, TextToken) for t in tokens))
        self.assertEqual(
            "".join(t.text for t in tokens if isinstance(t, TextToken)),
            "leans back.",
        )

    def test_char_ref_detected(self) -> None:
        """Character reference by sdesc descriptor+keyword is detected."""
        tokens = tokenize_emote(
            "nods at squat woman.", self.actor, [self.maria]
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertEqual(char_refs[0].character, self.maria)

    def test_speech_exempt(self) -> None:
        """Character names inside quoted speech are not tokenized."""
        tokens = tokenize_emote(
            'says "I saw squat woman earlier."',
            self.actor,
            [self.maria],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 0)
        # The speech block should be a SpeechToken
        speech = [t for t in tokens if isinstance(t, SpeechToken)]
        self.assertEqual(len(speech), 1)
        self.assertIn("squat woman", speech[0].text)

    def test_char_ref_outside_speech(self) -> None:
        """Char ref outside speech is detected even with speech nearby."""
        tokens = tokenize_emote(
            'nods at squat woman. "Hello."',
            self.actor,
            [self.maria],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertEqual(char_refs[0].character, self.maria)

    def test_no_verbs_or_pronouns_detected(self) -> None:
        """tokenize_emote does NOT detect verbs or pronouns."""
        tokens = tokenize_emote(
            "scratches my jaw and .sighs.",
            self.actor,
            [self.maria],
        )
        # Should have no VerbToken or PronounToken
        self.assertFalse(
            any(isinstance(t, (VerbToken, PronounToken)) for t in tokens)
        )

    def test_empty_input(self) -> None:
        """Empty input returns empty token list."""
        tokens = tokenize_emote("", self.actor, [])
        self.assertEqual(tokens, [])

    def test_whitespace_only(self) -> None:
        """Whitespace-only input returns empty token list."""
        tokens = tokenize_emote("   ", self.actor, [])
        self.assertEqual(tokens, [])


class TestRenderEmoteForObserver(TestCase):
    """Tests for render_emote_for_observer."""

    def setUp(self) -> None:
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="stocky",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )

    def test_actor_sees_own_name_prepended(self) -> None:
        """Actor sees own .key prepended (NOT 'You')."""
        tokens = tokenize_emote("leans back.", self.actor, [])
        result = render_emote_for_observer(tokens, self.actor, self.actor)
        self.assertIn("Jorge Jackson", result)
        self.assertIn("leans back.", result)

    def test_unknown_observer_sees_sdesc(self) -> None:
        """Observer who doesn't know actor sees sdesc."""
        observer = _make_character(
            key="Bob",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
        )
        tokens = tokenize_emote("leans back.", self.actor, [])
        result = render_emote_for_observer(tokens, self.actor, observer)
        self.assertIn("gaunt man", result.lower())
        self.assertTrue(result[0].isupper())

    def test_known_observer_sees_assigned_name(self) -> None:
        """Observer who assigned a name sees it prepended."""
        observer = _make_character(
            key="Bob",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
            },
        )
        tokens = tokenize_emote("waves.", self.actor, [])
        result = render_emote_for_observer(tokens, self.actor, observer)
        self.assertIn("Jorge waves.", result)

    def test_char_ref_resolved_per_observer(self) -> None:
        """Char ref in body is resolved using observer's memory."""
        # Observer knows Maria
        observer = _make_character(
            key="Bob",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={
                "uid-maria": {"assigned_name": "Maria"},
            },
        )
        tokens = tokenize_emote(
            "nods at squat woman.", self.actor, [self.maria]
        )
        result = render_emote_for_observer(tokens, self.actor, observer)
        self.assertIn("Maria", result)
        self.assertIn("nods at", result)

    def test_char_ref_unknown_observer_sees_sdesc(self) -> None:
        """Observer who doesn't know target sees target's sdesc."""
        observer = _make_character(
            key="Bob",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
        )
        tokens = tokenize_emote(
            "nods at squat woman.", self.actor, [self.maria]
        )
        result = render_emote_for_observer(tokens, self.actor, observer)
        self.assertIn("squat woman", result.lower())
        self.assertNotIn("Maria", result)

    def test_speech_preserved_in_rendering(self) -> None:
        """Speech blocks pass through unchanged in rendered output."""
        tokens = tokenize_emote(
            'says "Hello there."', self.actor, [self.maria]
        )
        result = render_emote_for_observer(tokens, self.actor, self.actor)
        self.assertIn('"Hello there."', result)


# ===================================================================
# Tests: Descriptor-Only Matching with Capital Gate (Bug 1)
# ===================================================================


class TestDescriptorOnlyMatching(TestCase):
    """Tests for physical descriptor-only character references.

    Physical descriptors (e.g. ``"towering"``, ``"gaunt"``) are valid
    character references but require a leading capital letter to
    distinguish intentional references from ordinary adjective usage.
    """

    def setUp(self) -> None:
        self.actor = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.big_guy = _make_character(
            key="Viktor Kozlov",
            sex="male",
            height="tall",
            build="heavyset",
            sdesc_keyword="man",
            sleeve_uid="uid-viktor",
        )

    def test_capitalized_descriptor_matches(self) -> None:
        """'Massive' (capitalized) matches the character."""
        tokens = tokenize_dot_pose(
            "flick a nod at Massive.",
            self.actor,
            [self.actor, self.big_guy],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.big_guy)

    def test_lowercase_descriptor_does_not_match(self) -> None:
        """'massive' (lowercase) does NOT match as a character ref."""
        tokens = tokenize_dot_pose(
            "look at the massive building.",
            self.actor,
            [self.actor, self.big_guy],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 0)

    def test_descriptor_keyword_still_works_lowercase(self) -> None:
        """'man' (keyword) still matches lowercase as before."""
        tokens = tokenize_dot_pose(
            "nod at man.",
            self.actor,
            [self.actor, self.big_guy],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.big_guy)

    def test_full_sdesc_still_works_lowercase(self) -> None:
        """'massive man' (full sdesc) still matches lowercase."""
        tokens = tokenize_dot_pose(
            "nod at massive man.",
            self.actor,
            [self.actor, self.big_guy],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.big_guy)

    def test_descriptor_in_candidates(self) -> None:
        """build_char_candidates includes descriptor with capital gate."""
        candidates = build_char_candidates(
            self.actor, [self.actor, self.big_guy]
        )
        descriptor_candidates = [
            (name, rc)
            for name, char, rc in candidates
            if name == "massive"
        ]
        self.assertEqual(len(descriptor_candidates), 1)
        # The descriptor candidate requires capital
        self.assertTrue(descriptor_candidates[0][1])

    def test_traditional_emote_descriptor_capitalized(self) -> None:
        """Traditional emote: 'nods at Massive' resolves correctly."""
        tokens = tokenize_emote(
            "nods at Massive.",
            self.actor,
            [self.actor, self.big_guy],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.big_guy)

    def test_traditional_emote_descriptor_lowercase_no_match(self) -> None:
        """Traditional emote: 'stands by the massive wall' no match."""
        tokens = tokenize_emote(
            "stands by the massive wall.",
            self.actor,
            [self.actor, self.big_guy],
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 0)


# ===================================================================
# Tests: Ordinal Character References in Emotes (Bug 2)
# ===================================================================


class TestOrdinalCharRefsInEmotes(TestCase):
    """Tests for ordinal-prefixed character references in emotes.

    Patterns like ``"2nd man"`` should resolve to the second matching
    character in the room.
    """

    def setUp(self) -> None:
        self.actor = _make_character(
            key="Alice Smith",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-alice",
        )
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.viktor = _make_character(
            key="Viktor Kozlov",
            sex="male",
            height="tall",
            build="heavyset",
            sdesc_keyword="man",
            sleeve_uid="uid-viktor",
        )
        self.occupants = [self.actor, self.jorge, self.viktor]

    def test_dot_pose_2nd_man(self) -> None:
        """'.flick a nod at 2nd man' resolves to Viktor."""
        tokens = tokenize_dot_pose(
            "flick a nod at 2nd man.",
            self.actor,
            self.occupants,
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.viktor)

    def test_dot_pose_1st_man(self) -> None:
        """'.nod at 1st man' resolves to Jorge."""
        tokens = tokenize_dot_pose(
            "nod at 1st man.",
            self.actor,
            self.occupants,
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.jorge)

    def test_dot_pose_ordinal_out_of_range(self) -> None:
        """'.nod at 3rd man' with only 2 men: ordinal fails, 'man' matches 1st."""
        tokens = tokenize_dot_pose(
            "nod at 3rd man.",
            self.actor,
            self.occupants,
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        # The ordinal fails (no 3rd man), but "man" still matches
        # via regular char ref matching (picks the first: Jorge)
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.jorge)

    def test_traditional_emote_2nd_man(self) -> None:
        """'emote nods at 2nd man' resolves to Viktor."""
        tokens = tokenize_emote(
            "nods at 2nd man.",
            self.actor,
            self.occupants,
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.viktor)

    def test_ordinal_does_not_consume_non_ordinal(self) -> None:
        """Plain 'man' still works alongside ordinals."""
        tokens = tokenize_dot_pose(
            "nod at man.",
            self.actor,
            self.occupants,
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        # Should match the first man (Jorge) via regular matching
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.jorge)

    def test_ordinal_span_claimed(self) -> None:
        """Ordinal span is fully claimed — no double match on 'man'."""
        tokens = tokenize_dot_pose(
            "flick a nod at 2nd man.",
            self.actor,
            self.occupants,
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        # Only ONE char ref (the ordinal match), not two
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.viktor)

    def test_ordinal_rendering(self) -> None:
        """Ordinal char ref renders with resolved display name."""
        observer = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={
                "uid-viktor": {"assigned_name": "Vik"},
            },
        )
        tokens = tokenize_dot_pose(
            "flick a nod at 2nd man.",
            self.actor,
            self.occupants,
        )
        result = render_for_observer(tokens, self.actor, observer)
        # Observer knows Viktor as "Vik"
        self.assertIn("Vik", result)

    def test_ordinal_in_traditional_emote_rendering(self) -> None:
        """Ordinal in traditional emote renders correctly."""
        observer = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )
        tokens = tokenize_emote(
            "nods at 2nd man.",
            self.actor,
            self.occupants,
        )
        result = render_emote_for_observer(tokens, self.actor, observer)
        # Viktor's sdesc is "a massive man" (tall + heavyset)
        self.assertIn("massive man", result.lower())

    def test_ordinal_with_full_sdesc(self) -> None:
        """'2nd gaunt man' — only one gaunt man, ordinal fails but
        'gaunt man' falls through to regular matching and finds Jorge."""
        tokens = tokenize_dot_pose(
            "nod at 2nd gaunt man.",
            self.actor,
            self.occupants,
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        # Ordinal fails (only 1 gaunt man), but "gaunt man" matches Jorge
        # via regular char ref path.
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.jorge)

    def test_ordinal_zero_ignored(self) -> None:
        """'0th man' is not a valid ordinal and is ignored."""
        tokens = tokenize_dot_pose(
            "nod at 0th man.",
            self.actor,
            self.occupants,
        )
        char_refs = [t for t in tokens if isinstance(t, CharRefToken)]
        # "man" should still match via regular path (first match)
        self.assertEqual(len(char_refs), 1)
        self.assertIs(char_refs[0].character, self.jorge)
