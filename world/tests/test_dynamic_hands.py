"""Tests for the dynamic hands view (#307, PR-H2).

The ``Character.hands`` property is now a derived view of the
species' grasping appendages minus the current severance state.
Held items live in the ``held_items`` AttributeProperty backing
store; the property's setter routes writes back through the
backing store with alias resolution ("left" → "left_hand").

This module exercises the pure helper functions
(``_canonical_hand`` / ``_humanize_hand``) plus the property
shape against light stubs.  The full Character integration
(Evennia's typeclass machinery) is covered by existing wield /
unwield / sever tests via the integration suite.

Run via::

    evennia test world.tests.test_dynamic_hands
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from typeclasses.characters import (
    HAND_NAME_ALIASES,
    _canonical_hand,
    _humanize_hand,
)


# ---------------------------------------------------------------------
# Hand-name aliases — user-facing shorthand → canonical key
# ---------------------------------------------------------------------


class CanonicalHandResolution(TestCase):

    def test_left_resolves_to_left_hand(self):
        self.assertEqual(_canonical_hand("left"), "left_hand")

    def test_right_resolves_to_right_hand(self):
        self.assertEqual(_canonical_hand("right"), "right_hand")

    def test_single_letter_l_resolves(self):
        self.assertEqual(_canonical_hand("l"), "left_hand")

    def test_single_letter_r_resolves(self):
        self.assertEqual(_canonical_hand("r"), "right_hand")

    def test_canonical_passes_through_unchanged(self):
        self.assertEqual(_canonical_hand("left_hand"), "left_hand")
        self.assertEqual(_canonical_hand("right_hand"), "right_hand")

    def test_case_insensitive(self):
        self.assertEqual(_canonical_hand("LEFT"), "left_hand")
        self.assertEqual(_canonical_hand("Right"), "right_hand")

    def test_whitespace_trimmed(self):
        self.assertEqual(_canonical_hand("  left  "), "left_hand")

    def test_unknown_passes_through(self):
        """Tentacle / claw / future grasping appendage names that
        aren't in the alias table fall through unchanged so the
        species can declare its own canonical names."""
        self.assertEqual(_canonical_hand("tentacle_1"), "tentacle_1")
        self.assertEqual(_canonical_hand("prehensile_tail"),
                         "prehensile_tail")

    def test_non_string_passes_through(self):
        """Defensive: dispatch shouldn't blow up on bad input."""
        self.assertIsNone(_canonical_hand(None))


class HumanizeHand(TestCase):

    def test_basic_underscore_to_space(self):
        self.assertEqual(_humanize_hand("left_hand"), "left hand")
        self.assertEqual(_humanize_hand("right_hand"), "right hand")

    def test_multi_underscore(self):
        self.assertEqual(_humanize_hand("prehensile_tail"),
                         "prehensile tail")

    def test_non_string_coerced(self):
        self.assertEqual(_humanize_hand(None), "None")


class AliasTableShape(TestCase):
    """Pin the alias table so future additions notice if they break
    the user-facing wield shorthand convention."""

    def test_left_is_aliased(self):
        self.assertIn("left", HAND_NAME_ALIASES)
        self.assertEqual(HAND_NAME_ALIASES["left"], "left_hand")

    def test_right_is_aliased(self):
        self.assertIn("right", HAND_NAME_ALIASES)
        self.assertEqual(HAND_NAME_ALIASES["right"], "right_hand")

    def test_single_letters_aliased(self):
        self.assertEqual(HAND_NAME_ALIASES["l"], "left_hand")
        self.assertEqual(HAND_NAME_ALIASES["r"], "right_hand")


# ---------------------------------------------------------------------
# Anatomy + severance integration via the hands property
# ---------------------------------------------------------------------


class _HandsViewStub:
    """Minimal Character-shaped stub that exercises just the
    ``hands`` property logic.

    The real Character is an Evennia typeclass with DB persistence;
    here we recreate the property method by hand against plain
    attribute storage so we can test the derivation contract
    without a real ``MedicalState``.
    """

    def __init__(self, species="human", severed=None,
                 held_items=None, medical_state=None):
        self.db = SimpleNamespace(species=species)
        self._severed = set(severed or ())
        self.held_items = dict(held_items or {})
        if medical_state is not None:
            self.medical_state = medical_state

    def _get_severed_locations(self):
        return self._severed

    @property
    def hands(self):
        # Direct copy of the Character.hands property body for
        # isolation testing.  (The real property also runs a
        # migration step which is exercised separately.)
        from world.anatomy import get_species_grasping_containers
        species = getattr(self.db, "species", None)
        grasping = set(get_species_grasping_containers(species))

        # Per-character grasping overlay (ANATOMY_AUGMENTS_SPEC §3.4).
        try:
            medical_state = self.medical_state
        except AttributeError:
            medical_state = None
        if medical_state is not None:
            for organ in getattr(medical_state, "organs", {}).values():
                organ_data = getattr(organ, "data", None)
                if organ_data and organ_data.get("grasping"):
                    container = getattr(organ, "container", None)
                    if container:
                        grasping.add(container)

        severed = self._get_severed_locations()

        # Functional-anatomy gate (#526 review) — mirror of the real
        # property: all organs at a grasping container tombstoned =
        # no grip, even when the severed set missed it (chain
        # severance suppresses downstream wounds).
        if medical_state is not None:
            organs = getattr(medical_state, "organs", {}) or {}
            for location in list(grasping):
                at_location = [
                    o for o in organs.values()
                    if getattr(o, "container", None) == location
                ]
                if at_location and not any(
                        getattr(o, "current_hp", 1) > 0
                        for o in at_location):
                    severed = set(severed) | {location}

        held = self.held_items or {}
        return {
            location: held.get(location)
            for location in grasping
            if location not in severed
        }


class HandsViewAgainstAnatomy(TestCase):

    def test_human_with_no_held_items_has_two_empty_slots(self):
        char = _HandsViewStub(species="human")
        self.assertEqual(
            char.hands,
            {"left_hand": None, "right_hand": None},
        )

    def test_held_items_surface_at_their_slots(self):
        sentinel = SimpleNamespace(key="knife")
        char = _HandsViewStub(
            species="human",
            held_items={"right_hand": sentinel},
        )
        self.assertIs(char.hands["right_hand"], sentinel)
        self.assertIsNone(char.hands["left_hand"])

    def test_severed_left_excluded_from_view(self):
        char = _HandsViewStub(
            species="human", severed={"left_hand"},
        )
        view = char.hands
        self.assertNotIn("left_hand", view)
        self.assertIn("right_hand", view)

    def test_grasping_organ_adds_slot(self):
        """ANATOMY_AUGMENTS §3.4: the prehensile cybernetic tail is a
        third hand — a grasping-flagged organ adds its container."""
        tail_organ = SimpleNamespace(
            data={"grasping": True}, container="tail",
        )
        state = SimpleNamespace(organs={"cybernetic_tailbone": tail_organ})
        char = _HandsViewStub(species="human", medical_state=state)
        self.assertEqual(
            set(char.hands), {"left_hand", "right_hand", "tail"},
        )
        self.assertIsNone(char.hands["tail"])

    def test_chain_severed_hand_drops_out(self):
        """The Laszlo finding (#526 review): severing the ARM
        suppresses the hand's own wounds (cut-point filter), so the
        severed set misses the hand — the organ-truth gate must
        still remove the slot.  No holding cigarettes in a hand
        attached to nothing."""
        dead_hand_organ = SimpleNamespace(
            data={}, container="right_hand", current_hp=0,
        )
        live_hand_organ = SimpleNamespace(
            data={}, container="left_hand", current_hp=15,
        )
        state = SimpleNamespace(organs={
            "right_metacarpals": dead_hand_organ,
            "left_metacarpals": live_hand_organ,
        })
        char = _HandsViewStub(species="human", medical_state=state)
        view = char.hands
        self.assertNotIn("right_hand", view)
        self.assertIn("left_hand", view)

    def test_severed_tail_drops_out_of_view(self):
        """The existing severance subtraction covers the augment slot
        with no new code."""
        tail_organ = SimpleNamespace(
            data={"grasping": True}, container="tail",
        )
        state = SimpleNamespace(organs={"cybernetic_tailbone": tail_organ})
        char = _HandsViewStub(
            species="human", medical_state=state, severed={"tail"},
        )
        self.assertEqual(set(char.hands), {"left_hand", "right_hand"})

    def test_severed_left_arm_excludes_left_hand(self):
        """Severance of a parent location should propagate via the
        existing _get_severed_locations contract.  Here we simulate
        that by including the hand directly in the severed set."""
        char = _HandsViewStub(
            species="human", severed={"left_arm", "left_hand"},
        )
        self.assertNotIn("left_hand", char.hands)
        self.assertIn("right_hand", char.hands)

    def test_both_hands_severed_returns_empty(self):
        char = _HandsViewStub(
            species="human",
            severed={"left_hand", "right_hand"},
        )
        self.assertEqual(char.hands, {})

    def test_rat_has_no_hands(self):
        char = _HandsViewStub(species="rat")
        self.assertEqual(char.hands, {})

    def test_rat_with_held_items_still_no_hands(self):
        """Defensive: even if some legacy data has ``held_items``
        populated on a rat, the derived view respects the species'
        empty ``grasping_containers``."""
        sentinel = SimpleNamespace(key="cheese")
        char = _HandsViewStub(
            species="rat",
            held_items={"left_hand": sentinel, "right_hand": None},
        )
        self.assertEqual(char.hands, {})

    def test_held_item_at_severed_slot_hidden(self):
        """A wielded item at a slot that gets severed disappears
        from the view — the sever pipeline (PR-H0) drops the
        physical item to the room independently."""
        sentinel = SimpleNamespace(key="severed_arm_knife")
        char = _HandsViewStub(
            species="human",
            severed={"left_hand"},
            held_items={"left_hand": sentinel},
        )
        self.assertNotIn("left_hand", char.hands)


class HandsViewKeySet(TestCase):
    """Pin the contract that view keys are canonical anatomical
    names, not the legacy "left" / "right" shorthand.  This is the
    critical migration assertion — pre-PR-H2 consumers that ask
    for ``hands["left"]`` now get a KeyError, surfacing the
    drift rather than silently returning ``None``."""

    def test_keys_are_anatomical(self):
        char = _HandsViewStub(species="human")
        for key in char.hands:
            self.assertTrue(
                key.endswith("_hand") or "_" in key,
                f"Hand key {key!r} should be a canonical container name",
            )

    def test_legacy_left_key_absent(self):
        char = _HandsViewStub(species="human")
        self.assertNotIn("left", char.hands)
        self.assertNotIn("right", char.hands)
