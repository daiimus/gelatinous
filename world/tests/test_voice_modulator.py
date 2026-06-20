"""
Tests for the voice-modulator augment ability
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §4.2).

The modulator is the audio parallel to a worn mask: toggling it sets
``voice_modulator_active``, which shifts the voice signature to a different
UID so listeners no longer recognise the voice. These tests drive the
``voice_modulator`` ability handler and confirm the recognition effect.

Run via::

    evennia test --keepdb world.tests.test_voice_modulator
"""

from types import SimpleNamespace
from unittest import TestCase

from world.medical.augments import _toggle_voice_modulator
from world.voice import (
    get_apparent_voice_uid,
    get_assigned_voice_name,
    is_voice_modulated,
    remember_voice,
)


class _Organ:
    def __init__(self):
        self.ability_state = {}


class _Char:
    def __init__(self, sleeve_uid="s1"):
        self.db = SimpleNamespace(voice_modulator_active=False)
        self.sleeve_uid = sleeve_uid
        self.voice_memory = {}


class VoiceModulatorToggleTests(TestCase):
    def test_toggle_sets_and_clears_flag(self):
        char, organ = _Char(), _Organ()
        self.assertFalse(is_voice_modulated(char))

        _toggle_voice_modulator(char, organ, "modulate", {})
        self.assertTrue(char.db.voice_modulator_active)
        self.assertTrue(is_voice_modulated(char))
        self.assertTrue(organ.ability_state["modulate"]["deployed"])

        _toggle_voice_modulator(char, organ, "modulate", {})
        self.assertFalse(char.db.voice_modulator_active)
        self.assertFalse(is_voice_modulated(char))
        self.assertFalse(organ.ability_state["modulate"]["deployed"])

    def test_custom_messages_used(self):
        char, organ = _Char(), _Organ()
        spec = {"deploy_msg": "DEPLOY!", "retract_msg": "RETRACT!"}
        self.assertEqual(
            _toggle_voice_modulator(char, organ, "modulate", spec), "DEPLOY!"
        )
        self.assertEqual(
            _toggle_voice_modulator(char, organ, "modulate", spec), "RETRACT!"
        )

    def test_modulation_changes_voice_uid(self):
        char, organ = _Char(), _Organ()
        bare = get_apparent_voice_uid(char)
        _toggle_voice_modulator(char, organ, "modulate", {})
        masked = get_apparent_voice_uid(char)
        self.assertNotEqual(bare, masked)

    def test_modulation_defeats_recognition(self):
        observer = _Char(sleeve_uid="obs")
        speaker, organ = _Char(sleeve_uid="spk"), _Organ()
        # Learn the speaker's natural voice...
        remember_voice(observer, speaker, "Bob")
        self.assertEqual(get_assigned_voice_name(observer, speaker), "Bob")
        # ...then they engage the modulator → unknown voice.
        _toggle_voice_modulator(speaker, organ, "modulate", {})
        self.assertIsNone(get_assigned_voice_name(observer, speaker))
        # Disengage → recognised again.
        _toggle_voice_modulator(speaker, organ, "modulate", {})
        self.assertEqual(get_assigned_voice_name(observer, speaker), "Bob")
