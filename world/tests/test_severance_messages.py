"""Tests for the severance messaging library (issue #332).

Covers:

* The loader's location → module routing (pair-key aliases work).
* Injury-type and severity routing (cut/stab/laceration × grievous/minor).
* Fallback when an injury type / severity isn't seeded.
* Each per-location module has the expected MESSAGES shape with content
  in every cell.
* Per-audience message rendering (attacker / victim / observer).
* Identity-aware observer_template wiring.
* Hit-location underscore handling and color wrapping.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from world.combat.messages.severance import (
    _LIMB_ALIASES,
    _resolve_module_name,
    get_severance_message,
)


class _FakeChar:
    """Minimal character stub for loader tests."""

    def __init__(self, key="char"):
        self.key = key

    def get_display_name(self, looker):
        return self.key


class _FakeItem:
    def __init__(self, key="blade"):
        self.key = key


# =====================================================================
# Routing / module resolution
# =====================================================================


class ModuleResolutionTests(TestCase):

    def test_head_alias_routes_to_head_module(self):
        self.assertEqual(_resolve_module_name("head"), "head")

    def test_neck_alias_routes_to_head_module(self):
        # Decapitation is a "neck container" hit, but the narrative
        # template library is the head.
        self.assertEqual(_resolve_module_name("neck"), "head")

    def test_limb_side_routes_to_pair_module(self):
        self.assertEqual(_resolve_module_name("left_arm"), "arms")
        self.assertEqual(_resolve_module_name("right_arm"), "arms")
        self.assertEqual(_resolve_module_name("left_hand"), "hands")
        self.assertEqual(_resolve_module_name("right_thigh"), "thighs")
        self.assertEqual(_resolve_module_name("left_shin"), "shins")
        self.assertEqual(_resolve_module_name("right_foot"), "feet")

    def test_pair_key_passes_through(self):
        for pair_key in ("arms", "hands", "thighs", "shins", "feet"):
            with self.subTest(pair_key=pair_key):
                self.assertEqual(_resolve_module_name(pair_key), pair_key)

    def test_aliases_table_covers_all_severable_limbs(self):
        from world.combat.constants import SEVERABLE_CONTAINERS

        for loc in SEVERABLE_CONTAINERS:
            with self.subTest(location=loc):
                self.assertIn(loc, _LIMB_ALIASES,
                              f"Severable {loc} missing from _LIMB_ALIASES")


# =====================================================================
# Per-module content presence
# =====================================================================


class DataLayerTests(TestCase):

    EXPECTED_INJURY_TYPES = ("cut", "stab", "laceration")
    EXPECTED_SEVERITIES = ("grievous", "minor")
    LOCATIONS = ("head", "arms", "hands", "thighs", "shins", "feet")

    def test_each_location_has_messages_dict(self):
        import importlib
        for loc in self.LOCATIONS:
            with self.subTest(location=loc):
                mod = importlib.import_module(
                    f"world.combat.messages.severance.{loc}"
                )
                self.assertTrue(hasattr(mod, "MESSAGES"))

    def test_each_cell_has_variants(self):
        """Every (location, injury_type, severity) cell has at least 3
        variants, each with all three audience messages."""
        import importlib
        for loc in self.LOCATIONS:
            mod = importlib.import_module(
                f"world.combat.messages.severance.{loc}"
            )
            for itype in self.EXPECTED_INJURY_TYPES:
                for sev in self.EXPECTED_SEVERITIES:
                    cell = mod.MESSAGES.get(itype, {}).get(sev, [])
                    with self.subTest(loc=loc, injury=itype, severity=sev):
                        self.assertGreaterEqual(
                            len(cell), 3,
                            f"{loc}.{itype}.{sev} has only "
                            f"{len(cell)} variants",
                        )
                        for variant in cell:
                            for key in ("attacker_msg", "victim_msg",
                                        "observer_msg"):
                                self.assertIn(
                                    key, variant,
                                    f"{loc}.{itype}.{sev} missing {key}"
                                )


# =====================================================================
# Loader rendering
# =====================================================================


class LoaderRenderTests(TestCase):

    def test_returns_required_keys(self):
        attacker = _FakeChar("Vasquez")
        target = _FakeChar("Maria")
        item = _FakeItem("katana")
        msgs = get_severance_message(
            "head", "cut", attacker, target, item,
            severity="grievous", hit_location="neck",
        )
        for key in ("attacker_msg", "victim_msg", "observer_msg",
                    "observer_template", "observer_char_refs"):
            self.assertIn(key, msgs)

    def test_observer_char_refs_populated(self):
        attacker = _FakeChar("Vasquez")
        target = _FakeChar("Maria")
        msgs = get_severance_message(
            "left_arm", "cut", attacker, target, _FakeItem("sword"),
        )
        self.assertEqual(msgs["observer_char_refs"]["actor"], attacker)
        self.assertEqual(msgs["observer_char_refs"]["target_char"], target)

    def test_hit_location_underscore_replaced(self):
        attacker = _FakeChar("Vasquez")
        target = _FakeChar("Maria")
        msgs = get_severance_message(
            "left_arm", "cut", attacker, target, _FakeItem("sword"),
            hit_location="left_arm",
        )
        # No template should still contain underscored "left_arm"
        for key in ("attacker_msg", "victim_msg", "observer_msg",
                    "observer_template"):
            self.assertNotIn("left_arm", msgs[key])

    def test_messages_are_color_wrapped_red(self):
        attacker = _FakeChar("Vasquez")
        target = _FakeChar("Maria")
        msgs = get_severance_message(
            "head", "cut", attacker, target, _FakeItem("katana"),
        )
        # Severance is a dramatic positive-strike beat → bright red.
        self.assertTrue(msgs["attacker_msg"].startswith("|r"))
        self.assertTrue(msgs["attacker_msg"].endswith("|n"))

    def test_observer_template_has_identity_tokens(self):
        attacker = _FakeChar("Vasquez")
        target = _FakeChar("Maria")
        msgs = get_severance_message(
            "head", "cut", attacker, target, _FakeItem("katana"),
        )
        # The observer_template should carry the identity-aware tokens
        # (literal {actor}/{target_char}) so msg_room_identity can
        # resolve them per-observer.
        template = msgs["observer_template"]
        self.assertTrue(
            "{actor}" in template or "{target_char}" in template,
            f"Observer template has no identity tokens: {template!r}"
        )

    def test_attacker_msg_uses_you_perspective(self):
        attacker = _FakeChar("Vasquez")
        target = _FakeChar("Maria")
        # Try several templates — at least one should use "Your"/"You".
        outputs = [
            get_severance_message(
                "head", "cut", attacker, target, _FakeItem("katana"),
            )["attacker_msg"]
            for _ in range(15)
        ]
        joined = " ".join(outputs)
        # Should not contain the attacker's name in attacker_msg.
        self.assertNotIn("Vasquez", joined)

    def test_victim_msg_uses_your_perspective(self):
        attacker = _FakeChar("Vasquez")
        target = _FakeChar("Maria")
        outputs = [
            get_severance_message(
                "left_hand", "cut", attacker, target, _FakeItem("sword"),
            )["victim_msg"]
            for _ in range(15)
        ]
        joined = " ".join(outputs)
        # Should not contain the victim's name in victim_msg.
        self.assertNotIn("Maria", joined)


# =====================================================================
# Fallback paths
# =====================================================================


class FallbackTests(TestCase):

    def test_unknown_injury_type_falls_back_to_cut(self):
        attacker = _FakeChar("A")
        target = _FakeChar("B")
        # An unknown injury type still produces a valid message dict.
        msgs = get_severance_message(
            "head", "bullet", attacker, target,  # bullet isn't severing
        )
        self.assertIn("attacker_msg", msgs)
        self.assertTrue(len(msgs["attacker_msg"]) > 0)

    def test_unknown_severity_falls_back_to_grievous(self):
        attacker = _FakeChar("A")
        target = _FakeChar("B")
        msgs = get_severance_message(
            "head", "cut", attacker, target, severity="catastrophic",
        )
        self.assertIn("attacker_msg", msgs)
        self.assertTrue(len(msgs["attacker_msg"]) > 0)

    def test_unknown_location_falls_through_to_generic(self):
        # Location with no module returns the generic fallback template.
        attacker = _FakeChar("A")
        target = _FakeChar("B")
        msgs = get_severance_message(
            "tentacle", "cut", attacker, target,
            hit_location="tentacle",
        )
        # Generic fallback still produces all keys.
        self.assertIn("attacker_msg", msgs)
        self.assertIn("victim_msg", msgs)
        self.assertIn("observer_msg", msgs)
