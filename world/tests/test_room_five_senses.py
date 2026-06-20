"""
Tests for perception-aware room descriptions — the five-senses framework
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §5).

`Room.get_display_desc` composes the room's description from only the sense
layers the looker can perceive: visual blob (when sighted) + authored
non-visual layers (auditory/olfactory/tactile/atmospheric) for senses they
still have. A blind looker loses the visual prose but reads the room by sound
/ smell / feel. Rooms with no sense layers + a sighted looker are unchanged.

The method only touches ``self.db.desc`` / ``self.db.sense_descs`` /
``self.SENSE_LAYER_ORDER`` and ``can_perceive_sense(looker)``, so it's driven
here with a stub ``self`` and stub lookers — no DB room needed.

Run via::

    evennia test --keepdb world.tests.test_room_five_senses
"""

from types import SimpleNamespace
from unittest import TestCase

from typeclasses.rooms import Room


def _room(desc="A neon-lit alley.", **sense_descs):
    return SimpleNamespace(
        db=SimpleNamespace(desc=desc, sense_descs=dict(sense_descs)),
        SENSE_LAYER_ORDER=Room.SENSE_LAYER_ORDER,
    )


class _Med:
    def __init__(self, sight=1.0, hearing=1.0):
        self._caps = {"sight": sight, "hearing": hearing}

    def calculate_body_capacity(self, name):
        return self._caps.get(name, 1.0)

    def get_conditions_by_type(self, condition_type):
        return []


def _looker(sight=1.0, hearing=1.0, medical=True):
    return SimpleNamespace(
        medical_state=_Med(sight, hearing) if medical else None
    )


def _desc(room, looker):
    return Room.get_display_desc(room, looker)


class FullSensesTests(TestCase):
    def test_sighted_hearing_gets_all_layers(self):
        room = _room(auditory="Sirens wail.", olfactory="Wet garbage.")
        out = _desc(room, _looker())
        self.assertEqual(out, "A neon-lit alley. Sirens wail. Wet garbage.")

    def test_no_sense_layers_is_just_visual(self):
        # Zero-regression: a plain room renders exactly its visual desc.
        self.assertEqual(
            _desc(_room(), _looker()), "A neon-lit alley."
        )


class BlindTests(TestCase):
    def test_blind_drops_visual_keeps_other_senses(self):
        room = _room(auditory="Sirens wail.", olfactory="Wet garbage.")
        out = _desc(room, _looker(sight=0.0))
        self.assertEqual(out, "Sirens wail. Wet garbage.")
        self.assertNotIn("neon-lit alley", out)

    def test_blind_with_no_other_senses_gets_void(self):
        out = _desc(_room(), _looker(sight=0.0))
        self.assertIn("can't see", out.lower())


class DeafTests(TestCase):
    def test_deaf_drops_auditory_only(self):
        room = _room(
            auditory="Sirens wail.", olfactory="Wet garbage.",
            tactile="Cold mist clings.",
        )
        out = _desc(room, _looker(hearing=0.0))
        self.assertNotIn("Sirens", out)
        self.assertIn("A neon-lit alley.", out)
        self.assertIn("Wet garbage.", out)
        self.assertIn("Cold mist clings.", out)


class BlindAndDeafTests(TestCase):
    def test_only_smell_and_touch_remain(self):
        room = _room(
            auditory="Sirens wail.", olfactory="Wet garbage.",
            tactile="Cold mist clings.",
        )
        out = _desc(room, _looker(sight=0.0, hearing=0.0))
        self.assertEqual(out, "Wet garbage. Cold mist clings.")


class LayerOrderTests(TestCase):
    def test_layers_render_in_canonical_order(self):
        room = _room(
            atmospheric="Dread hangs heavy.",
            auditory="Sirens wail.",
            tactile="Cold mist clings.",
            olfactory="Wet garbage.",
        )
        out = _desc(room, _looker())
        # visual, then auditory, olfactory, tactile, atmospheric.
        self.assertEqual(
            out,
            "A neon-lit alley. Sirens wail. Wet garbage. "
            "Cold mist clings. Dread hangs heavy.",
        )


class FailOpenTests(TestCase):
    def test_no_medical_model_perceives_everything(self):
        room = _room(auditory="Sirens wail.")
        out = _desc(room, _looker(medical=False))
        self.assertIn("A neon-lit alley.", out)
        self.assertIn("Sirens wail.", out)
