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
    GENERIC_UNSEEN_SPEAKER,
    VOICE_GARBLE_THRESHOLD,
    attempt_voice_discern,
    can_hear,
    can_see,
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
    resolve_speaker_attribution,
    voice_phrase,
)


class _FakeDB:
    def __init__(self, description=None, ending=None, modulated=False):
        self.voice_description = description
        self.voice_ending = ending
        self.voice_modulator_active = modulated
        # Evennia's db handler returns None for unset attributes; the discern
        # cache relies on that.
        self.voice_discern_cache = None


class _FakeMedicalState:
    def __init__(self, talking=1.0, sight=1.0, hearing=1.0, conditions=None):
        self._caps = {"talking": talking, "sight": sight, "hearing": hearing}
        self._conditions = conditions or {}

    def calculate_body_capacity(self, name):
        return self._caps.get(name, 1.0)

    def get_conditions_by_type(self, condition_type):
        return [object()] * self._conditions.get(condition_type, 0)


class _FakeChar:
    def __init__(self, description=None, ending=None, talking=1.0,
                 medical=True, sleeve_uid="sleeve-1", modulated=False,
                 sight=1.0, hearing=1.0, intellect=10, resonance=10,
                 dbref="#1", conditions=None, key="Speaker"):
        self.db = _FakeDB(description, ending, modulated)
        self.medical_state = (
            _FakeMedicalState(talking, sight, hearing, conditions)
            if medical else None
        )
        self.sleeve_uid = sleeve_uid
        self.voice_memory = {}
        self.intellect = intellect
        self.resonance = resonance
        self.dbref = dbref
        self.key = key

    def get_display_name(self, looker=None, **kwargs):
        return self.key


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


class PerceptionTests(TestCase):
    """can_see / can_hear capacity thresholds + override seams (§4.5)."""

    def test_full_senses(self):
        char = _FakeChar(sight=1.0, hearing=1.0)
        self.assertTrue(can_see(char))
        self.assertTrue(can_hear(char))

    def test_one_eye_one_ear_still_perceive(self):
        char = _FakeChar(sight=0.5, hearing=0.5)
        self.assertTrue(can_see(char))
        self.assertTrue(can_hear(char))

    def test_blind_and_deaf(self):
        char = _FakeChar(sight=0.0, hearing=0.0)
        self.assertFalse(can_see(char))
        self.assertFalse(can_hear(char))

    def test_override_conditions_restore_senses(self):
        from world.perception import (
            SIGHT_OVERRIDE_CONDITION, HEARING_OVERRIDE_CONDITION,
        )
        char = _FakeChar(
            sight=0.0, hearing=0.0,
            conditions={SIGHT_OVERRIDE_CONDITION: 1, HEARING_OVERRIDE_CONDITION: 1},
        )
        self.assertTrue(can_see(char))
        self.assertTrue(can_hear(char))

    def test_no_medical_model_fails_open(self):
        char = _FakeChar(medical=False)
        self.assertTrue(can_see(char))
        self.assertTrue(can_hear(char))


class VoiceDiscernmentTests(TestCase):
    """The discernment determination (mirrors disguise piercing, §4.5)."""

    def _observer(self, **kw):
        kw.setdefault("dbref", "#100")
        kw.setdefault("key", "Listener")
        return _FakeChar(**kw)

    def test_unknown_voice_not_discerned(self):
        observer = self._observer()
        speaker = _FakeChar(sleeve_uid="spk", dbref="#1")
        self.assertIsNone(attempt_voice_discern(observer, speaker))

    def test_garbled_speaker_not_discerned(self):
        observer = self._observer(intellect=1000)
        speaker = _FakeChar(sleeve_uid="spk", dbref="#1", resonance=1, talking=0.0)
        remember_voice(observer, speaker, "Bob")
        self.assertIsNone(attempt_voice_discern(observer, speaker))

    def test_no_sleeve_not_discerned(self):
        observer = self._observer()
        speaker = _FakeChar(sleeve_uid=None, dbref="#1")
        self.assertIsNone(attempt_voice_discern(observer, speaker))

    def test_strong_observer_discerns_known_voice(self):
        # Overwhelming intellect vs minimal resonance + familiarity → success
        # is deterministic (obs_roll>=1, +fam, vs tgt_roll==1).
        observer = self._observer(intellect=1000, hearing=1.0)
        speaker = _FakeChar(sleeve_uid="spk", dbref="#1", resonance=1)
        remember_voice(observer, speaker, "Bob")
        self.assertEqual(attempt_voice_discern(observer, speaker), "Bob")

    def test_hearing_capacity_gates_discernment(self):
        # Same overwhelming setup, but near-zero hearing collapses the
        # observer's side below the target's floor → deterministic failure.
        speaker = _FakeChar(sleeve_uid="spk", dbref="#1", resonance=1)
        deaf = self._observer(intellect=1000, hearing=0.0001, dbref="#101")
        remember_voice(deaf, speaker, "Bob")
        self.assertIsNone(attempt_voice_discern(deaf, speaker))

    def test_verdict_is_cached(self):
        observer = self._observer()
        speaker = _FakeChar(sleeve_uid="spk", dbref="#1", resonance=1)
        remember_voice(observer, speaker, "Bob")
        # Pre-seed a True verdict; the cached value is honoured (no re-roll).
        voice_uid = get_apparent_voice_uid(speaker)
        observer.db.voice_discern_cache = {("#1", voice_uid): True}
        self.assertEqual(attempt_voice_discern(observer, speaker), "Bob")
        # Flip the cached verdict → None, proving the cache is read.
        observer.db.voice_discern_cache = {("#1", voice_uid): False}
        self.assertIsNone(attempt_voice_discern(observer, speaker))

    def test_forget_clears_discern_cache(self):
        observer = self._observer(intellect=1000)
        speaker = _FakeChar(sleeve_uid="spk", dbref="#1", resonance=1)
        remember_voice(observer, speaker, "Bob")
        attempt_voice_discern(observer, speaker)  # populate cache
        self.assertTrue(observer.db.voice_discern_cache)
        forget_voice(observer, speaker)
        self.assertFalse(observer.db.voice_discern_cache)


class ResolutionChainTests(TestCase):
    """resolve_speaker_attribution: see -> hear -> neither (§4.5)."""

    def test_self_returns_own_key(self):
        char = _FakeChar(key="Me")
        self.assertEqual(resolve_speaker_attribution(char, char), "Me")

    def test_sighted_observer_uses_display_name(self):
        speaker = _FakeChar(key="Bob")
        observer = _FakeChar(sight=1.0, dbref="#100", key="Listener")
        self.assertEqual(resolve_speaker_attribution(speaker, observer), "Bob")

    def test_blind_hearing_discerns_known_voice(self):
        speaker = _FakeChar(key="Bob", sleeve_uid="spk", dbref="#1", resonance=1)
        observer = _FakeChar(
            sight=0.0, hearing=1.0, intellect=1000, dbref="#100", key="Listener"
        )
        remember_voice(observer, speaker, "Bob-voice")
        self.assertEqual(
            resolve_speaker_attribution(speaker, observer), "Bob-voice"
        )

    def test_blind_hearing_unknown_voice_is_generic(self):
        speaker = _FakeChar(key="Bob", sleeve_uid="spk", dbref="#1")
        observer = _FakeChar(sight=0.0, hearing=1.0, dbref="#100")
        self.assertEqual(
            resolve_speaker_attribution(speaker, observer),
            GENERIC_UNSEEN_SPEAKER,
        )

    def test_blind_and_deaf_is_generic(self):
        speaker = _FakeChar(key="Bob", sleeve_uid="spk", dbref="#1", resonance=1)
        observer = _FakeChar(
            sight=0.0, hearing=0.0, intellect=1000, dbref="#100"
        )
        remember_voice(observer, speaker, "Bob-voice")
        # Even with the voice remembered, no hearing → generic.
        self.assertEqual(
            resolve_speaker_attribution(speaker, observer),
            GENERIC_UNSEEN_SPEAKER,
        )


class CommandRegistrationTests(TestCase):
    """@voice is wired into the live character cmdset (runs under the evennia
    test harness, which bootstraps the command framework)."""

    def test_voice_command_registered(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        keys = {c.key for c in cs.commands}
        self.assertIn("@voice", keys)
