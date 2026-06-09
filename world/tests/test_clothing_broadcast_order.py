"""Regression tests for the wear/remove broadcast order — action
emote must land before any identity-shift recognition messages.

Before this fix, ``CmdRemove`` (and ``CmdWear``) called the
underlying ``remove_item`` / ``wear_item`` method, which wraps the
mutation in :class:`apply_signature_change`.  ``apply_signature_change``
fires ``_broadcast_unmasking`` on its ``__exit__`` — the "you
realize X and Y are the same person" message — *before* the
command had a chance to emit the action emote ("X removes a
balaclava").  Observer prose came out backwards.

The fix: ``wear_item`` and ``remove_item`` accept an
``on_committed`` callback that fires after validation passes but
before the mutation runs (and therefore before
``apply_signature_change``).  Commands pass the action broadcast
as ``on_committed``, restoring the natural ordering.

These tests verify the callback fires in the right position via
clothing-mixin behaviour with fakes — no Evennia DB.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from typeclasses.clothing_mixin import ClothingMixin


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _FakeItem:
    """Minimum surface ClothingMixin's wear/remove need."""

    def __init__(self, *, key="balaclava", layer=2, coverage=("head",),
                 essential=False):
        self.key = key
        self.layer = layer
        self.location = None  # set to actor by tests that exercise wear
        self._coverage = list(coverage)
        self.disguise_essential = essential

    def is_wearable(self):
        return True

    def get_current_coverage(self):
        return list(self._coverage)


class _Actor(ClothingMixin):
    """Stand-in for a Character — only the surface ClothingMixin
    needs.  No Evennia base class involvement."""

    def __init__(self):
        self.worn_items = {}
        self.hands = {"left": None, "right": None}
        self.events: list[str] = []


# ---------------------------------------------------------------------
# Wear order
# ---------------------------------------------------------------------


class TestWearItemOrder(TestCase):
    def test_on_committed_fires_before_mutation(self):
        actor = _Actor()
        item = _FakeItem()
        item.location = actor

        def _hook():
            # At the moment the hook fires, the item must not yet be
            # in worn_items — the mutation runs after on_committed.
            self.assertNotIn("head", actor.worn_items)
            actor.events.append("emote")

        success, _msg = actor.wear_item(item, on_committed=_hook)
        self.assertTrue(success)
        self.assertEqual(actor.events, ["emote"])
        # Mutation completed afterwards.
        self.assertIn("head", actor.worn_items)
        self.assertIn(item, actor.worn_items["head"])

    def test_on_committed_fires_before_signature_change(self):
        """For essential items the broadcast happens inside
        ``apply_signature_change.__exit__``.  ``on_committed`` must
        fire before we even enter that context."""
        actor = _Actor()
        item = _FakeItem(essential=True)
        item.location = actor

        events = []

        def _hook():
            events.append("emote")

        # Stub apply_signature_change so we can assert ordering
        # without pulling in the real broadcast pipeline.
        class _StubCtx:
            def __init__(self, *args, **kwargs):
                events.append("enter_sigchange")

            def __enter__(self):
                return self

            def __exit__(self, *_):
                events.append("exit_sigchange")
                return False

        with patch(
            "world.identity.apply_signature_change", _StubCtx,
        ):
            actor.wear_item(item, on_committed=_hook)

        self.assertEqual(
            events, ["emote", "enter_sigchange", "exit_sigchange"],
        )

    def test_on_committed_skipped_on_validation_failure(self):
        actor = _Actor()
        # Pre-fill the location with a same-layer item — wear should fail.
        blocking = _FakeItem(key="hat", layer=2)
        actor.worn_items["head"] = [blocking]
        new_item = _FakeItem()
        new_item.location = actor

        fired = []
        success, _msg = actor.wear_item(
            new_item, on_committed=lambda: fired.append(True),
        )
        self.assertFalse(success)
        self.assertEqual(fired, [])


# ---------------------------------------------------------------------
# Remove order
# ---------------------------------------------------------------------


class TestRemoveItemOrder(TestCase):
    def test_on_committed_fires_before_mutation(self):
        actor = _Actor()
        item = _FakeItem()
        actor.worn_items["head"] = [item]

        def _hook():
            # Item still worn at hook time — mutation runs after.
            self.assertIn(item, actor.worn_items.get("head", []))
            actor.events.append("emote")

        success, _msg = actor.remove_item(item, on_committed=_hook)
        self.assertTrue(success)
        self.assertEqual(actor.events, ["emote"])
        # Worn dict cleaned up after.
        self.assertNotIn("head", actor.worn_items)

    def test_on_committed_fires_before_signature_change(self):
        actor = _Actor()
        item = _FakeItem(essential=True)
        actor.worn_items["head"] = [item]

        events = []

        def _hook():
            events.append("emote")

        class _StubCtx:
            def __init__(self, *args, **kwargs):
                events.append("enter_sigchange")

            def __enter__(self):
                return self

            def __exit__(self, *_):
                events.append("exit_sigchange")
                return False

        with patch(
            "world.identity.apply_signature_change", _StubCtx,
        ):
            actor.remove_item(item, on_committed=_hook)

        self.assertEqual(
            events, ["emote", "enter_sigchange", "exit_sigchange"],
        )

    def test_on_committed_skipped_on_not_worn(self):
        actor = _Actor()
        item = _FakeItem()
        # NOT in worn_items — remove should fail validation.

        fired = []
        success, _msg = actor.remove_item(
            item, on_committed=lambda: fired.append(True),
        )
        self.assertFalse(success)
        self.assertEqual(fired, [])

    def test_on_committed_skipped_on_outer_layer_blocking(self):
        actor = _Actor()
        inner = _FakeItem(key="undershirt", layer=1, coverage=("chest",))
        outer = _FakeItem(key="jacket", layer=3, coverage=("chest",))
        actor.worn_items["chest"] = [outer, inner]

        fired = []
        success, _msg = actor.remove_item(
            inner, on_committed=lambda: fired.append(True),
        )
        self.assertFalse(success)
        self.assertEqual(fired, [])
