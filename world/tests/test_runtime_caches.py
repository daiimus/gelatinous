"""Tests for the ``world.runtime_caches`` helper module.

The runtime-cache pattern moves the four recognition caches
(disguise pierce, forensic, diagnose, autopsy) off the
descriptor-protocol hot path: a plain Python dict on the carrier
holds the working state; ``db.X`` only sees writes at flush
boundaries.  These tests pin the contract.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world import runtime_caches as rc


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


class _DB(SimpleNamespace):
    """Bare attribute holder mimicking ``obj.db``."""


def _make_carrier(**db_values):
    """Build a stub object with a ``.db`` slot for the cache attr."""
    return SimpleNamespace(db=_DB(**db_values))


# ---------------------------------------------------------------------
# Lazy load
# ---------------------------------------------------------------------


class TestLazyLoad(TestCase):
    def test_first_read_initialises_empty_when_db_slot_missing(self):
        carrier = _make_carrier()
        cache = rc.get_runtime_cache(carrier, "my_cache")
        self.assertEqual(cache, {})
        # Runtime attribute is now set on the carrier.
        self.assertTrue(hasattr(carrier, "_runtime_my_cache"))
        # db slot untouched until flush.
        self.assertFalse(hasattr(carrier.db, "my_cache"))

    def test_first_read_copies_from_db_into_runtime(self):
        carrier = _make_carrier(my_cache={"k": "v"})
        cache = rc.get_runtime_cache(carrier, "my_cache")
        self.assertEqual(cache, {"k": "v"})
        # Plain dict on the runtime side, not the original db reference.
        self.assertIsNot(cache, carrier.db.my_cache)

    def test_subsequent_reads_return_same_dict(self):
        carrier = _make_carrier()
        first = rc.get_runtime_cache(carrier, "my_cache")
        first["k"] = "v"
        second = rc.get_runtime_cache(carrier, "my_cache")
        self.assertIs(first, second)
        self.assertEqual(second["k"], "v")

    def test_mutations_do_not_touch_db_until_flush(self):
        carrier = _make_carrier(my_cache={})
        cache = rc.get_runtime_cache(carrier, "my_cache")
        cache["k"] = "v"
        # db slot still empty.
        self.assertEqual(carrier.db.my_cache, {})

    def test_carrier_without_db_returns_empty_dict(self):
        carrier = SimpleNamespace()  # no db
        cache = rc.get_runtime_cache(carrier, "my_cache")
        self.assertEqual(cache, {})


# ---------------------------------------------------------------------
# Flush
# ---------------------------------------------------------------------


class TestFlush(TestCase):
    def test_flush_writes_runtime_dict_to_db(self):
        carrier = _make_carrier(my_cache={})
        cache = rc.get_runtime_cache(carrier, "my_cache")
        cache["k"] = "v"
        rc.flush_runtime_cache(carrier, "my_cache")
        self.assertEqual(carrier.db.my_cache, {"k": "v"})

    def test_flush_without_load_is_noop(self):
        carrier = _make_carrier(my_cache={"original": "value"})
        rc.flush_runtime_cache(carrier, "my_cache")
        # db slot untouched.
        self.assertEqual(carrier.db.my_cache, {"original": "value"})

    def test_flush_carrier_without_db_is_noop(self):
        carrier = SimpleNamespace()
        cache = rc.get_runtime_cache(carrier, "my_cache")
        cache["k"] = "v"
        # Should not raise.
        rc.flush_runtime_cache(carrier, "my_cache")

    def test_flush_writes_plain_dict_copy(self):
        # Flushing should not leave the runtime dict aliased to the
        # db slot — otherwise later mutations would persist
        # silently, defeating the "explicit flush boundary" contract.
        carrier = _make_carrier(my_cache={})
        cache = rc.get_runtime_cache(carrier, "my_cache")
        cache["k"] = "v"
        rc.flush_runtime_cache(carrier, "my_cache")
        cache["k2"] = "v2"
        self.assertNotIn("k2", carrier.db.my_cache)


# ---------------------------------------------------------------------
# Registry / flush_all
# ---------------------------------------------------------------------


class TestRegistry(TestCase):
    def setUp(self):
        # Clear the global registry between tests.
        rc._REGISTRY.clear()

    def tearDown(self):
        rc._REGISTRY.clear()

    def test_lazy_load_auto_registers(self):
        carrier = _make_carrier()
        rc.get_runtime_cache(carrier, "my_cache")
        registered = list(rc.registered_caches())
        self.assertEqual(len(registered), 1)
        self.assertIs(registered[0][0], carrier)
        self.assertEqual(registered[0][1], "my_cache")

    def test_flush_all_flushes_every_registered_entry(self):
        a = _make_carrier(cache_a={})
        b = _make_carrier(cache_b={})
        rc.get_runtime_cache(a, "cache_a")["k_a"] = "v_a"
        rc.get_runtime_cache(b, "cache_b")["k_b"] = "v_b"
        n = rc.flush_all_runtime_caches()
        self.assertEqual(n, 2)
        self.assertEqual(a.db.cache_a, {"k_a": "v_a"})
        self.assertEqual(b.db.cache_b, {"k_b": "v_b"})

    def test_carrier_garbage_collected_drops_from_registry(self):
        # SimpleNamespace doesn't support weakref; build a tiny
        # weakref-friendly carrier class so the registry's lazy
        # prune path can be exercised.  Regular class (not slotted)
        # so setattr for the runtime attribute still works.
        import gc

        class _WeakrefCarrier:
            def __init__(self):
                self.db = _DB()

        carrier = _WeakrefCarrier()
        rc.get_runtime_cache(carrier, "my_cache")
        self.assertEqual(len(list(rc.registered_caches())), 1)
        del carrier
        gc.collect()
        self.assertEqual(len(list(rc.registered_caches())), 0)


# ---------------------------------------------------------------------
# Drop / invalidate
# ---------------------------------------------------------------------


class TestDrop(TestCase):
    def test_drop_clears_runtime_attribute(self):
        carrier = _make_carrier()
        rc.get_runtime_cache(carrier, "my_cache")["k"] = "v"
        rc.drop_runtime_cache(carrier, "my_cache")
        # Next read lazy-loads afresh — but db slot was never written,
        # so we get an empty dict back.
        self.assertEqual(
            rc.get_runtime_cache(carrier, "my_cache"), {},
        )

    def test_drop_does_not_flush(self):
        carrier = _make_carrier(my_cache={})
        rc.get_runtime_cache(carrier, "my_cache")["k"] = "v"
        rc.drop_runtime_cache(carrier, "my_cache")
        # db slot still empty — drop discards, does not persist.
        self.assertEqual(carrier.db.my_cache, {})

    def test_unregister_only_removes_from_registry(self):
        carrier = _make_carrier()
        rc.get_runtime_cache(carrier, "my_cache")["k"] = "v"
        rc.unregister_runtime_cache(carrier, "my_cache")
        # Runtime dict still present.
        self.assertTrue(hasattr(carrier, "_runtime_my_cache"))
        self.assertEqual(
            getattr(carrier, "_runtime_my_cache"), {"k": "v"},
        )


# ---------------------------------------------------------------------
# SaverDict tolerance
# ---------------------------------------------------------------------


class TestSaverDictTolerance(TestCase):
    def test_dict_like_object_loads_cleanly(self):
        # _SaverDict isn't an isinstance of dict but supports .items().
        class _SaverDictLike:
            def __init__(self, data):
                self._data = data

            def items(self):
                return self._data.items()

        carrier = _make_carrier(my_cache=_SaverDictLike({"k": "v"}))
        cache = rc.get_runtime_cache(carrier, "my_cache")
        self.assertEqual(cache, {"k": "v"})
        # Mutation is on the plain runtime dict, not the saver-like.
        cache["k2"] = "v2"
        self.assertNotIn("k2", carrier.db.my_cache._data)
