"""Cyber ears that pass the hearing gate must also weight the roll.

Regression pin for #2644.  Two doors onto one character's hearing, three
lines apart in the same call chain:

``world/voice.py:461`` gates on ``can_hear(observer)``, which honours the
``hearing_override`` condition — cyber ears restore hearing regardless of
organ state.  ``attempt_voice_discern`` then read the capacity **raw**::

    hearing = _read_capacity(observer, "hearing")
    if hearing is None:
        hearing = 1.0
    success = (obs_roll + familiarity) * hearing > (tgt_roll + penalty)

``calculate_body_capacity`` is documented as the *organ-only floor* and
consults no condition anywhere in ``world/medical/``.  So a character
whose organic hearing is destroyed reads ``0.0`` — a real float, not
``None``, so the fail-open branch never fires — and the multiplication
collapses their side to zero.  They hear the speech, which is the whole
point of the augment, and can never place a voice they know perfectly
well, however many times they have heard it.

Every other capacity consumer applies its override before reading the
capacity (``sight_hit_factor``, ``moving_dodge_factor``,
``manipulation_hit_factor`` in ``world/combat/capacity.py``).  This was
the one that did not.

Armed-unfired when filed: zero live objects carry ``hearing_override``.
The condition and the override branch both ship, so it fires the first
time a character installs cyber ears.
"""

from __future__ import annotations

from unittest import TestCase

from world import perception
from world.perception import HEARING_OVERRIDE_CONDITION, can_hear
from world.voice import attempt_voice_discern, remember_voice

from world.tests.test_voice_identity import _FakeChar


#: Destroyed organic ears, chrome ones fitted.
CHROME_EARS = {"hearing": 0.0, "conditions": {HEARING_OVERRIDE_CONDITION: 1}}


def _observer(**kw):
    kw.setdefault("dbref", "#100")
    kw.setdefault("key", "Listener")
    # Overwhelming intellect vs the speaker's minimal resonance makes the
    # determination deterministic: the only thing that can sink it is the
    # hearing multiplier.
    kw.setdefault("intellect", 1000)
    return _FakeChar(**kw)


def _speaker(dbref="#1"):
    return _FakeChar(sleeve_uid="spk", dbref=dbref, resonance=1)


class TestChromeEarsCanPlaceAVoice(TestCase):

    def test_chrome_ears_place_a_known_voice(self):
        """The defect: passes the gate, then multiplied by zero forever."""
        observer = _observer(**CHROME_EARS)
        speaker = _speaker()
        remember_voice(observer, speaker, "Bob")

        self.assertTrue(
            can_hear(observer),
            "fixture check — the override must open the gate",
        )
        self.assertEqual(
            attempt_voice_discern(observer, speaker), "Bob",
            "cyber ears heard the speech but could never place the voice: "
            "the roll was multiplied by the destroyed organ's 0.0",
        )

    # -- controls: the multiplier must still bite --------------------

    def test_destroyed_ears_without_chrome_still_cannot_place_a_voice(self):
        """The negative control. No override, no discernment."""
        observer = _observer(hearing=0.0, dbref="#101")
        speaker = _speaker()
        remember_voice(observer, speaker, "Bob")
        self.assertIsNone(attempt_voice_discern(observer, speaker))

    def test_intact_ears_place_a_known_voice(self):
        """The positive control. The harness can report a success."""
        observer = _observer(hearing=1.0, dbref="#102")
        speaker = _speaker()
        remember_voice(observer, speaker, "Bob")
        self.assertEqual(attempt_voice_discern(observer, speaker), "Bob")

    def test_chrome_ears_do_not_discern_a_voice_never_named(self):
        """The override restores hearing, not memory."""
        observer = _observer(dbref="#103", **CHROME_EARS)
        self.assertIsNone(attempt_voice_discern(observer, _speaker()))

    def test_chrome_ears_do_not_discern_a_garbled_speaker(self):
        """The override is on the listening side only."""
        observer = _observer(dbref="#104", **CHROME_EARS)
        speaker = _FakeChar(
            sleeve_uid="spk", dbref="#2", resonance=1, talking=0.0,
        )
        remember_voice(observer, speaker, "Bob")
        self.assertIsNone(attempt_voice_discern(observer, speaker))

    # -- the gate's own behaviour is unchanged -----------------------

    def test_can_hear_is_unchanged_across_every_state(self):
        """Routing ``can_hear`` through the multiplier is a no-op for it."""
        cases = (
            ("chrome ears over dead organs", CHROME_EARS, True),
            ("intact ears", {"hearing": 1.0}, True),
            ("one ear", {"hearing": 0.5}, True),
            ("destroyed ears", {"hearing": 0.0}, False),
            ("below the threshold", {"hearing": 0.1}, False),
            ("no medical model", {"medical": False}, True),
        )
        for label, kw, expected in cases:
            with self.subTest(label):
                self.assertIs(can_hear(_FakeChar(**kw)), expected)

    def test_the_multiplier_and_the_gate_read_one_door(self):
        """``hearing_multiplier`` is the shared read the fix introduces.

        Bound off the module rather than imported, so this file still
        LOADS against the unfixed tree — an import error would make every
        test above ERROR and destroy the control.
        """
        multiplier = getattr(perception, "hearing_multiplier", None)
        self.assertIsNotNone(
            multiplier, "world.perception.hearing_multiplier is missing",
        )
        self.assertEqual(multiplier(_FakeChar(**CHROME_EARS)), 1.0)
        self.assertEqual(multiplier(_FakeChar(hearing=0.0)), 0.0)
        self.assertEqual(multiplier(_FakeChar(hearing=0.5)), 0.5)
        self.assertEqual(multiplier(_FakeChar(medical=False)), 1.0)
