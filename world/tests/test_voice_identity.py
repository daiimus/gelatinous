"""
Tests for the voice-identity foundation
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §4, build slice 2a).

Covers the curated vocabulary + validation, the composed speech-flavour
phrase across signature states, and the ``talking``-capacity garble gate
(§4.7) — the first consumer of the otherwise-blocked ``talking`` capacity.

Run via::

    evennia test --keepdb world.tests.test_voice_identity
"""

from unittest import TestCase

from world.voice import (
    DEFAULT_VOICE_DESCRIPTIONS,
    DEFAULT_VOICE_ENDINGS,
    VOICE_GARBLE_THRESHOLD,
    forget_voice,
    garbled_voice_phrase,
    get_apparent_voice_uid,
    get_assigned_voice_name,
    get_voice_descriptions,
    get_voice_endings,
    get_voice_signature,
    has_voice_signature,
    is_valid_voice_description,
    is_valid_voice_ending,
    is_voice_garbled,
    remember_voice,
    voice_phrase,
)


class _FakeDB:
    def __init__(self, description=None, ending=None, modulated=False):
        self.voice_description = description
        self.voice_ending = ending
        self.voice_modulator_active = modulated


class _FakeMedicalState:
    def __init__(self, talking=1.0):
        self._talking = talking

    def calculate_body_capacity(self, name):
        if name == "talking":
            return self._talking
        return 1.0


class _FakeChar:
    def __init__(self, description=None, ending=None, talking=1.0,
                 medical=True, sleeve_uid="sleeve-1", modulated=False):
        self.db = _FakeDB(description, ending, modulated)
        self.medical_state = _FakeMedicalState(talking) if medical else None
        self.sleeve_uid = sleeve_uid
        self.voice_memory = {}


class VocabularyTests(TestCase):
    def test_defaults_are_nonempty_and_lowercase(self):
        self.assertTrue(DEFAULT_VOICE_DESCRIPTIONS)
        self.assertTrue(DEFAULT_VOICE_ENDINGS)
        for word in (*DEFAULT_VOICE_DESCRIPTIONS, *DEFAULT_VOICE_ENDINGS):
            self.assertEqual(word, word.lower())

    def test_getters_return_defaults_without_config(self):
        self.assertEqual(get_voice_descriptions(), DEFAULT_VOICE_DESCRIPTIONS)
        self.assertEqual(get_voice_endings(), DEFAULT_VOICE_ENDINGS)

    def test_validation_accepts_known_words(self):
        self.assertTrue(is_valid_voice_description("gravelly"))
        self.assertTrue(is_valid_voice_ending("drawl"))

    def test_validation_is_case_insensitive(self):
        self.assertTrue(is_valid_voice_description("GRAVELLY"))
        self.assertTrue(is_valid_voice_ending("  Drawl "))

    def test_validation_rejects_unknown_and_empty(self):
        self.assertFalse(is_valid_voice_description("xyzzy"))
        self.assertFalse(is_valid_voice_ending("xyzzy"))
        self.assertFalse(is_valid_voice_description(""))
        self.assertFalse(is_valid_voice_ending(""))


class SignatureCompositionTests(TestCase):
    def test_both_slots_compose_full_phrase(self):
        char = _FakeChar("gravelly", "drawl")
        self.assertEqual(
            voice_phrase(char), "speaking Common, in a gravelly drawl"
        )

    def test_description_only(self):
        char = _FakeChar("silken", None)
        self.assertEqual(
            voice_phrase(char), "speaking Common, in a silken voice"
        )

    def test_ending_only(self):
        char = _FakeChar(None, "rasp")
        self.assertEqual(voice_phrase(char), "speaking Common, in a rasp")

    def test_no_signature_returns_none(self):
        self.assertIsNone(voice_phrase(_FakeChar()))

    def test_language_slot_is_parameterised(self):
        char = _FakeChar("husky", "purr")
        self.assertIn("speaking Streetcant", voice_phrase(char, "Streetcant"))

    def test_has_voice_signature(self):
        self.assertTrue(has_voice_signature(_FakeChar("gravelly", None)))
        self.assertTrue(has_voice_signature(_FakeChar(None, "drawl")))
        self.assertFalse(has_voice_signature(_FakeChar()))


class TalkingGarbleGateTests(TestCase):
    def test_healthy_talking_not_garbled(self):
        self.assertFalse(is_voice_garbled(_FakeChar(talking=1.0)))
        self.assertIsNone(garbled_voice_phrase(_FakeChar(talking=1.0)))

    def test_wrecked_talking_garbles(self):
        char = _FakeChar("gravelly", "drawl", talking=0.1)
        self.assertTrue(is_voice_garbled(char))
        self.assertEqual(
            garbled_voice_phrase(char),
            "speaking Common, in a slurred, broken voice",
        )

    def test_threshold_boundary(self):
        # Exactly at threshold is NOT garbled (strict less-than).
        self.assertFalse(is_voice_garbled(_FakeChar(talking=VOICE_GARBLE_THRESHOLD)))
        self.assertTrue(
            is_voice_garbled(_FakeChar(talking=VOICE_GARBLE_THRESHOLD - 0.01))
        )

    def test_no_medical_model_fails_open(self):
        # No medical state => no garble (mobs, stubs).
        char = _FakeChar("gravelly", "drawl", medical=False)
        self.assertFalse(is_voice_garbled(char))
        self.assertIsNone(garbled_voice_phrase(char))


class VoiceRecognitionTests(TestCase):
    """The voice apparent-UID / voice-memory parallel (§4.2)."""

    def test_uid_is_stable_and_deterministic(self):
        a = _FakeChar("gravelly", "drawl", sleeve_uid="s1")
        b = _FakeChar("gravelly", "drawl", sleeve_uid="s1")
        self.assertEqual(get_apparent_voice_uid(a), get_apparent_voice_uid(b))
        self.assertEqual(len(get_apparent_voice_uid(a)), 16)

    def test_uid_salted_on_sleeve_even_without_flavour(self):
        # Everyone has a recognisable voice UID via sleeve_uid; flavour is
        # presentation, not identity.
        a = _FakeChar(sleeve_uid="s1")
        b = _FakeChar(sleeve_uid="s2")
        self.assertIsNotNone(get_apparent_voice_uid(a))
        self.assertNotEqual(get_apparent_voice_uid(a), get_apparent_voice_uid(b))

    def test_no_sleeve_uid_means_no_uid(self):
        self.assertIsNone(get_apparent_voice_uid(_FakeChar(sleeve_uid=None)))

    def test_modulator_changes_uid(self):
        bare = _FakeChar("gravelly", "drawl", sleeve_uid="s1", modulated=False)
        masked = _FakeChar("gravelly", "drawl", sleeve_uid="s1", modulated=True)
        self.assertNotEqual(
            get_apparent_voice_uid(bare), get_apparent_voice_uid(masked)
        )

    def test_signature_shape(self):
        char = _FakeChar("gravelly", "drawl", sleeve_uid="s1")
        self.assertEqual(
            get_voice_signature(char), ("s1", "gravelly", "drawl", False)
        )

    def test_remember_and_resolve(self):
        observer = _FakeChar(sleeve_uid="obs")
        speaker = _FakeChar("gravelly", "drawl", sleeve_uid="spk")
        self.assertIsNone(get_assigned_voice_name(observer, speaker))
        self.assertTrue(remember_voice(observer, speaker, "Bob"))
        self.assertEqual(get_assigned_voice_name(observer, speaker), "Bob")

    def test_remembered_voice_not_recognised_through_modulator(self):
        observer = _FakeChar(sleeve_uid="obs")
        speaker = _FakeChar("gravelly", "drawl", sleeve_uid="spk")
        remember_voice(observer, speaker, "Bob")
        # Same person switches on a modulator → unknown voice.
        speaker.db.voice_modulator_active = True
        self.assertIsNone(get_assigned_voice_name(observer, speaker))

    def test_cannot_remember_voiceless_target(self):
        observer = _FakeChar(sleeve_uid="obs")
        no_sleeve = _FakeChar(sleeve_uid=None)
        self.assertFalse(remember_voice(observer, no_sleeve, "Ghost"))

    def test_forget_voice(self):
        observer = _FakeChar(sleeve_uid="obs")
        speaker = _FakeChar("gravelly", "drawl", sleeve_uid="spk")
        remember_voice(observer, speaker, "Bob")
        self.assertTrue(forget_voice(observer, speaker))
        self.assertIsNone(get_assigned_voice_name(observer, speaker))


class CommandRegistrationTests(TestCase):
    """@voice is wired into the live character cmdset (runs under the evennia
    test harness, which bootstraps the command framework)."""

    def test_voice_command_registered(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        keys = {c.key for c in cs.commands}
        self.assertIn("@voice", keys)
