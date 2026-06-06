"""Unit tests for the at-decap head spawn (issue #343).

Previously the :class:`~typeclasses.items.SeveredHead` item only
materialised when the corpse was built at the *tail* of the death-
progression window (~90s after the killing blow), driven from
:meth:`~typeclasses.death_progression.DeathProgressionScript._create_corpse_from_character`.
Issue #343 shifts the spawn synchronously onto the cervical-spine-
destroyed *living* character so the head appears in the room at the
moment of the hit.

These tests exercise the three new pure / orchestrator helpers in
:mod:`typeclasses.items`:

* :func:`apply_severed_head_overlay_from_living` — copies identity /
  decay clock / trimmed head-container snapshot from a live character
  onto a head stub. Living counterpart to
  :func:`apply_severed_head_overlay`.
* :meth:`SeveredHead.configure_from_living_decap` — high-level
  configure: prose, key, condition, plus the overlay above and the
  head-cluster prose / wound overlay.
* :func:`spawn_severed_head_for_living` — orchestrator: spawns the
  head item, configures it from the living character, mutates the
  body (head-cluster longdesc + organ stages), and sets the
  ``head_severed_at_decap`` flag.

The orchestrator's ``create_object`` call is monkeypatched to a plain
stub so we don't need an Evennia DB. The pure overlay helper and the
configure method are exercised against plain-Python stubs directly.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

import typeclasses.items as items_module
from typeclasses.items import (
    apply_severed_head_overlay_from_living,
    spawn_severed_head_for_living,
)
from world.combat.constants import SEVERED_HEAD_LOCATIONS


class _DB:
    """Bare attribute container — matches Evennia ``obj.db`` surface."""

    def __init__(self):
        self.head_severed_at_decap = None


class _FakeHead:
    """SeveredHead-shaped stub for the pure overlay tests."""

    def __init__(self):
        self.db = _DB()


class _FakeOrgan:
    def __init__(self, name, container, *, current_hp=10, max_hp=10,
                 wound_stage=None, injury_type=None):
        self.name = name
        self.container = container
        self.current_hp = current_hp
        self.max_hp = max_hp
        self.wound_stage = wound_stage
        self.injury_type = injury_type

    def to_dict(self):
        return {
            "name": self.name,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "container": self.container,
            "wound_stage": self.wound_stage,
            "injury_type": self.injury_type,
            "conditions": [],
            "wound_timestamp": None,
        }


class _FakeMedicalState:
    def __init__(self, organs):
        self.organs = organs
        self.vital_signs_updated = False

    def update_vital_signs(self):
        self.vital_signs_updated = True

    def to_dict(self):
        return {
            "organs": {
                name: organ.to_dict() for name, organ in self.organs.items()
            },
            "conditions": [],
            "blood_level": 100,
            "pain_level": 0,
            "consciousness": 100,
        }


class _FakeCharacter:
    """Minimal living-character stub for the at-decap head spawn path."""

    def __init__(self, *, location=SimpleNamespace(key="alley"),
                 organs=None, longdesc=None, gender="male",
                 species="human", key="Anthony",
                 sleeve_uid="slv-anthony",
                 death_cause="decapitation"):
        self.location = location
        self.gender = gender
        self.key = key
        self.sleeve_uid = sleeve_uid
        self.longdesc = dict(longdesc or {})
        self.medical_state = _FakeMedicalState(organs or {})
        self._death_cause = death_cause
        self._saved = False
        self.db = _DB()
        self.db.species = species

    def get_death_cause(self):
        return self._death_cause

    def save_medical_state(self):
        self._saved = True


def _head_organs():
    return {
        "brain": _FakeOrgan("brain", "head", current_hp=0,
                            wound_stage="destroyed"),
        "left_eye": _FakeOrgan("left_eye", "head"),
        "right_eye": _FakeOrgan("right_eye", "head"),
    }


# ---------------------------------------------------------------------
# apply_severed_head_overlay_from_living
# ---------------------------------------------------------------------


class ApplyLivingOverlayTests(TestCase):
    """Pure copy of identity / decay / trimmed snapshot from the live body."""

    def test_sleeve_uid_copied_from_character(self):
        char = _FakeCharacter(sleeve_uid="slv-XYZ")
        head = _FakeHead()
        apply_severed_head_overlay_from_living(head, char)
        self.assertEqual(head.db.sleeve_uid, "slv-XYZ")

    def test_creation_and_death_time_now(self):
        import time
        char = _FakeCharacter()
        head = _FakeHead()
        before = time.time()
        apply_severed_head_overlay_from_living(head, char)
        after = time.time()
        self.assertGreaterEqual(head.db.creation_time, before)
        self.assertLessEqual(head.db.creation_time, after)
        # Head and death-time share the same now-anchor.
        self.assertEqual(head.db.creation_time, head.db.death_time)

    def test_death_cause_from_character(self):
        char = _FakeCharacter(death_cause="chainsaw to the neck")
        head = _FakeHead()
        apply_severed_head_overlay_from_living(head, char)
        self.assertEqual(head.db.death_cause, "chainsaw to the neck")

    def test_death_cause_defaults_to_decapitation(self):
        char = _FakeCharacter(death_cause=None)
        head = _FakeHead()
        apply_severed_head_overlay_from_living(head, char)
        self.assertEqual(head.db.death_cause, "decapitation")

    def test_medical_snapshot_only_head_container(self):
        organs = {
            "brain": _FakeOrgan("brain", "head", current_hp=0,
                                wound_stage="destroyed"),
            "heart": _FakeOrgan("heart", "chest", current_hp=10),
            "left_eye": _FakeOrgan("left_eye", "head"),
        }
        char = _FakeCharacter(organs=organs)
        head = _FakeHead()
        apply_severed_head_overlay_from_living(head, char)

        snap = head.db.medical_state_at_death
        organ_names = set(snap["organs"].keys())
        self.assertEqual(organ_names, {"brain", "left_eye"})
        # Body-wide fields are blanked — they describe the whole body
        # and would lie if reported off a disembodied head.
        self.assertEqual(snap["conditions"], [])
        self.assertIsNone(snap["blood_level"])
        self.assertIsNone(snap["pain_level"])
        self.assertIsNone(snap["consciousness"])

    def test_organ_dicts_deep_copied(self):
        # Mutating the head snapshot must not bleed back into the live
        # character's medical state.
        char = _FakeCharacter(organs=_head_organs())
        head = _FakeHead()
        apply_severed_head_overlay_from_living(head, char)
        head.db.medical_state_at_death["organs"]["brain"]["current_hp"] = 99
        self.assertEqual(
            char.medical_state.organs["brain"].current_hp, 0
        )

    def test_removed_organs_defaults_empty(self):
        char = _FakeCharacter()
        head = _FakeHead()
        apply_severed_head_overlay_from_living(head, char)
        self.assertEqual(head.db.removed_organs, [])


# ---------------------------------------------------------------------
# spawn_severed_head_for_living orchestrator
# ---------------------------------------------------------------------


class _SpawnedHeadStub:
    """Stand-in for the SeveredHead spawn target.

    We don't actually want to exercise the full
    :meth:`SeveredHead.configure_from_living_decap` over a typeclass
    instance here (its species / longdesc imports route through Evennia-
    aware modules); these tests stub configure_from_living_decap so we
    can isolate the orchestrator's responsibility: spawn + mutate body +
    flag.
    """

    def __init__(self, key, location):
        self.key = key
        self.location = location
        self.db = _DB()
        self.configure_calls = []

    def configure_from_living_decap(self, *, character, injury_type):
        self.configure_calls.append((character, injury_type))


class SpawnSeveredHeadForLivingTests(TestCase):
    def setUp(self):
        # Capture create_object so no DB call happens.
        self.spawned = []

        def _fake_create(typeclass, key, location):
            stub = _SpawnedHeadStub(key=key, location=location)
            self.spawned.append((typeclass, stub))
            return stub

        # spawn_severed_head_for_living does an inline
        # ``from evennia import create_object`` — monkeypatch via the
        # ``evennia`` module.
        import evennia
        self._orig_create = evennia.create_object
        evennia.create_object = _fake_create

    def tearDown(self):
        import evennia
        evennia.create_object = self._orig_create

    def test_no_location_no_spawn(self):
        char = _FakeCharacter(location=None)
        result = spawn_severed_head_for_living(char, injury_type="cut")
        self.assertIsNone(result)
        self.assertEqual(self.spawned, [])
        # The flag must NOT be set if the spawn aborted — otherwise
        # death progression would skip the corpse-side fallback.
        self.assertIsNone(char.db.head_severed_at_decap)

    def test_idempotent_when_already_severed(self):
        char = _FakeCharacter()
        char.db.head_severed_at_decap = True
        result = spawn_severed_head_for_living(char)
        self.assertIsNone(result)
        self.assertEqual(self.spawned, [])

    def test_spawns_into_room(self):
        room = SimpleNamespace(key="alley")
        char = _FakeCharacter(
            location=room,
            organs=_head_organs(),
            longdesc={
                "face": "{Their} face is angular.",
                "chest": "{Their} chest is broad.",
            },
        )
        result = spawn_severed_head_for_living(char, injury_type="cut")
        self.assertIsNotNone(result)
        self.assertEqual(len(self.spawned), 1)
        typeclass, head = self.spawned[0]
        self.assertEqual(typeclass, "typeclasses.items.SeveredHead")
        self.assertIs(head.location, room)
        # Orchestrator delegated identity / prose to configure_from_living_decap.
        self.assertEqual(head.configure_calls, [(char, "cut")])

    def test_body_stripped_after_spawn(self):
        char = _FakeCharacter(
            organs=_head_organs(),
            longdesc={
                "face": "{Their} face is angular.",
                "neck": "{Their} neck is corded.",
                "chest": "{Their} chest is broad.",
            },
        )
        spawn_severed_head_for_living(char)
        # Head-cluster longdesc gone, body locations preserved.
        self.assertNotIn("face", char.longdesc)
        self.assertNotIn("neck", char.longdesc)
        self.assertIn("chest", char.longdesc)
        # Head organs marked severed / hp=0; body organs untouched.
        for organ in char.medical_state.organs.values():
            if organ.container == "head":
                self.assertEqual(organ.wound_stage, "severed")
                self.assertEqual(organ.current_hp, 0)

    def test_at_decap_flag_set(self):
        char = _FakeCharacter(organs=_head_organs())
        spawn_severed_head_for_living(char)
        self.assertTrue(char.db.head_severed_at_decap)

    def test_decapitation_pending_flag_set(self):
        # The death-progression hook in
        # ``_create_corpse_from_character`` gates corpse-side cleanup
        # (head-cluster prose / wound stripping, synthesised neck
        # stump) on ``decapitation_pending``.  Combat sets this flag
        # before calling the spawn, but chart-driven amputation routes
        # straight through here — owning the flag inside the spawn
        # makes the cleanup fire for both pipelines.
        char = _FakeCharacter(organs=_head_organs())
        spawn_severed_head_for_living(char)
        self.assertTrue(char.db.decapitation_pending)

    def test_vital_signs_recomputed(self):
        char = _FakeCharacter(organs=_head_organs())
        spawn_severed_head_for_living(char)
        self.assertTrue(char.medical_state.vital_signs_updated)

    def test_medical_state_persisted(self):
        char = _FakeCharacter(organs=_head_organs())
        spawn_severed_head_for_living(char)
        self.assertTrue(char._saved)

    def test_clears_full_head_cluster_not_just_head_location(self):
        # Issue #343 contract: the WHOLE head-cluster
        # (face / neck / eyes / ears / hair) leaves with the head, not
        # just the bare "head" container.
        longdesc = {
            loc: f"{{Their}} {loc} prose" for loc in SEVERED_HEAD_LOCATIONS
        }
        longdesc["chest"] = "{Their} chest prose"
        char = _FakeCharacter(organs=_head_organs(), longdesc=longdesc)
        spawn_severed_head_for_living(char)
        for loc in SEVERED_HEAD_LOCATIONS:
            self.assertNotIn(loc, char.longdesc,
                             f"{loc} should have left with the head")
        self.assertIn("chest", char.longdesc)


# ---------------------------------------------------------------------
# Armor-mixin neck-hit integration
# ---------------------------------------------------------------------


class NeckHitDispatchTests(TestCase):
    """The combat severance trigger must call the at-decap spawn."""

    def setUp(self):
        from typeclasses.armor_mixin import ArmorMixin

        self.calls = []
        self._orig = items_module.spawn_severed_head_for_living

        def _spy(character, *, injury_type="cut"):
            self.calls.append((character, injury_type))
            # Mirror the live function's flag-set so tests can verify
            # the orchestrator was invoked AND the path completes.
            character.db.head_severed_at_decap = True

        items_module.spawn_severed_head_for_living = _spy

        class _NeckHit(ArmorMixin):
            def __init__(self, organs):
                self.db = SimpleNamespace(
                    decapitation_pending=None,
                    head_severed_at_decap=None,
                )
                self.medical_state = SimpleNamespace(organs=organs)

        self._NeckHit = _NeckHit

    def tearDown(self):
        items_module.spawn_severed_head_for_living = self._orig

    def _destroyed_neck(self):
        return self._NeckHit({
            "cervical_spine": _FakeOrgan(
                "cervical_spine", "neck", current_hp=0,
                wound_stage="destroyed",
            ),
        })

    def test_edged_neck_hit_spawns_head_at_decap(self):
        char = self._destroyed_neck()
        char._maybe_sever_from_damage("neck", "cut")
        self.assertEqual(self.calls, [(char, "cut")])
        # Decapitation flag still set — death progression reads it.
        self.assertTrue(char.db.decapitation_pending)
        # And the new flag — death progression reads this too.
        self.assertTrue(char.db.head_severed_at_decap)

    def test_blunt_neck_hit_does_not_spawn(self):
        char = self._destroyed_neck()
        char._maybe_sever_from_damage("neck", "blunt")
        self.assertEqual(self.calls, [])
        self.assertIsNone(char.db.head_severed_at_decap)

    def test_intact_neck_does_not_spawn(self):
        char = self._NeckHit({
            "cervical_spine": _FakeOrgan(
                "cervical_spine", "neck", current_hp=10,
            ),
        })
        char._maybe_sever_from_damage("neck", "cut")
        self.assertEqual(self.calls, [])
