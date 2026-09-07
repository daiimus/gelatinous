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
    """A living host organ. `iter_abilities` needs `current_hp`,
    `data["abilities"]` and `ability_state` — a bare object with only
    `ability_state` looks like a body with no cyberware at all now that
    the effect is derived from the organ (#2484)."""

    def __init__(self, ability, ability_type, hp=10):
        self.current_hp = hp
        self.container = "head"
        self.data = {"abilities": {ability: {"type": ability_type}}}
        self.ability_state = {}


class _Char:
    def __init__(self, sleeve_uid="s1"):
        self.db = SimpleNamespace()
        self.sleeve_uid = sleeve_uid
        self.voice_memory = {}
        self.organ = _Organ("modulate", "voice_modulator")
        self.medical_state = SimpleNamespace(organs={"jaw": self.organ})


class VoiceModulatorToggleTests(TestCase):
    def test_toggle_engages_and_disengages(self):
        char = _Char()
        organ = char.organ
        self.assertFalse(is_voice_modulated(char))

        _toggle_voice_modulator(char, organ, "modulate", {})
        self.assertTrue(is_voice_modulated(char))
        self.assertTrue(organ.ability_state["modulate"]["deployed"])

        _toggle_voice_modulator(char, organ, "modulate", {})
        self.assertFalse(is_voice_modulated(char))
        self.assertFalse(organ.ability_state["modulate"]["deployed"])

    def test_a_destroyed_module_gives_the_voice_back(self):
        """The disguise used to be welded on: the module dies in place,
        no teardown hook runs, and the toggle can no longer find it
        (#2484)."""
        char = _Char()
        _toggle_voice_modulator(char, char.organ, "modulate", {})
        self.assertTrue(is_voice_modulated(char))
        char.organ.current_hp = 0
        self.assertFalse(is_voice_modulated(char))

    def test_custom_messages_used(self):
        char = _Char()
        organ = char.organ
        spec = {"deploy_msg": "DEPLOY!", "retract_msg": "RETRACT!"}
        self.assertEqual(
            _toggle_voice_modulator(char, organ, "modulate", spec), "DEPLOY!"
        )
        self.assertEqual(
            _toggle_voice_modulator(char, organ, "modulate", spec), "RETRACT!"
        )

    def test_modulation_changes_voice_uid(self):
        char = _Char()
        organ = char.organ
        bare = get_apparent_voice_uid(char)
        _toggle_voice_modulator(char, organ, "modulate", {})
        masked = get_apparent_voice_uid(char)
        self.assertNotEqual(bare, masked)

    def test_modulation_defeats_recognition(self):
        observer = _Char(sleeve_uid="obs")
        speaker = _Char(sleeve_uid="spk")
        organ = speaker.organ
        # Learn the speaker's natural voice...
        remember_voice(observer, speaker, "Bob")
        self.assertEqual(get_assigned_voice_name(observer, speaker), "Bob")
        # ...then they engage the modulator → unknown voice.
        _toggle_voice_modulator(speaker, organ, "modulate", {})
        self.assertIsNone(get_assigned_voice_name(observer, speaker))
        # Disengage → recognised again.
        _toggle_voice_modulator(speaker, organ, "modulate", {})
        self.assertEqual(get_assigned_voice_name(observer, speaker), "Bob")
