"""Orphan sweep respects AIM as a combat relationship (#1002).

The perfect storm: comply/flee reactions drop a target's target_dbref, so the
per-round orphan sweep ejected them (clearing combat + aim-lock) and they
walked out of a fight they were still in. Aim now holds them — but only when
the aim is LIVE (no immortal handlers from stale refs).
"""

from unittest import TestCase
from unittest.mock import MagicMock

from world.combat.constants import (
    DB_CHAR, DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF, DB_TARGET_DBREF,
    NDB_AIMED_AT_BY, NDB_AIMING_AT, NDB_PROXIMITY,
)
import world.combat.utils as cu


def _entry(char, target=None):
    return {DB_CHAR: char, DB_TARGET_DBREF: target,
            DB_GRAPPLING_DBREF: None, DB_GRAPPLED_BY_DBREF: None}


def _char(dbref):
    c = MagicMock()
    c.key = f"char{dbref}"
    c._dbref = dbref
    # bare ndb: nothing aiming by default
    for attr in (NDB_AIMING_AT, NDB_AIMED_AT_BY, NDB_PROXIMITY):
        setattr(c.ndb, attr, None)
    c.location = "room"
    return c


class TestOrphanAim(TestCase):
    def _run(self, handler):
        """Call the real detector with dbref plumbing patched to our fakes."""
        removed = []
        orig_remove = cu.remove_combatant
        cu.remove_combatant = lambda h, ch: removed.append(ch)
        orig_dbref = cu.get_character_dbref
        cu.get_character_dbref = lambda ch: getattr(ch, "_dbref", None)
        try:
            cu.detect_and_remove_orphaned_combatants(handler)
        finally:
            cu.remove_combatant = orig_remove
            cu.get_character_dbref = orig_dbref
        return removed

    def _handler(self, entries):
        h = MagicMock()
        h.db.combatants = entries
        return h

    def test_yielding_no_target_is_orphaned_without_aim(self):
        # baseline: the storm as-was — a complied NPC (no target, not
        # targeted, no aim) is swept.
        a = _char(1)
        removed = self._run(self._handler([_entry(a, target=None)]))
        self.assertIn(a, removed)

    def test_aimed_at_target_is_held(self):
        # aggressor A aims at B; B yields (no target). B must NOT be swept.
        a, b = _char(1), _char(2)
        setattr(a.ndb, NDB_AIMING_AT, b)
        setattr(b.ndb, NDB_AIMED_AT_BY, a)
        entries = [_entry(a, target=None), _entry(b, target=None)]
        removed = self._run(self._handler(entries))
        self.assertNotIn(b, removed)      # held at gunpoint
        self.assertNotIn(a, removed)      # aiming = engaged

    def test_stale_aimed_at_is_still_orphaned(self):
        # B thinks it's aimed at by A, but A is gone (not reciprocally
        # aiming) — must NOT become immortal.
        a, b = _char(1), _char(2)
        setattr(b.ndb, NDB_AIMED_AT_BY, a)   # stale: A doesn't aim back
        setattr(a.ndb, NDB_AIMING_AT, None)
        removed = self._run(self._handler([_entry(b, target=None)]))
        self.assertIn(b, removed)

    def test_aimer_in_other_room_does_not_hold(self):
        a, b = _char(1), _char(2)
        a.location = "elsewhere"
        setattr(a.ndb, NDB_AIMING_AT, b)
        setattr(b.ndb, NDB_AIMED_AT_BY, a)
        removed = self._run(self._handler([_entry(b, target=None)]))
        self.assertIn(b, removed)          # aimer not present -> not live

    def test_targeted_combatant_still_safe(self):
        # regression: normal targeting still prevents orphaning.
        a, b = _char(1), _char(2)
        entries = [_entry(a, target=2), _entry(b, target=None)]
        removed = self._run(self._handler(entries))
        self.assertNotIn(b, removed)       # b is targeted by a


class TestOrphanProximity(TestCase):
    """Melee proximity is a combat relationship (only combat establishes it),
    so a yielder held at melee range must not be swept — the close-quarters
    twin of the aim hold."""

    def _run(self, handler):
        removed = []
        orig_remove = cu.remove_combatant
        cu.remove_combatant = lambda h, ch: removed.append(ch)
        orig_dbref = cu.get_character_dbref
        cu.get_character_dbref = lambda ch: getattr(ch, "_dbref", None)
        try:
            cu.detect_and_remove_orphaned_combatants(handler)
        finally:
            cu.remove_combatant = orig_remove
            cu.get_character_dbref = orig_dbref
        return removed

    def _handler(self, entries):
        h = MagicMock(); h.db.combatants = entries
        return h

    def test_in_melee_proximity_is_held(self):
        a, b = _char(1), _char(2)
        setattr(a.ndb, NDB_PROXIMITY, {b})
        setattr(b.ndb, NDB_PROXIMITY, {a})
        entries = [_entry(a, target=None), _entry(b, target=None)]
        removed = self._run(self._handler(entries))
        self.assertNotIn(b, removed)
        self.assertNotIn(a, removed)

    def test_stale_proximity_partner_gone_is_orphaned(self):
        a, b = _char(1), _char(2)
        b.location = "elsewhere"          # partner not present
        setattr(a.ndb, NDB_PROXIMITY, {b})
        removed = self._run(self._handler([_entry(a, target=None)]))
        self.assertIn(a, removed)

    def test_empty_proximity_set_is_orphaned(self):
        a = _char(1)
        setattr(a.ndb, NDB_PROXIMITY, set())
        removed = self._run(self._handler([_entry(a, target=None)]))
        self.assertIn(a, removed)
