"""Both proximity repair helpers keep the bidirectional invariant.

Regression pin for #2485. `cleanup_invalid_proximity` and
`sync_proximity_bidirectional` are unreferenced repair helpers for a
known desync-prone seam -- exactly what a maintainer reaches for when it
bites -- and each was wrong about the invariant, in OPPOSITE directions.

* cleanup discarded from the character's own set only, leaving the
  character in the partner's: a repair that creates a new asymmetry.
* sync resolved a one-sided entry by ADDING, treating the character's
  set as authoritative, so a stale cross-room entry was propagated.

Same desync, one removes and one adds. Both now route through
`break_proximity`, the module's working primitive, and sync decides by
VALIDITY rather than by which side it happened to be called from.
"""

from unittest import TestCase

from world.combat.proximity import (
    NDB_PROXIMITY, cleanup_invalid_proximity, establish_proximity,
    sync_proximity_bidirectional,
)


class _Ndb:
    """Evennia's `ndb` returns None for a missing attribute rather than
    raising — `initialize_proximity` relies on that."""

    def __getattr__(self, name):
        return None


class _Char:
    """Hashable by identity: proximity is stored in SETS."""

    def __init__(self, key, room):
        self.key = key
        self.location = room
        self.ndb = _Ndb()

    def __repr__(self):
        return f"<{self.key}>"


def _char(key, room):
    return _Char(key, room)


def _prox(char):
    return getattr(char.ndb, NDB_PROXIMITY, set())


class TestTwoRepairsThatCorruptWhatTheyRepair(TestCase):

    def test_cleanup_removes_from_both_sides(self):
        here, there = object(), object()
        a, b = _char("A", here), _char("B", here)
        establish_proximity(a, b)
        b.location = there                      # walked out
        cleanup_invalid_proximity(a)
        self.assertNotIn(b, _prox(a))
        self.assertNotIn(a, _prox(b), "A was left in B's set — a new asymmetry")

    def test_sync_breaks_a_stale_pair_instead_of_propagating_it(self):
        here, there = object(), object()
        a, b = _char("A", here), _char("B", here)
        establish_proximity(a, b)
        _prox(b).discard(a)                     # one-sided
        b.location = there                      # ...and stale
        sync_proximity_bidirectional(a)
        self.assertNotIn(b, _prox(a))
        self.assertNotIn(a, _prox(b))

    def test_sync_completes_a_genuinely_valid_pair(self):
        """The control — sync must still repair what it should."""
        here = object()
        a, b = _char("A", here), _char("B", here)
        establish_proximity(a, b)
        _prox(b).discard(a)                     # partner dropped us
        sync_proximity_bidirectional(a)
        self.assertIn(a, _prox(b))
        self.assertIn(b, _prox(a))

    def test_cleanup_leaves_a_valid_pair_alone(self):
        here = object()
        a, b = _char("A", here), _char("B", here)
        establish_proximity(a, b)
        cleanup_invalid_proximity(a)
        self.assertIn(b, _prox(a))
        self.assertIn(a, _prox(b))
