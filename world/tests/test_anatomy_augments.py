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
