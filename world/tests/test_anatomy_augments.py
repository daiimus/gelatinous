"""Phase 2 test contract for ANATOMY_AUGMENTS_SPEC (issue #511).

Pins the augment install pipeline and the per-character overlays:

* the ``install_augment`` resolver — creates the item's declared
  anatomy, surfaces the longdesc, consumes the item; failure seeds
  infection at the anchor and leaves the item; the anchor incision
  gate holds at resolution time;
* re-augmentation — installing over a severed stump replaces the
  remnants with fresh hardware;
* the severable overlay — augment organs declare their own
  severability (``MedicalState.location_severable_by_organ`` and
  the operate-menu listing);
* severed-part prose — a human tail Appendage has a default desc.

The prehensile ``hands`` overlay is pinned in
``test_dynamic_hands.HandsViewAgainstAnatomy``; the resolution
substrate (organ round-trip, body-driven targeting) in
``test_anatomy_substrate``.

Run via::

    evennia test --settings settings.py world.tests.test_anatomy_augments
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.medical.core import MedicalState, Organ
from world.medical.procedures import (
    _resolve_install_augment,
    open_incision,
)


TAIL_ORGAN_SPEC = {
    "container": "tail", "max_hp": 25, "hit_weight": "common",
    "can_be_destroyed": True,
    "fracture_vulnerable": True, "bone_type": "actuator_column",
    "severable_container": True,
    "grasping": True,
}


def _patient(species="human"):
    """Stub character with the surfaces the resolver touches —
    mirrors the ``test_surgical_procedures`` fixture pattern."""
    char = SimpleNamespace()
    char.intellect = 3
    char.motorics = 3
    char.is_unconscious = lambda: False
    char.db = SimpleNamespace(
        species=species, archived=False, surgical_state=None,
        medical_chart=None,
    )
    char.key = "Patient"
    char.get_display_name = lambda looker=None: "Patient"
    char.msg = lambda *a, **kw: None
    char.longdesc = {"head": None, "back": None, "groin": None}
    char.medical_state = MedicalState(char)
    char.save_medical_state = lambda: None
    return char


def _surgeon():
    actor = SimpleNamespace()
    actor.intellect = 4
    actor.motorics = 4
    actor.key = "Surgeon"
    actor.location = None  # skips the room broadcast
    actor.messages = []
    actor.msg = actor.messages.append
    return actor


def _tail_item(**db_overrides):
    item = SimpleNamespace()
    item.key = "cybernetic tail"
    item.deleted = False

    def _delete():
        item.deleted = True
    item.delete = _delete
    db_attrs = dict(
        augment_organs={"cybernetic_tailbone": dict(TAIL_ORGAN_SPEC)},
        augment_container="tail",
        augment_anchor="back",
        augment_longdesc={
            "key": "tail",
            "default_desc": "A cybernetic tail.",
            "display_after": "back",
        },
        compatible_species=["human"],
    )
    db_attrs.update(db_overrides)
    item.db = SimpleNamespace(**db_attrs)
    return item


class TestInstallAugmentResolver(TestCase):
    def _install(self, target, outcome="success", item=None):
        actor = _surgeon()
        item = item if item is not None else _tail_item()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": outcome},
        ):
            _resolve_install_augment(
                actor, target, organ_item=item, location="back",
            )
        return actor, item

    def test_success_creates_the_anatomy(self):
        target = _patient()
        open_incision(target, "back")
        actor, item = self._install(target)

        organ = target.medical_state.organs.get("cybernetic_tailbone")
        self.assertIsNotNone(organ)
        self.assertEqual(organ.container, "tail")
        self.assertEqual(organ.current_hp, 25)
        self.assertIs(organ.medical_state, target.medical_state)
        self.assertTrue(item.deleted)

    def test_success_surfaces_the_longdesc_after_anchor(self):
        target = _patient()
        open_incision(target, "back")
        self._install(target)
        keys = list(target.longdesc.keys())
        self.assertIn("tail", keys)
        self.assertEqual(keys.index("tail"), keys.index("back") + 1)

    def test_failure_leaves_item_and_seeds_infection(self):
        target = _patient()
        open_incision(target, "back")
        actor, item = self._install(target, outcome="failure")

        self.assertNotIn("cybernetic_tailbone", target.medical_state.organs)
        self.assertNotIn("tail", target.longdesc)
        self.assertFalse(item.deleted)
        infections = [
            c for c in target.medical_state.conditions
            if getattr(c, "condition_type", "") == "infection"
            and c.location == "back"
        ]
        self.assertTrue(infections)

    def test_missing_anchor_incision_blocks(self):
        target = _patient()  # no incision opened
        actor, item = self._install(target)
        self.assertNotIn("cybernetic_tailbone", target.medical_state.organs)
        self.assertFalse(item.deleted)
        self.assertTrue(any("isn't open" in m for m in actor.messages))

    def test_reaugment_replaces_severed_stump(self):
        """Install over a severed tail: the remnants are replaced
        wholesale by fresh hardware."""
        target = _patient()
        stump = Organ("cybernetic_tailbone", organ_data=dict(TAIL_ORGAN_SPEC))
        stump.current_hp = 0
        stump.wound_stage = "severed"
        stump.medical_state = target.medical_state
        target.medical_state.organs["cybernetic_tailbone"] = stump

        open_incision(target, "back")
        self._install(target)
        organ = target.medical_state.organs["cybernetic_tailbone"]
        self.assertEqual(organ.current_hp, 25)
        self.assertIsNone(organ.wound_stage)

    def test_partial_installs_but_seeds_infection(self):
        target = _patient()
        open_incision(target, "back")
        self._install(target, outcome="partial")
        self.assertIn("cybernetic_tailbone", target.medical_state.organs)
        infections = [
            c for c in target.medical_state.conditions
            if getattr(c, "condition_type", "") == "infection"
        ]
        self.assertTrue(infections)

    def test_species_gate_blocks_in_resolver(self):
        """Chart-commenced installs bypass CmdInstall's gates — the
        resolver re-checks species itself."""
        target = _patient(species="rat")
        open_incision(target, "back")
        actor, item = self._install(target)
        self.assertNotIn("cybernetic_tailbone", target.medical_state.organs)
        self.assertFalse(item.deleted)
        self.assertTrue(any("isn't rated" in m for m in actor.messages))

    def test_legacy_species_compat_field_accepted(self):
        """Items spawned before the compatible_species unification
        carry species_compat — still honored."""
        target = _patient()
        open_incision(target, "back")
        item = _tail_item(compatible_species=None, species_compat=["human"])
        self._install(target, item=item)
        self.assertIn("cybernetic_tailbone", target.medical_state.organs)


class TestOperateMenuDonorListing(TestCase):
    def test_augment_items_list_as_donors(self):
        """The operate install picker shows augment items alongside
        harvested organs — the bug where the tail never appeared."""
        from commands.CmdOperate import _list_donor_organs

        heart = SimpleNamespace(
            key="donor heart", db=SimpleNamespace(organ_name="heart"),
        )
        tail = _tail_item()
        plain = SimpleNamespace(key="brick", db=SimpleNamespace())
        caller = SimpleNamespace(contents=[heart, tail, plain])
        donors = _list_donor_organs(caller)
        items = [item for item, _label in donors]
        self.assertIn(heart, items)
        self.assertIn(tail, items)
        self.assertNotIn(plain, items)


class TestSeverableOverlay(TestCase):
    def test_organ_flag_makes_location_severable(self):
        state = MedicalState(character=None)
        organ = Organ("cybernetic_tailbone", organ_data=dict(TAIL_ORGAN_SPEC))
        organ.medical_state = state
        state.organs["cybernetic_tailbone"] = organ
        self.assertTrue(state.location_severable_by_organ("tail"))

    def test_unflagged_locations_are_not(self):
        state = MedicalState(character=None)
        self.assertFalse(state.location_severable_by_organ("chest"))
        self.assertFalse(state.location_severable_by_organ("tail"))

    def test_operate_listing_includes_augment_location(self):
        from commands.CmdOperate import _list_severable_containers

        target = _patient()
        organ = Organ("cybernetic_tailbone", organ_data=dict(TAIL_ORGAN_SPEC))
        organ.medical_state = target.medical_state
        target.medical_state.organs["cybernetic_tailbone"] = organ
        locations = _list_severable_containers(target)
        self.assertIn("tail", locations)
        self.assertIn("left_arm", locations)


class TestSeveredTailProse(TestCase):
    def test_human_tail_has_descriptions(self):
        from world.anatomy.severed_parts import get_severed_part_description

        for condition in ("pristine", "damaged", "putrid"):
            prose = get_severed_part_description("human", "tail", condition)
            self.assertTrue(prose, f"missing {condition} tail prose")
