"""Tests for the generic consumable decrement helper
(:func:`world.consumables.consume_use`).

The smoke commands and the medical ``use_item`` wrapper both
delegate here.  These tests pin the contract independent of
either consumer.
"""
from __future__ import annotations

from unittest import TestCase

from types import SimpleNamespace

from world import consumables
from world.consumables import consume_use


class _Attributes:
    def __init__(self, **initial):
        self._values = dict(initial)

    def get(self, key, default=None):
        return self._values.get(key, default)

    def add(self, key, value):
        self._values[key] = value


class _Item:
    def __init__(self, uses_left=3, max_uses=3, *, with_attrs=True):
        if with_attrs:
            self.attributes = _Attributes(
                uses_left=uses_left, max_uses=max_uses,
            )
        self.deleted = False

    def delete(self):
        self.deleted = True


class TestConsumeUseBasic(TestCase):
    def test_decrements_uses_left(self):
        item = _Item(uses_left=3)
        outcome = consume_use(item)
        self.assertEqual(outcome["success"], True)
        self.assertEqual(outcome["destroyed"], False)
        self.assertEqual(item.attributes.get("uses_left"), 2)
        self.assertFalse(item.deleted)

    def test_destroys_on_final_use(self):
        item = _Item(uses_left=1)
        outcome = consume_use(item)
        self.assertEqual(outcome["destroyed"], True)
        self.assertTrue(item.deleted)
        self.assertEqual(item.attributes.get("uses_left"), 0)

    def test_zero_uses_returns_failure(self):
        item = _Item(uses_left=0)
        outcome = consume_use(item)
        self.assertEqual(outcome["success"], False)
        self.assertEqual(outcome["destroyed"], False)
        self.assertFalse(item.deleted)

    def test_no_attributes_surface_returns_failure(self):
        # Object without ``.attributes`` — degrades gracefully.
        item = _Item(with_attrs=False)
        outcome = consume_use(item)
        self.assertEqual(outcome["success"], False)
        self.assertFalse(item.deleted)


class TestConsumeUseDestroyCallback(TestCase):
    def test_callback_fires_just_before_delete(self):
        item = _Item(uses_left=1)
        events = []

        def _on_destroy():
            # Callback runs BEFORE the item is deleted — the
            # cigarette-side burnout broadcast wants to reference
            # the still-extant item for display name etc.
            events.append(("on_destroy_called", item.deleted))

        consume_use(item, on_destroy=_on_destroy)
        self.assertEqual(events, [("on_destroy_called", False)])
        self.assertTrue(item.deleted)

    def test_callback_only_fires_on_destruction(self):
        item = _Item(uses_left=3)
        fired = []
        consume_use(item, on_destroy=lambda: fired.append(True))
        self.assertEqual(fired, [])

    def test_callback_exception_does_not_block_delete(self):
        """The lifecycle invariant (zero uses ⇒ gone) is more
        important than a buggy flavor callback."""
        item = _Item(uses_left=1)

        def _bad_callback():
            raise RuntimeError("boom")

        outcome = consume_use(item, on_destroy=_bad_callback)
        self.assertEqual(outcome["destroyed"], True)
        self.assertTrue(item.deleted)


# ===================================================================
# supports_delivery — delivery tags + legacy medical_type migration
# ===================================================================


class _Tags:
    """Tag-handler stub matching Evennia's (value, category) calls."""

    def __init__(self, *pairs):
        self._tags = set(pairs)

    def has(self, value, category=None):
        return (value, category) in self._tags

    def add(self, value, category=None):
        self._tags.add((value, category))


class _TaggedItem:
    def __init__(self, *, tags=(), medical_type=None):
        self.tags = _Tags(*tags)
        attrs = {}
        if medical_type is not None:
            attrs["medical_type"] = medical_type
        self.attributes = _Attributes(**attrs)


class TestSupportsDelivery(TestCase):
    def test_tagged_item_supports_its_method(self):
        from world.consumables import supports_delivery

        item = _TaggedItem(tags=[("inject", "delivery_method")])
        self.assertTrue(supports_delivery(item, "inject"))
        self.assertFalse(supports_delivery(item, "eat"))

    def test_none_item_unsupported(self):
        from world.consumables import supports_delivery

        self.assertFalse(supports_delivery(None, "eat"))

    def test_legacy_medical_type_self_heals_to_tags(self):
        """A pre-#474 item (medical_type, no tags) is migrated on
        first check: implied tags written, correct verb accepted."""
        from world.consumables import supports_delivery

        item = _TaggedItem(medical_type="pain_relief")
        self.assertTrue(supports_delivery(item, "inject"))
        # Tag was written back — the migration is once-per-item.
        self.assertTrue(item.tags.has("inject", category="delivery_method"))

    def test_legacy_wound_care_supports_both_apply_and_bandage(self):
        from world.consumables import supports_delivery

        item = _TaggedItem(medical_type="wound_care")
        self.assertTrue(supports_delivery(item, "bandage"))
        self.assertTrue(item.tags.has("apply", category="delivery_method"))
        self.assertTrue(item.tags.has("bandage", category="delivery_method"))

    def test_legacy_type_rejects_wrong_method(self):
        from world.consumables import supports_delivery

        item = _TaggedItem(medical_type="oxygen")
        self.assertFalse(supports_delivery(item, "eat"))
        # Migration still happened toward the implied verb.
        self.assertTrue(item.tags.has("inhale", category="delivery_method"))

    def test_unknown_medical_type_unsupported(self):
        """Types with no delivery mapping (surgical_treatment,
        healing_acceleration) stay non-consumable — preserved
        behavior."""
        from world.consumables import supports_delivery

        for mtype in ("surgical_treatment", "healing_acceleration", ""):
            item = _TaggedItem(medical_type=mtype)
            for verb in ("eat", "drink", "inject", "apply", "inhale",
                         "bandage", "smoke"):
                self.assertFalse(supports_delivery(item, verb))

    def test_legacy_smokables_map_to_smoke_delivery(self):
        from world.consumables import supports_delivery

        item = _TaggedItem(medical_type="herb")
        self.assertTrue(supports_delivery(item, "smoke"))


# ---------------------------------------------------------------------
# Hunger is pharmacology (#2074): the nutrition substance moves a
# soul's hunger meter through the SAME consumption path every
# character object uses — command, delivery gate, substance pipeline.
# ---------------------------------------------------------------------

import time as _time

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest


class _NutritionTestBase(BaseEvenniaTest):
    """Chars AND the room must be GAME typeclasses — apply_substance
    requires a medical body, and the eat command's room broadcast
    resolves identity handles, which the stock DefaultCharacter/
    DefaultRoom test fixtures don't carry."""

    def setUp(self):
        super().setUp()
        self.game_room = create_object(
            "typeclasses.rooms.Room", key="mess hall")

    def _game_char(self, key="Eater"):
        char = create_object(
            "typeclasses.characters.Character", key=key,
            location=self.game_room)
        # the test harness resets CMDSET_CHARACTER to core defaults —
        # re-add the game cmdset so the REAL eat verb is on the char
        char.cmdset.add(
            "commands.default_cmdsets.CharacterCmdSet", persistent=False)
        return char

    def _soul_char(self, hunger=0.6):
        char = self._game_char(key="TestSoul")
        char.tags.add("soul", category="npc_role")
        char.db.soul_needs = {"hunger": hunger, "_at": _time.time()}
        return char


class TestNutritionSubstance(_NutritionTestBase):
    """The nourish effect kind and its no-meter no-op."""

    def test_nourish_moves_soul_hunger(self):
        from world.souls import needs
        from world.substances import apply_substance

        soul = self._soul_char(hunger=0.6)
        result = apply_substance(soul, "nutrition")
        self.assertGreater(result["applied"].get("nourish", 0), 0)
        self.assertAlmostEqual(
            needs.pressure(soul, "hunger"), 0.45, delta=0.02)

    def test_nourish_noops_without_meter(self):
        """A consumer without a soul meter (a player, today) is
        untouched — no feedback, no phantom needs dict."""
        from world.substances import apply_substance

        char = self._game_char()
        result = apply_substance(char, "nutrition")
        self.assertEqual(result["applied"], {})
        self.assertIsNone(char.db.soul_needs)


class TestEatingFeedsThroughTheCommand(_NutritionTestBase):
    """End-to-end: the real eat verb is the only feeding path."""

    def test_eat_command_feeds_a_soul(self):
        from world.souls import needs

        soul = self._soul_char(hunger=0.6)
        snack = create_object(
            "typeclasses.items.Item", key="ration wafer",
            location=soul)
        snack.tags.add("eat", category="delivery_method")
        snack.db.drink_effects = {"nutrition": 2}
        snack.db.uses_left = 1
        soul.execute_cmd("eat wafer")
        self.assertAlmostEqual(
            needs.pressure(soul, "hunger"), 0.30, delta=0.02)

    def test_any_fixture_with_snacks_serves(self):
        """The serving membrane is no longer bar-only (#2074): a room
        fixture carrying db.snacks feeds through the real eat verb —
        the Rook's nutrient line pattern."""
        from world.souls import needs

        soul = self._soul_char(hunger=0.6)
        line = create_object(
            "typeclasses.items.Item", key="a test feed line",
            location=self.game_room)
        line.db.snacks = [{
            "name": "nutrient feed",
            "order_keywords": ("feed",),
            "effects": {"nutrition": 4},
            "taste": "Warm nothing.",
        }]
        soul.execute_cmd("eat feed")
        self.assertLessEqual(needs.pressure(soul, "hunger"), 0.05)


class TestBothDoorsAgree(TestCase):
    """`uses_left` had two decrement doors and they disagreed three ways
    (#2812). All three were latent — no item in the world was at or
    below zero — and all three are structural.
    """

    def _item(self, **attrs):
        store = dict(attrs)

        class _Attrs:
            def get(self, key, default=None):
                return store.get(key, default)

            def add(self, key, value):
                store[key] = value

        item = SimpleNamespace(attributes=_Attrs(), key="a bandage")
        item._store = store
        item.deleted = False

        def _delete():
            item.deleted = True
        item.delete = _delete
        return item

    def test_the_medical_door_deletes_at_zero(self):
        """`world/consumables.py` states the invariant: zero uses => gone.
        `treatments._consume_use` decremented and stopped, leaving a
        spent item in the world -- visible, holdable, and refused by
        every consumer that checks."""
        from world.medical.treatments import _consume_use
        item = self._item(uses_left=1)
        _consume_use(item)
        self.assertEqual(item._store["uses_left"], 0)
        self.assertTrue(item.deleted, "a spent item stayed in the world")

    def test_the_medical_door_still_leaves_a_partly_used_item(self):
        from world.medical.treatments import _consume_use
        item = self._item(uses_left=3)
        _consume_use(item)
        self.assertEqual(item._store["uses_left"], 2)
        self.assertFalse(item.deleted)

    def test_an_item_without_uses_left_is_still_the_callers_problem(self):
        """The pin: `_consume_use` documents that items with no
        `uses_left` are left alone, and that must not change."""
        from world.medical.treatments import _consume_use
        item = self._item()
        _consume_use(item)
        self.assertFalse(item.deleted)
        self.assertNotIn("uses_left", item._store)

    def test_a_missing_uses_left_means_one_use_not_zero(self):
        """The medical layer's `can_be_used` defaults to 1 (usable);
        `consume_use` defaulted to 0 (already spent). An item was usable
        on one side of the wall and empty on the other."""
        from world.consumables import consume_use
        item = self._item()
        out = consume_use(item)
        self.assertTrue(out["success"])
        self.assertTrue(out["destroyed"])


class TestTheDeliveryMigrationRunsOnce(TestCase):
    """`supports_delivery`'s docstring promises the implied tags are
    written back "so the migration happens once per item". The early
    return only fired when the QUERIED method was one of the implied
    ones -- which no negative check ever is -- so `eat` on a bandage
    re-added the same tags on every call, forever (#2812)."""

    def _tagged_item(self, medical_type):
        adds = []

        class _Tags:
            def __init__(self):
                self.store = set()

            def has(self, key, category=None):
                return (key, category) in self.store

            def add(self, key, category=None):
                adds.append((key, category))
                self.store.add((key, category))

        class _Attrs:
            def get(self, key, default=None):
                return {"medical_type": medical_type}.get(key, default)

        item = SimpleNamespace(tags=_Tags(), attributes=_Attrs())
        item._adds = adds
        return item

    def test_a_negative_check_does_not_rewrite_the_tags(self):
        from world.consumables import LEGACY_MEDICAL_TYPE_DELIVERIES
        mtype = next(k for k, v in LEGACY_MEDICAL_TYPE_DELIVERIES.items()
                     if v)
        item = self._tagged_item(mtype)
        self.assertFalse(consumables.supports_delivery(item, "nosuchverb"))
        after_first = len(item._adds)
        for _ in range(5):
            consumables.supports_delivery(item, "nosuchverb")
        self.assertEqual(len(item._adds), after_first,
                         "the migration re-ran on every negative check")

    def test_the_migration_still_grants_the_implied_verbs(self):
        from world.consumables import LEGACY_MEDICAL_TYPE_DELIVERIES
        mtype, implied = next((k, v) for k, v
                              in LEGACY_MEDICAL_TYPE_DELIVERIES.items() if v)
        item = self._tagged_item(mtype)
        self.assertTrue(consumables.supports_delivery(item, implied[0]))

    def test_the_implied_verb_still_answers_after_a_negative_check(self):
        """The over-correction to avoid: marking the migration done on a
        negative check must not lock out the verbs it just granted."""
        from world.consumables import LEGACY_MEDICAL_TYPE_DELIVERIES
        mtype, implied = next((k, v) for k, v
                              in LEGACY_MEDICAL_TYPE_DELIVERIES.items() if v)
        item = self._tagged_item(mtype)
        consumables.supports_delivery(item, "nosuchverb")
        self.assertTrue(consumables.supports_delivery(item, implied[0]))
