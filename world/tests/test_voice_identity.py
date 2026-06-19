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
    garbled_voice_phrase,
    get_voice_descriptions,
    get_voice_endings,
    has_voice_signature,
    is_valid_voice_description,
    is_valid_voice_ending,
    is_voice_garbled,
    voice_phrase,
)


class _FakeDB:
    def __init__(self, description=None, ending=None):
        self.voice_description = description
        self.voice_ending = ending


class _FakeMedicalState:
    def __init__(self, talking=1.0):
        self._talking = talking

    def calculate_body_capacity(self, name):
        if name == "talking":
            return self._talking
        return 1.0


class _FakeChar:
    def __init__(self, description=None, ending=None, talking=1.0,
                 medical=True):
        self.db = _FakeDB(description, ending)
        self.medical_state = _FakeMedicalState(talking) if medical else None


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


class CommandRegistrationTests(TestCase):
    """@voice is wired into the live character cmdset (runs under the evennia
    test harness, which bootstraps the command framework)."""

    def test_voice_command_registered(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        keys = {c.key for c in cs.commands}
        self.assertIn("@voice", keys)
