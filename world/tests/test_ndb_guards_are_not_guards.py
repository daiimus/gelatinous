"""`hasattr(obj.ndb, anything)` is always True (#2487).

Evennia's `obj.ndb` returns a `DbHolder`, whose `__getattribute__`
returns the handler's `get()` rather than raising — and `get()` returns
`None` for a missing key. `hasattr` reports True whenever `getattr`
doesn't raise, so it reports True for **every possible name**.

Verified by execution rather than by reading:

```
hasattr(ndb, "probe_xyz_none")   True
getattr(ndb, "probe_xyz_none")   None
hasattr(ndb, in_proximity_with)  True
value of in_proximity_with       None
delattr(ndb, missing key)        no raise
```

The codebase has 77 of these guards. **Most are harmless** and this is
not 77 bugs: `delattr` on a missing key is a verified no-op, so the very
common `if hasattr(...): delattr(...)` shape is safe, and most proximity
readers follow the `hasattr` with an `isinstance(..., set)` or a
truthiness test that does the work the `hasattr` was standing in for.

**Two sites had no second check**, and both raise:

```
grappling.py  resolve_grapple_join    TypeError: argument of type 'NoneType' is not iterable
utils.py      remove_combatant        TypeError: argument of type 'NoneType' is not iterable
```

The grapple site is the clearer illustration: its
initialize-if-missing branch could never run, because the condition is
always False — so the set it was meant to create never existed, and the
next line indexed `None`.

**Why it is reachable.** Both need `in_proximity_with` to be `None`
rather than an empty set. `add_combatant` initialises it for anyone
joining a fight, so in normal play it is a set — but all ndb dies on
reload, and the re-link sweep in `at_server_startstop` only restores
proximity for *mutually engaged pairs*. Any combatant in the handler who
is not mutually engaged with anyone keeps `None`: the yielding
combatant, the target-less one, the one held in the fight by aim. The
`remove_combatant` site is the worse of the two by position — it runs
inside the round tick, from `_remove_incapacitated` in `at_repeat`.

Both now route through `is_in_proximity`, which was already in
`proximity.py` doing the isinstance check correctly. No new helper: the
right door existed, these two sites just weren't using it.

The dead `hasattr` was also removed from `get_proximity_list` and
`is_in_proximity` themselves. It gated nothing there — the isinstance
check below it did all the work — but leaving it in the two canonical
helpers is what teaches the pattern to the next reader.
"""
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import NDB_PROXIMITY
from world.combat.proximity import (establish_proximity, get_proximity_list,
                                    is_in_proximity)


class TestTheGuardGuardsNothing(EvenniaTest):
    """Pinned against the installed Evennia, so an upgrade that changes
    `DbHolder` fails here rather than silently making 77 guards real."""

    def test_hasattr_is_true_for_a_name_that_was_never_set(self):
        self.assertTrue(hasattr(self.char1.ndb, "probe_xyz_never_set"))

    def test_and_the_value_is_none(self):
        self.assertIsNone(getattr(self.char1.ndb, "probe_xyz_never_set"))

    def test_delattr_on_a_missing_key_does_not_raise(self):
        """Why most of the 77 sites are harmless."""
        delattr(self.char1.ndb, "probe_xyz_never_set")

    def test_indexing_the_none_is_what_raises(self):
        with self.assertRaises(TypeError):
            self.char2 in getattr(self.char1.ndb, NDB_PROXIMITY)


class _ProximityCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        for c in (self.char1, self.char2):
            c.location = self.room1
        # the post-reload state: in the handler, never paired, so the
        # sweep never built the set
        setattr(self.char1.ndb, NDB_PROXIMITY, None)
        setattr(self.char2.ndb, NDB_PROXIMITY, None)


class TestTheHelpersSurviveAnUnbuiltSet(_ProximityCase):
    def test_is_in_proximity_is_false_not_a_crash(self):
        self.assertFalse(is_in_proximity(self.char1, self.char2))

    def test_get_proximity_list_is_empty_not_a_crash(self):
        self.assertEqual(get_proximity_list(self.char1), [])

    def test_a_character_is_never_in_proximity_with_itself(self):
        establish_proximity(self.char1, self.char2)
        self.assertFalse(is_in_proximity(self.char1, self.char1))


class TestTheHelpersStillWork(_ProximityCase):
    """The fix must not make everything simply answer "no"."""

    def test_established_proximity_reads_true(self):
        establish_proximity(self.char1, self.char2)
        self.assertTrue(is_in_proximity(self.char1, self.char2))

    def test_it_is_mutual(self):
        establish_proximity(self.char1, self.char2)
        self.assertTrue(is_in_proximity(self.char2, self.char1))

    def test_the_list_reports_the_partner(self):
        establish_proximity(self.char1, self.char2)
        self.assertIn(self.char2, get_proximity_list(self.char1))


class TestGrappleJoinDoesNotCrash(_ProximityCase):
    """`resolve_grapple_join` should refuse for want of proximity — it
    must not raise on the way to refusing.

    Driven with real combat entries and a stub handler rather than a
    mock of the function under test, so it walks the same four early
    returns a live call does before reaching the proximity check.
    """

    def _entries(self):
        from unittest import mock

        from world.combat.constants import (DB_CHAR, DB_GRAPPLED_BY_DBREF,
                                            DB_GRAPPLING_DBREF)
        joiner = {DB_CHAR: self.char1}
        victim = {DB_CHAR: self.char2,
                  DB_GRAPPLED_BY_DBREF: self.obj1.dbref}
        holder = {DB_CHAR: self.obj1, DB_GRAPPLING_DBREF: self.char2.dbref}
        handler = mock.MagicMock()
        handler.get_target_obj.return_value = self.char2
        handler.get_grappled_by_obj.return_value = self.obj1
        return joiner, [joiner, victim, holder], handler

    def test_the_refusal_path_is_reachable(self):
        from world.combat import grappling
        said = []
        self.char1.msg = lambda *a, **k: said.append(str(a[0] if a else ""))
        entry, combatants, handler = self._entries()
        grappling.resolve_grapple_join(entry, combatants, handler)
        self.assertTrue(said, "the join said nothing at all")

    def test_it_says_why_it_refused(self):
        from world.combat import grappling
        said = []
        self.char1.msg = lambda *a, **k: said.append(str(a[0] if a else ""))
        entry, combatants, handler = self._entries()
        grappling.resolve_grapple_join(entry, combatants, handler)
        self.assertTrue(any("proximity" in s for s in said),
                        f"expected a proximity refusal, got {said}")


class TestTheSourceKeepsTheRightDoor(EvenniaTest):
    """Both sites were repaired by DELETING a guard that looked load
    bearing, so a future reader restoring it would bring the crash
    back."""

    def _source(self, relpath):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / relpath).read_text(errors="ignore")

    def test_grappling_no_longer_indexes_the_raw_attribute(self):
        body = self._source("world/combat/grappling.py")
        self.assertNotIn("if target not in getattr(char.ndb", body)

    def test_utils_no_longer_indexes_in_proximity_with_directly(self):
        body = self._source("world/combat/utils.py")
        self.assertNotIn("in other_char.ndb.in_proximity_with", body)

    def test_the_proximity_module_carries_no_dead_ndb_guard(self):
        """Every one of them in this file was followed by the
        `isinstance` that did the real work, so removing them changes
        no behaviour — it stops the file teaching the pattern."""
        import re
        body = self._source("world/combat/proximity.py")
        live = [ln for ln in body.splitlines()
                if re.search(r"hasattr\([^)]*\.ndb", ln)
                and not ln.strip().startswith("#")]
        self.assertEqual(live, [])
