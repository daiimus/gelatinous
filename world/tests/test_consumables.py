"""Tests for the generic consumable decrement helper
(:func:`world.consumables.consume_use`).

The smoke commands and the medical ``use_item`` wrapper both
delegate here.  These tests pin the contract independent of
either consumer.
"""
from __future__ import annotations

from unittest import TestCase

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
