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


# ---------------------------------------------------------------------
# Replacement augments — multi-container (#516 Phase 2)
# ---------------------------------------------------------------------


def _arm_item():
    """Stub mirroring the SHOTGUN_ARM prototype's augment attrs."""
    item = SimpleNamespace()
    item.key = "shotgun arm"
    item.deleted = False

    def _delete():
        item.deleted = True
    item.delete = _delete
    item.db = SimpleNamespace(
        augment_organs={
            "cybernetic_humerus": {
                "container": "right_arm", "max_hp": 30,
                "hit_weight": "common", "bone_type": "actuator_column",
                "abilities": {
                    "shotgun": {
                        "type": "integrated_weapon",
                        "slot": "right_hand",
                        "weapon_prototype": "SHOTGUN_ARM_GUN",
                    },
                },
            },
            "cybernetic_metacarpals": {
                "container": "right_hand", "max_hp": 18,
                "hit_weight": "uncommon", "grasping": True,
            },
        },
        augment_container="right_arm",
        augment_anchor="right_arm",
        augment_longdesc=[
            {"key": "right_arm", "default_desc": "A cyber arm."},
            {"key": "right_hand", "default_desc": "A cyber hand.",
             "display_after": "right_arm"},
        ],
        compatible_species=["human"],
    )
    return item


def _sever_right_arm(target):
    """Put the patient in the amputee state the arm mounts over."""
    for organ in target.medical_state.organs.values():
        if organ.container in ("right_arm", "right_hand"):
            organ.current_hp = 0
            organ.wound_stage = "severed"
    target.longdesc = {
        k: v for k, v in target.longdesc.items()
        if k not in ("right_arm", "right_hand")
    }


class TestReplacementAugmentInstall(TestCase):
    def _install(self, target, item, outcome="success"):
        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": outcome},
        ):
            _resolve_install_augment(
                actor, target, organ_item=item, location="right_arm",
            )
        return actor, item

    def _amputee(self):
        target = _patient()
        target.longdesc = {
            "head": None, "back": None,
            "right_arm": None, "right_hand": None,
        }
        _sever_right_arm(target)
        return target

    def test_mounts_over_the_stump(self):
        target = self._amputee()
        open_incision(target, "right_arm")
        self._install(target, _arm_item())

        organs = target.medical_state.organs
        self.assertIn("cybernetic_humerus", organs)
        self.assertIn("cybernetic_metacarpals", organs)
        # The severed flesh remnants are replaced wholesale.
        self.assertNotIn("right_humerus", organs)
        self.assertNotIn("right_metacarpals", organs)
        self.assertEqual(organs["cybernetic_humerus"].container, "right_arm")
        self.assertEqual(organs["cybernetic_metacarpals"].container, "right_hand")

    def test_longdesc_list_restores_both_keys_in_order(self):
        target = self._amputee()
        open_incision(target, "right_arm")
        self._install(target, _arm_item())
        keys = list(target.longdesc.keys())
        self.assertIn("right_arm", keys)
        self.assertIn("right_hand", keys)
        self.assertEqual(
            keys.index("right_hand"), keys.index("right_arm") + 1,
        )

    def test_ability_rideses_the_installed_organ(self):
        from world.medical.augments import find_ability

        target = self._amputee()
        open_incision(target, "right_arm")
        self._install(target, _arm_item())
        organ, spec = find_ability(target, "shotgun")
        self.assertIsNotNone(organ)
        self.assertEqual(spec["slot"], "right_hand")


class TestReplacementAugmentGate(TestCase):
    """Living anatomy blocks; stumps AND wreckage admit (user
    decision 2026-06-13: sever and amputate are one path, and the
    install surgery clears mangled remains the same way).  The gate
    is HP-based — tested at the helper level the command branch and
    resolver both use."""

    def _blocking(self, target, item):
        declared = {
            spec["container"]
            for spec in item.db.augment_organs.values()
        }
        return [
            organ for organ in target.medical_state.organs.values()
            if organ.container in declared and organ.current_hp > 0
        ]

    def test_living_anatomy_blocks_install(self):
        target = _patient()
        self.assertTrue(self._blocking(target, _arm_item()))

    def test_severed_stump_admits(self):
        target = _patient()
        _sever_right_arm(target)
        self.assertFalse(self._blocking(target, _arm_item()))

    def test_destroyed_wreckage_admits(self):
        """Pulped-in-place (blunt/bullet — destroyed, not severed)
        is anatomy to clear, not anatomy that blocks."""
        target = _patient()
        for organ in target.medical_state.organs.values():
            if organ.container in ("right_arm", "right_hand"):
                organ.current_hp = 0
                organ.wound_stage = "destroyed"
        self.assertFalse(self._blocking(target, _arm_item()))

    def test_resolver_recheck_blocks_living_anatomy(self):
        """Chart-commenced installs bypass the command gate — the
        resolver re-checks and marks the step failed."""
        target = _patient()
        target.longdesc = {"head": None, "right_arm": None}
        open_incision(target, "right_arm")
        actor = _surgeon()
        item = _arm_item()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": "success"},
        ):
            _resolve_install_augment(
                actor, target, organ_item=item, location="right_arm",
            )
        self.assertNotIn("cybernetic_humerus", target.medical_state.organs)
        self.assertFalse(item.deleted)
        self.assertTrue(any("living" in m for m in actor.messages))

    def test_install_over_wreckage_replaces_longdesc(self):
        """Destroyed-in-place limbs keep their longdesc key (only
        severance removes it) — the mount overwrites the dead flesh
        prose with the augment's."""
        target = _patient()
        target.longdesc = {
            "head": None, "right_arm": "A scarred but mighty arm.",
            "right_hand": None,
        }
        for organ in target.medical_state.organs.values():
            if organ.container in ("right_arm", "right_hand"):
                organ.current_hp = 0
                organ.wound_stage = "destroyed"
        open_incision(target, "right_arm")
        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": "success"},
        ):
            _resolve_install_augment(
                actor, target, organ_item=_arm_item(), location="right_arm",
            )
        self.assertIn("cybernetic_humerus", target.medical_state.organs)
        self.assertEqual(target.longdesc["right_arm"], "A cyber arm.")
        self.assertEqual(target.longdesc["right_hand"], "A cyber hand.")


class TestInorganicConditions(TestCase):
    """Chrome doesn't bleed and doesn't go septic; pain stays as
    neural feedback (user decision 2026-06-13)."""

    def _damaged(self, inorganic):
        from world.medical.conditions import MedicalCondition

        target = _patient()
        spec = dict(TAIL_ORGAN_SPEC)
        spec["inorganic"] = inorganic
        organ = Organ("cybernetic_tailbone", organ_data=spec)
        organ.medical_state = target.medical_state
        target.medical_state.organs["cybernetic_tailbone"] = organ
        # Script lifecycle isn't under test — the stub has no
        # Evennia scripts handler.
        with patch.object(
            MedicalCondition, "start_condition", lambda self, ch: None,
        ):
            target.medical_state.take_organ_damage(
                "cybernetic_tailbone", 12, "bullet",
            )
        return [
            getattr(c, "condition_type", "")
            for c in target.medical_state.conditions
        ]

    def test_inorganic_organ_damage_yields_pain_only(self):
        types = self._damaged(inorganic=True)
        self.assertNotIn("bleeding", types)
        self.assertNotIn("infection", types)
        self.assertIn("pain", types)

    def test_organic_organ_damage_still_bleeds(self):
        types = self._damaged(inorganic=False)
        self.assertIn("bleeding", types)


class TestAnatomyIsTheTruth(TestCase):
    """The #516-review standard: the organs dict is the single truth
    of present anatomy — nothing auto-creates.  The old get_organ
    auto-create was a zombie-organ factory: capacity math iterating
    species tables by name resurrected install-deleted flesh organs
    at full HP."""

    def test_get_organ_never_creates(self):
        state = _patient().medical_state
        del state.organs["right_humerus"]
        self.assertIsNone(state.get_organ("right_humerus"))
        self.assertNotIn("right_humerus", state.organs)

    def test_capacity_math_does_not_resurrect(self):
        """The exact bug: medinfo capacities after a gun-arm install
        re-created the deleted flesh arm."""
        state = _patient().medical_state
        del state.organs["right_humerus"]
        state._cache_dirty = True
        state.calculate_body_capacity("manipulation")
        self.assertNotIn("right_humerus", state.organs)

    def test_damage_to_absent_organ_is_a_noop(self):
        state = _patient().medical_state
        del state.organs["right_humerus"]
        result = state.take_organ_damage("right_humerus", 10, "cut")
        self.assertFalse(result)
        self.assertNotIn("right_humerus", state.organs)

    def test_severed_tombstones_still_reduce_capacity(self):
        """Tombstones are load-bearing: a severed (not replaced) arm
        keeps dragging manipulation down via its 0-HP record."""
        target = _patient()
        state = target.medical_state
        state._cache_dirty = True
        healthy = state.calculate_body_capacity("manipulation")
        _sever_right_arm(target)
        state._cache_dirty = True
        severed = state.calculate_body_capacity("manipulation")
        self.assertLess(severed, healthy)


SIDED_ARM_ORGANS = {
    "{side}_humerus": {
        "container": "{side}_arm", "max_hp": 30, "hit_weight": "common",
        "capacity": "manipulation", "contribution": "major",
        "bone_type": "actuator_column", "inorganic": True,
    },
    "{side}_forearm_hardpoint": {
        "container": "{side}_arm", "max_hp": 10, "hit_weight": "rare",
        "inorganic": True, "hardpoint": "forearm",
    },
}

SHOTGUN_MODULE_SPEC = {
    "container": "{side}_arm", "max_hp": 12, "hit_weight": "rare",
    "inorganic": True, "hardpoint": "forearm", "module_type": "forearm",
    "abilities": {
        "shotgun": {
            "type": "integrated_weapon",
            "slot": "{side}_hand",
            "weapon_prototype": "SHOTGUN_ARM_GUN",
        },
    },
}


def _sided_arm_item():
    """Stub mirroring the CYBER_ARM prototype's side-agnostic shape."""
    item = SimpleNamespace()
    item.key = "cybernetic arm"
    item.deleted = False

    def _delete():
        item.deleted = True
    item.delete = _delete
    item.db = SimpleNamespace(
        augment_organs={k: dict(v) for k, v in SIDED_ARM_ORGANS.items()},
        augment_container="{side}_arm",
        augment_anchor="{side}_arm",
        augment_longdesc=[
            {"key": "{side}_arm", "default_desc": "A cyber arm."},
        ],
        compatible_species=["human"],
    )
    return item


def _module_item():
    item = SimpleNamespace()
    item.key = "shotgun module"
    item.deleted = False

    def _delete():
        item.deleted = True
    item.delete = _delete
    item.db = SimpleNamespace(
        module_type="forearm",
        condition="pristine",
        organ_conditions=[],
        organ_spec=dict(SHOTGUN_MODULE_SPEC),
        compatible_species=["human"],
    )
    item.get_display_name = lambda looker=None: item.key
    return item


class TestSideAgnosticChassis(TestCase):
    """#526 M2: one CYBER_ARM mounts left or right — the surgeon
    names the side and the {side} templates resolve from it."""

    def test_declaration_resolves_side(self):
        from world.medical.procedures import resolve_augment_declaration

        declaration = resolve_augment_declaration(
            _sided_arm_item().db, side="left",
        )
        self.assertTrue(declaration["side_agnostic"])
        self.assertEqual(declaration["container"], "left_arm")
        self.assertEqual(declaration["anchor"], "left_arm")
        self.assertIn("left_humerus", declaration["organs"])
        self.assertEqual(
            declaration["organs"]["left_humerus"]["container"], "left_arm",
        )
        self.assertEqual(declaration["longdesc"][0]["key"], "left_arm")

    def test_declaration_without_side_keeps_templates(self):
        from world.medical.procedures import resolve_augment_declaration

        declaration = resolve_augment_declaration(_sided_arm_item().db)
        self.assertTrue(declaration["side_agnostic"])
        self.assertIn("{side}_humerus", declaration["organs"])

    def test_install_resolves_left(self):
        target = _patient()
        target.longdesc = {"head": None, "back": None}
        for organ in target.medical_state.organs.values():
            if organ.container in ("left_arm", "left_hand"):
                organ.current_hp = 0
                organ.wound_stage = "severed"
        open_incision(target, "left_arm")
        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": "success"},
        ):
            _resolve_install_augment(
                actor, target, organ_item=_sided_arm_item(),
                location="left_arm", side="left",
            )
        organs = target.medical_state.organs
        self.assertIn("left_humerus", organs)
        self.assertTrue(organs["left_humerus"].data.get("inorganic"))
        self.assertIn("left_forearm_hardpoint", organs)
        self.assertIn("left_arm", target.longdesc)
        # The RIGHT side is untouched flesh.
        self.assertFalse(organs["right_humerus"].data.get("inorganic"))

    def test_install_without_side_blocks(self):
        target = _patient()
        open_incision(target, "left_arm")
        actor = _surgeon()
        item = _sided_arm_item()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": "success"},
        ):
            _resolve_install_augment(
                actor, target, organ_item=item, location="left_arm",
            )
        self.assertFalse(item.deleted)
        self.assertTrue(any("either side" in m for m in actor.messages))


class TestModuleInstall(TestCase):
    """#526 M3: modules seat into chassis hardpoints and inherit
    their side from the slot."""

    def _chassis_patient(self, side="left"):
        target = _patient()
        spec = {
            "container": f"{side}_arm", "max_hp": 10, "hit_weight": "rare",
            "inorganic": True, "hardpoint": "forearm",
        }
        organ = Organ(f"{side}_forearm_hardpoint", organ_data=spec)
        organ.medical_state = target.medical_state
        target.medical_state.organs[f"{side}_forearm_hardpoint"] = organ
        return target

    def _install(self, target, item, location="left_arm", outcome="success"):
        from world.medical.procedures import _resolve_install_module

        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": outcome},
        ):
            _resolve_install_module(
                actor, target, organ_item=item, location=location,
            )
        return actor

    def test_module_seats_and_inherits_side(self):
        from world.medical.augments import find_ability

        target = self._chassis_patient("left")
        open_incision(target, "left_arm")
        item = _module_item()
        self._install(target, item)

        organ = target.medical_state.organs["left_forearm_hardpoint"]
        self.assertIn("shotgun", organ.data.get("abilities", {}))
        # Side inherited from the slot: the ability deploys into the
        # LEFT hand.
        found, spec = find_ability(target, "shotgun")
        self.assertIs(found, organ)
        self.assertEqual(spec["slot"], "left_hand")
        self.assertTrue(item.deleted)

    def test_occupied_hardpoint_rejects(self):
        target = self._chassis_patient("left")
        # Occupy it with a live module.
        occupied_spec = dict(SHOTGUN_MODULE_SPEC)
        occupied_spec["container"] = "left_arm"
        organ = Organ("left_forearm_hardpoint", organ_data=occupied_spec)
        organ.medical_state = target.medical_state
        target.medical_state.organs["left_forearm_hardpoint"] = organ
        open_incision(target, "left_arm")
        item = _module_item()
        actor = self._install(target, item)
        self.assertFalse(item.deleted)
        self.assertTrue(any("hardpoint" in m for m in actor.messages))

    def test_harvested_out_hardpoint_accepts_again(self):
        """Module harvest tombstones the slot (hp 0 severed) — a new
        module rebuilds over it."""
        target = self._chassis_patient("left")
        occupied_spec = dict(SHOTGUN_MODULE_SPEC)
        occupied_spec["container"] = "left_arm"
        organ = Organ("left_forearm_hardpoint", organ_data=occupied_spec)
        organ.current_hp = 0
        organ.wound_stage = "severed"
        organ.medical_state = target.medical_state
        target.medical_state.organs["left_forearm_hardpoint"] = organ
        open_incision(target, "left_arm")
        item = _module_item()
        self._install(target, item)
        rebuilt = target.medical_state.organs["left_forearm_hardpoint"]
        self.assertEqual(rebuilt.current_hp, rebuilt.max_hp)
        self.assertIn("shotgun", rebuilt.data.get("abilities", {}))

    def test_harvest_carries_module_provenance(self):
        from world.medical.procedures import _configure_harvested_item

        target = self._chassis_patient("left")
        occupied_spec = dict(SHOTGUN_MODULE_SPEC)
        occupied_spec = {
            k: (v.replace("{side}", "left") if isinstance(v, str) else v)
            for k, v in occupied_spec.items()
        }
        organ = Organ("left_forearm_hardpoint", organ_data=occupied_spec)
        item = SimpleNamespace(db=SimpleNamespace())
        _configure_harvested_item(
            item, organ_name="left_forearm_hardpoint",
            condition="pristine", source=target,
            organ_data=organ.to_dict(),
        )
        self.assertEqual(item.db.module_type, "forearm")
        self.assertIn("abilities", item.db.organ_spec)


CYBER_JAW_SPEC = {
    "container": "head", "display_location": "face",
    "max_hp": 14, "hit_weight": "rare",
    "capacities": ["talking", "eating"],
    "talking_contribution": "major",
    "eating_contribution": "moderate",
    "can_be_harvested": True, "can_be_replaced": True,
    "inorganic": True, "prosthetic_frame": True,
    "hardpoint": "jaw",
}

JAWZ_MODULE_SPEC = dict(
    CYBER_JAW_SPEC,
    module_type="jaw",
    abilities={
        "jawz": {
            "type": "natural_weapon",
            "weapon_prototype": "JAWZ_FANGS",
        },
    },
)


def _jawz_item():
    item = SimpleNamespace()
    item.key = "Jawz"
    item.deleted = False

    def _delete():
        item.deleted = True
    item.delete = _delete
    item.db = SimpleNamespace(
        module_type="jaw",
        condition="pristine",
        organ_conditions=[],
        organ_spec={k: (dict(v) if isinstance(v, dict) else v)
                    for k, v in JAWZ_MODULE_SPEC.items()},
        compatible_species=["human"],
    )
    item.get_display_name = lambda looker=None: item.key
    return item


class TestCyberJawHardpoint(TestCase):
    """#525 review: Jawz is a hardpoint module, not a flesh implant.
    The line is drawn — a MODULE needs a chassis hardpoint, so a
    cybernetic jaw (CYBER_JAW) is the prerequisite.  The cyber jaw
    replaces the flesh jaw via the spec-carrying organ path and
    carries a ``jaw`` hardpoint; Jawz seats into it."""

    def _install_jaw(self, target, item, location="head", outcome="success"):
        from world.medical.procedures import _resolve_install

        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": outcome},
        ):
            _resolve_install(
                actor, target, organ_item=item, location=location,
            )
        return actor

    def _install_module(self, target, item, location="head",
                        outcome="success"):
        from world.medical.procedures import _resolve_install_module

        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": outcome},
        ):
            _resolve_install_module(
                actor, target, organ_item=item, location=location,
            )
        return actor

    def _cyber_jaw_item(self):
        return _organ_item(
            organ_name="jaw", organ_spec=dict(CYBER_JAW_SPEC),
        )

    def test_cyber_jaw_replaces_flesh_jaw(self):
        """The chassis: a cyber jaw rebuilds the jaw slot as chrome,
        keeps talking/eating, and exposes a jaw hardpoint.  The jaw
        is surface-accessible (its display_location is its own face),
        so no cavity incision is required."""
        target = _patient()
        self._install_jaw(target, self._cyber_jaw_item())

        jaw = target.medical_state.organs["jaw"]
        self.assertTrue(jaw.data.get("inorganic"))
        self.assertTrue(jaw.data.get("prosthetic_frame"))
        self.assertEqual(jaw.data.get("hardpoint"), "jaw")
        self.assertEqual(jaw.max_hp, 14)
        self.assertIn("talking", jaw.data.get("capacities", []))
        self.assertIn("eating", jaw.data.get("capacities", []))
        # No ability yet — the hardpoint is empty.
        self.assertFalse(jaw.data.get("abilities"))

    def test_cyber_jaw_installs_at_face_display_location(self):
        """Regression (operate-menu bug): the install picker passes the
        jaw's *display_location* ("face"), not its container ("head"),
        as the procedure location.  Surface-accessibility must be judged
        from the organ itself, so installing at "face" needs NO incision
        — the old gate wrongly demanded a face incision the menu can't
        open, dead-ending the install."""
        target = _patient()
        self._install_jaw(target, self._cyber_jaw_item(), location="face")

        jaw = target.medical_state.organs["jaw"]
        self.assertTrue(jaw.data.get("inorganic"))
        self.assertTrue(jaw.data.get("prosthetic_frame"))
        self.assertEqual(jaw.data.get("hardpoint"), "jaw")

    def test_jawz_seats_into_cyber_jaw_hardpoint(self):
        """The module: with a cyber jaw in place, Jawz seats into the
        jaw hardpoint, adding the bite while keeping talk/eat."""
        from world.medical.augments import find_ability

        target = _patient()
        self._install_jaw(target, self._cyber_jaw_item())
        open_incision(target, "head")
        item = _jawz_item()
        self._install_module(target, item)

        jaw = target.medical_state.organs["jaw"]
        self.assertIn("jawz", jaw.data.get("abilities", {}))
        # Chassis function preserved.
        self.assertTrue(jaw.data.get("inorganic"))
        self.assertIn("talking", jaw.data.get("capacities", []))
        self.assertIn("eating", jaw.data.get("capacities", []))
        found, spec = find_ability(target, "jawz")
        self.assertIs(found, jaw)
        self.assertEqual(spec["type"], "natural_weapon")
        self.assertEqual(spec["weapon_prototype"], "JAWZ_FANGS")
        self.assertTrue(item.deleted)

    def test_jawz_without_cyber_jaw_rejects(self):
        """The gate: a flesh jaw has no hardpoint — Jawz can't seat,
        and the message names the missing hardpoint."""
        target = _patient()
        open_incision(target, "head")
        item = _jawz_item()
        actor = self._install_module(target, item)
        self.assertFalse(item.deleted)
        self.assertTrue(any("hardpoint" in m for m in actor.messages))
        # Flesh jaw untouched — no bite grafted onto living anatomy.
        jaw = target.medical_state.organs["jaw"]
        self.assertNotIn("jawz", jaw.data.get("abilities", {}) or {})


def _nailz_item():
    item = SimpleNamespace()
    item.key = "Nailz"
    item.deleted = False

    def _delete():
        item.deleted = True
    item.delete = _delete
    item.db = SimpleNamespace(
        module_type="nailz",
        module_mount="flesh",
        flesh_containers=["{side}_hand"],
        condition="pristine",
        organ_conditions=[],
        organ_spec={
            "module_type": "nailz",
            "abilities": {
                "nailz": {
                    "type": "natural_weapon",
                    "weapon_prototype": "NAILZ_CLAWS",
                },
            },
        },
        compatible_species=["human"],
    )
    item.get_display_name = lambda looker=None: item.key
    return item


class TestFleshMountModules(TestCase):
    """#526 M4: the Nailz/Jawz class — abilities implant into LIVING
    anatomy; the host stays what it is (flesh still bleeds)."""

    def _install(self, target, item, location="left_hand", outcome="success"):
        from world.medical.procedures import _resolve_install_module

        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": outcome},
        ):
            _resolve_install_module(
                actor, target, organ_item=item, location=location,
            )
        return actor

    def test_flesh_organ_targets_named_host_not_first(self):
        """flesh_organ targeting: a multi-organ container (head)
        requires naming the specific host, or the implant would land
        in whatever organ comes first (the brain)."""
        from world.medical.augments import find_ability

        target = _patient()
        open_incision(target, "head")
        implant = SimpleNamespace()
        implant.key = "test implant"
        implant.deleted = False
        implant.delete = lambda: setattr(implant, "deleted", True)
        implant.get_display_name = lambda looker=None: "test implant"
        implant.db = SimpleNamespace(
            module_type="testmod", module_mount="flesh",
            flesh_containers=["head"], flesh_organ="jaw",
            condition="pristine", organ_conditions=[],
            organ_spec={"module_type": "testmod", "abilities": {
                "testmod": {"type": "natural_weapon",
                            "weapon_prototype": "JAWZ_FANGS"}}},
            compatible_species=["human"],
        )
        self._install(target, implant, location="head")

        organs = target.medical_state.organs
        self.assertIn("testmod", organs["jaw"].data.get("abilities", {}))
        self.assertNotIn("testmod", organs["brain"].data.get("abilities", {}))
        self.assertTrue(implant.deleted)
        found, _spec = find_ability(target, "testmod")
        self.assertIs(found, organs["jaw"])

    def test_implants_into_living_flesh(self):
        from world.medical.augments import find_ability

        target = _patient()
        open_incision(target, "left_hand")
        item = _nailz_item()
        self._install(target, item)

        host = target.medical_state.organs["left_metacarpals"]
        self.assertIn("nailz", host.data.get("abilities", {}))
        # The host stays flesh — it still bleeds.
        self.assertFalse(host.data.get("inorganic"))
        organ, spec = find_ability(target, "nailz")
        self.assertIs(organ, host)
        self.assertEqual(spec["type"], "natural_weapon")
        self.assertTrue(item.deleted)
        # The species table was never mutated: a second character's
        # metacarpals carry no claws.
        other = _patient()
        self.assertNotIn(
            "nailz",
            other.medical_state.organs["left_metacarpals"].data.get(
                "abilities", {},
            ),
        )

    def test_duplicate_implant_rejects(self):
        target = _patient()
        open_incision(target, "left_hand")
        self._install(target, _nailz_item())
        second = _nailz_item()
        actor = self._install(target, second)
        self.assertFalse(second.deleted)
        self.assertTrue(any("already carries" in m for m in actor.messages))

    def test_dead_anatomy_rejects(self):
        target = _patient()
        for organ in target.medical_state.organs.values():
            if organ.container == "left_hand":
                organ.current_hp = 0
                organ.wound_stage = "destroyed"
        open_incision(target, "left_hand")
        item = _nailz_item()
        actor = self._install(target, item)
        self.assertFalse(item.deleted)
        self.assertTrue(any("Nothing living" in m for m in actor.messages))

    def test_undeclared_container_rejects(self):
        target = _patient()
        open_incision(target, "chest")
        item = _nailz_item()
        actor = self._install(target, item, location="chest")
        self.assertFalse(item.deleted)
        self.assertTrue(any("doesn't mount" in m for m in actor.messages))


class TestNailzMaterial(TestCase):
    """#525 review: claws are carbide with a monofilament EDGE — a
    monofilament whip/wire isn't a claw body.  Pins the material so
    the prose doesn't drift back to 'monofilament claws'."""

    def test_nailz_prototypes_are_carbide(self):
        from world import prototypes

        for proto in (prototypes.NAILZ, prototypes.NAILZ_CLAWS):
            desc = proto["desc"].lower()
            self.assertIn("carbide", desc)
            self.assertNotIn("monofilament claw", desc)
        # The edge — not the body — is the monofilament part.
        self.assertIn("monofilament edge", prototypes.NAILZ["desc"].lower())


CYBER_HEART_SPEC = {
    "container": "chest", "max_hp": 20, "hit_weight": "uncommon",
    "vital": True, "capacity": "blood_pumping", "contribution": "total",
    "inorganic": True,
}


def _organ_item(organ_name="heart", organ_spec=None, condition="pristine"):
    """Stub mirroring a harvested/cyber organ item (#526 M1)."""
    item = SimpleNamespace()
    item.key = f"cybernetic {organ_name}"
    item.deleted = False

    def _delete():
        item.deleted = True
    item.delete = _delete
    item.db = SimpleNamespace(
        organ_name=organ_name,
        condition=condition,
        organ_conditions=[],
        organ_spec=organ_spec,
        compatible_species=["human"],
    )
    item.get_display_name = lambda looker=None: item.key
    return item


class TestSpecCarryingOrgans(TestCase):
    """#526 M1: the item IS the organ — specs travel with harvested
    items and rebuild the slot on install (same canonical name, new
    nature)."""

    def _install(self, target, item, outcome="success"):
        from world.medical.procedures import _resolve_install

        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": outcome},
        ):
            _resolve_install(
                actor, target, organ_item=item, location="chest",
            )
        return actor

    def test_spec_item_rebuilds_the_slot(self):
        """Installing a cybernetic heart replaces the flesh heart's
        NATURE while keeping the canonical name — capacity wiring
        untouched, organ now chrome."""
        target = _patient()
        open_incision(target, "chest")
        self._install(target, _organ_item(organ_spec=dict(CYBER_HEART_SPEC)))

        heart = target.medical_state.organs["heart"]
        self.assertTrue(heart.data.get("inorganic"))
        self.assertEqual(heart.max_hp, 20)
        self.assertEqual(heart.current_hp, 20)  # pristine
        self.assertEqual(heart.container, "chest")
        self.assertIs(heart.medical_state, target.medical_state)

    def test_damaged_spec_item_installs_damaged(self):
        target = _patient()
        open_incision(target, "chest")
        self._install(
            target,
            _organ_item(organ_spec=dict(CYBER_HEART_SPEC), condition="damaged"),
        )
        heart = target.medical_state.organs["heart"]
        self.assertEqual(heart.current_hp, 12)  # 60% of 20
        self.assertEqual(heart.wound_stage, "fresh")

    def test_legacy_item_keeps_restore_behavior(self):
        """No spec = plain biological organ: the existing slot organ
        is restored, its nature unchanged."""
        target = _patient()
        open_incision(target, "chest")
        original = target.medical_state.organs["heart"]
        original.current_hp = 3
        self._install(target, _organ_item(organ_spec=None))

        heart = target.medical_state.organs["heart"]
        self.assertIs(heart, original)
        self.assertEqual(heart.current_hp, heart.max_hp)
        self.assertFalse(heart.data.get("inorganic"))

    def test_harvest_writes_the_spec_onto_the_item(self):
        """The other half of the round trip: extraction carries the
        organ's spec so chrome reinstalls as chrome."""
        from world.medical.procedures import _configure_harvested_item

        target = _patient()
        cyber = Organ("heart", organ_data=dict(CYBER_HEART_SPEC))
        cyber.medical_state = target.medical_state
        target.medical_state.organs["heart"] = cyber

        item = SimpleNamespace(db=SimpleNamespace())
        _configure_harvested_item(
            item, organ_name="heart", condition="pristine",
            source=target, organ_data=cyber.to_dict(),
        )
        self.assertTrue(item.db.organ_spec.get("inorganic"))
        self.assertEqual(item.db.organ_spec.get("max_hp"), 20)


class TestFullHealStandard(TestCase):
    """#526 review: @heal restores PRESENT anatomy — tombstones are
    absence records, not injuries."""

    def test_severed_tombstones_stay_severed(self):
        target = _patient()
        _sever_right_arm(target)
        target.medical_state.full_heal()
        stump = target.medical_state.organs["right_humerus"]
        self.assertEqual(stump.current_hp, 0)
        self.assertEqual(stump.wound_stage, "severed")

    def test_harvested_module_does_not_resurrect(self):
        """The duplication exploit: harvest the module (item in
        hand), @heal the patient, ability returns.  Must not."""
        from world.medical.augments import find_ability

        target = _patient()
        spec = dict(SHOTGUN_MODULE_SPEC)
        spec["container"] = "left_arm"
        organ = Organ("left_forearm_hardpoint", organ_data=spec)
        organ.current_hp = 0
        organ.wound_stage = "severed"  # harvest tombstone
        organ.medical_state = target.medical_state
        target.medical_state.organs["left_forearm_hardpoint"] = organ

        target.medical_state.full_heal()
        self.assertEqual(organ.current_hp, 0)
        found, _spec = find_ability(target, "shotgun")
        self.assertIsNone(found)

    def test_destroyed_in_place_restores_clean(self):
        target = _patient()
        heart = target.medical_state.organs["heart"]
        heart.current_hp = 0
        heart.wound_stage = "destroyed"
        heart.injury_type = "bullet"
        heart.stabilized = True
        heart.tourniqueted = True
        healed = target.medical_state.full_heal()
        self.assertGreaterEqual(healed, 1)
        self.assertEqual(heart.current_hp, heart.max_hp)
        self.assertIsNone(heart.wound_stage)
        self.assertIsNone(heart.injury_type)
        self.assertFalse(heart.stabilized)
        self.assertFalse(heart.tourniqueted)

    def test_vitals_and_conditions_reset(self):
        from world.medical.conditions import BleedingCondition, MedicalCondition

        target = _patient()
        state = target.medical_state
        with patch.object(
            MedicalCondition, "start_condition", lambda self, ch: None,
        ):
            state.add_condition(BleedingCondition(4, "chest"))
        state.blood_level = 40.0
        state.pain_level = 12.0
        state.full_heal()
        self.assertEqual(state.conditions, [])
        self.assertEqual(state.blood_level, 100.0)
        self.assertEqual(state.pain_level, 0.0)


class TestAugmentOrganPredicate(TestCase):
    """#526 review: the @resetmedical preservation rule."""

    def test_predicate_classifies_the_templates(self):
        from world.anatomy import get_species_organs
        from world.medical.core import is_augment_organ

        table = get_species_organs(None)
        # New-container anatomy: no table entry.
        tail = Organ("cybernetic_tailbone", organ_data=dict(TAIL_ORGAN_SPEC))
        self.assertTrue(is_augment_organ(tail, table))
        # Canonical-name chrome: table entry, inorganic spec.
        cyber_heart = Organ("heart", organ_data=dict(CYBER_HEART_SPEC))
        self.assertTrue(is_augment_organ(cyber_heart, table))
        # Flesh-mounted module host: flesh spec + abilities.
        host_spec = dict(get_species_organs(None)["left_metacarpals"])
        host_spec["abilities"] = {"nailz": {"type": "natural_weapon"}}
        host = Organ("left_metacarpals", organ_data=host_spec)
        self.assertTrue(is_augment_organ(host, table))
        # Factory flesh: not an augment.
        flesh = _patient().medical_state.organs["heart"]
        self.assertFalse(is_augment_organ(flesh, table))


def _severed_cyber_arm(deployed=False):
    """Stub Appendage carrying a severed cyber-arm snapshot (#526
    reattach)."""
    item = SimpleNamespace()
    item.key = "cybernetic right arm"
    item.deleted = False

    def _delete():
        item.deleted = True
    item.delete = _delete
    snapshot = {"organs": {
        "right_humerus": {
            "container": "right_arm", "current_hp": 30, "max_hp": 30,
            "wound_stage": "severed",
            "data": {"container": "right_arm", "max_hp": 30,
                     "inorganic": True, "prosthetic_frame": True},
        },
        "right_metacarpals": {
            "container": "right_hand", "current_hp": 18, "max_hp": 18,
            "wound_stage": "severed",
            "data": {"container": "right_hand", "max_hp": 18,
                     "inorganic": True, "prosthetic_frame": True,
                     "grasping": True},
        },
        "right_forearm_hardpoint": {
            "container": "right_arm", "current_hp": 12, "max_hp": 12,
            "wound_stage": "severed",
            "ability_state": {"shotgun": {"deployed": deployed,
                                          "weapon_dbref": None}},
            "data": {"container": "right_arm", "inorganic": True,
                     "prosthetic_frame": True, "hardpoint": "forearm",
                     "abilities": {"shotgun": {
                         "type": "integrated_weapon",
                         "slot": "right_hand", "weapon_prototype": "X"}}},
        },
    }}
    item.get_medical_snapshot = lambda: snapshot
    item.db = SimpleNamespace(
        location_name="right_arm",
        longdesc_data={
            "right_arm": "A full cybernetic right arm.",
            "right_hand": "An articulated alloy right hand.",
        },
    )
    item.get_display_name = lambda looker=None: item.key
    return item


class TestLimbReattach(TestCase):
    """#526 follow-up (user decision 2026-06-13): a severed cyber
    limb reattaches whole — chassis + seated module, over a stump,
    onto any compatible body."""

    def _amputee(self):
        target = _patient()
        for o in target.medical_state.organs.values():
            if o.container in ("right_arm", "right_hand"):
                o.current_hp = 0
                o.wound_stage = "severed"
        target.longdesc = {"head": None}
        return target

    def _reattach(self, target, item, outcome="success"):
        from world.medical.procedures import _resolve_install_limb
        actor = _surgeon()
        with patch(
            "world.medical.procedures.roll_procedure",
            return_value={"outcome": outcome},
        ):
            _resolve_install_limb(
                actor, target, organ_item=item, location="right_arm",
            )
        return actor

    def test_is_cybernetic_limb_detects(self):
        from world.medical.procedures import is_cybernetic_limb
        self.assertTrue(is_cybernetic_limb(_severed_cyber_arm()))

    def test_reattach_rebuilds_the_limb(self):
        from world.medical.augments import find_ability

        target = self._amputee()
        open_incision(target, "right_arm")
        item = _severed_cyber_arm()
        self._reattach(target, item)

        organs = target.medical_state.organs
        self.assertEqual(organs["right_humerus"].current_hp, 30)
        self.assertTrue(organs["right_humerus"].data.get("inorganic"))
        self.assertIn("right_forearm_hardpoint", organs)
        found, _spec = find_ability(target, "shotgun")
        self.assertIsNotNone(found)
        self.assertEqual(
            target.longdesc["right_arm"], "A full cybernetic right arm.",
        )
        self.assertTrue(item.deleted)

    def test_reattach_comes_back_retracted(self):
        target = self._amputee()
        open_incision(target, "right_arm")
        item = _severed_cyber_arm(deployed=True)
        self._reattach(target, item)
        hp = target.medical_state.organs["right_forearm_hardpoint"]
        self.assertFalse(hp.ability_state["shotgun"]["deployed"])

    def test_bare_chassis_reattaches(self):
        """No module seated — the chassis still goes back on."""
        target = self._amputee()
        open_incision(target, "right_arm")
        item = _severed_cyber_arm()
        # Strip the module from the snapshot.
        del item.get_medical_snapshot()["organs"]["right_forearm_hardpoint"]
        self._reattach(target, item)
        self.assertIn("right_humerus", target.medical_state.organs)
        self.assertNotIn(
            "right_forearm_hardpoint", target.medical_state.organs,
        )
        self.assertTrue(item.deleted)

    def test_living_arm_blocks_reattach(self):
        target = _patient()
        target.longdesc = {"head": None}
        open_incision(target, "right_arm")
        item = _severed_cyber_arm()
        actor = self._reattach(target, item)
        self.assertFalse(item.deleted)
        self.assertTrue(any("living" in m for m in actor.messages))

    def test_reattach_needs_incision(self):
        target = self._amputee()
        item = _severed_cyber_arm()
        actor = self._reattach(target, item)
        self.assertFalse(item.deleted)
        self.assertTrue(any("isn't open" in m for m in actor.messages))

    def test_reattach_keys_on_frame_not_inorganic(self):
        """The frame marker is the discriminator, not organ content:
        strip ``prosthetic_frame`` (leaving the chrome) and the limb
        no longer reattaches."""
        from world.medical.procedures import is_cybernetic_limb
        item = _severed_cyber_arm()
        for d in item.get_medical_snapshot()["organs"].values():
            d["data"].pop("prosthetic_frame", None)
        self.assertFalse(is_cybernetic_limb(item))

    def test_flesh_hand_with_cyberware_not_reattachable(self):
        """The user's case: a flesh hand with cyberware implanted in
        it (Nailz) is still flesh — no prosthetic frame, so it
        necroses and doesn't reattach.  The cyberware harvests out
        separately."""
        from world.medical.procedures import is_cybernetic_limb

        item = SimpleNamespace()
        snap = {"organs": {
            "left_metacarpals": {
                "container": "left_hand", "current_hp": 0,
                # Flesh organ carrying an implanted ability — and even
                # a stray inorganic sub-part — but NO prosthetic frame.
                "data": {"container": "left_hand", "inorganic": True,
                         "abilities": {"nailz": {"type": "natural_weapon"}}},
            },
        }}
        item.get_medical_snapshot = lambda: snap
        item.db = SimpleNamespace(location_name="left_hand")
        self.assertFalse(is_cybernetic_limb(item))

    def test_operate_lists_cyber_limb_as_donor(self):
        from commands.CmdOperate import _list_donor_organs

        limb = _severed_cyber_arm()
        caller = SimpleNamespace(contents=[limb])
        donors = _list_donor_organs(caller)
        self.assertTrue(any(it is limb for it, _label in donors))


class TestSeveredCyberProse(TestCase):
    def test_inorganic_parts_get_chrome_prose(self):
        from world.anatomy.severed_parts import get_severed_part_description

        for condition in ("pristine", "damaged", "putrid"):
            prose = get_severed_part_description(
                "human", "right_arm", condition, inorganic=True,
            )
            self.assertIn("cybernetic", prose.lower())
            self.assertNotIn("muscle", prose.lower())

    def test_flesh_parts_unchanged(self):
        from world.anatomy.severed_parts import get_severed_part_description

        prose = get_severed_part_description("human", "right_arm", "pristine")
        self.assertIn("muscle", prose.lower())


class TestCyberneticShotgunMessages(TestCase):
    def test_message_set_loads_for_every_phase(self):
        from world.combat.messages import get_combat_message
        from world.combat.messages.cybernetic_shotgun import MESSAGES

        for phase in ("initiate", "hit", "miss", "kill"):
            self.assertGreaterEqual(len(MESSAGES[phase]), 30)
            result = get_combat_message(
                "cybernetic_shotgun", phase,
                hit_location="chest", damage=20,
            )
            self.assertNotIn("Error", result["attacker_msg"])
            # Non-fallback: fallback prose is "You <phase> ... with".
            self.assertNotIn(f"You {phase}", result["attacker_msg"])

    def test_every_variant_formats_cleanly(self):
        """Every template in every phase must format with the
        standard kwargs — a typo'd placeholder fails loudly here
        instead of mid-combat."""
        from world.combat.messages.cybernetic_shotgun import MESSAGES

        kwargs = {
            "attacker_name": "A", "target_name": "B",
            "item_name": "gun", "item": "gun",
            "hit_location": "chest", "damage": 20, "phase": "x",
        }
        for phase, variants in MESSAGES.items():
            for variant in variants:
                for key in ("attacker_msg", "victim_msg", "observer_msg"):
                    variant[key].format(**kwargs)


class TestCyberneticTeethMessages(TestCase):
    """Jawz bite message set (#525)."""

    def test_message_set_loads_for_every_phase(self):
        from world.combat.messages import get_combat_message
        from world.combat.messages.cybernetic_teeth import MESSAGES

        for phase in ("initiate", "hit", "miss", "kill"):
            self.assertGreaterEqual(len(MESSAGES[phase]), 12)
            result = get_combat_message(
                "cybernetic_teeth", phase, hit_location="arm",
            )
            self.assertNotIn("Error", result["attacker_msg"])
            self.assertNotIn(f"You {phase}", result["attacker_msg"])

    def test_every_variant_formats_cleanly(self):
        from world.combat.messages.cybernetic_teeth import MESSAGES

        kwargs = {
            "attacker_name": "A", "target_name": "B",
            "item_name": "fangs", "item": "fangs",
            "hit_location": "arm", "phase": "x",
        }
        for phase, variants in MESSAGES.items():
            for variant in variants:
                for key in ("attacker_msg", "victim_msg", "observer_msg"):
                    variant[key].format(**kwargs)
