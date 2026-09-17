"""Orphan sweep respects AIM as a combat relationship (#1002).

The perfect storm: comply/flee reactions drop a target's target_dbref, so the
per-round orphan sweep ejected them (clearing combat + aim-lock) and they
walked out of a fight they were still in. Aim now holds them — but only when
the aim is LIVE (no immortal handlers from stale refs).
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.combat.constants import (
    DB_CHAR, DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF, DB_TARGET_DBREF,
    NDB_AIMED_AT_BY, NDB_AIMING_AT,
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
    for attr in (NDB_AIMING_AT, NDB_AIMED_AT_BY):
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
        # #3568: the sweep now asks whether a target still EXISTS; resolve
        # against the fakes in this handler, so a dbref nobody carries is
        # "gone" the way a deleted character is.
        alive = {getattr(e.get(DB_CHAR), "_dbref", None): e.get(DB_CHAR)
                 for e in (handler.db.combatants or [])}
        orig_by_dbref = cu.get_character_by_dbref
        cu.get_character_by_dbref = lambda d: alive.get(d)
        try:
            cu.detect_and_remove_orphaned_combatants(handler)
        finally:
            cu.remove_combatant = orig_remove
            cu.get_character_dbref = orig_dbref
            cu.get_character_by_dbref = orig_by_dbref
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


class TestAGoneTargetIsNoRelationship(TestOrphanAim):
    """#3568: a recorded dbref whose character no longer exists kept a
    combatant 'locked in combat' with nobody. Presence is not liveness."""

    def test_targeting_a_deleted_character_orphans_you(self):
        a = _char(1)
        with patch.object(cu, "logger") as log:
            removed = self._run(self._handler([_entry(a, target=999)]))
        self.assertIn(a, removed)
        a.msg.assert_called()
        self.assertIn("no longer there", a.msg.call_args[0][0])
        log.log_warn.assert_called()

    def test_the_stale_dbref_is_cleared_on_the_entry(self):
        a = _char(1)
        entry = _entry(a, target=999)
        with patch.object(cu, "logger"):
            self._run(self._handler([entry]))
        self.assertIsNone(entry[DB_TARGET_DBREF])

    def test_leaving_you_are_not_told_to_pick_a_new_target(self):
        # removed in the same tick: "choose a new target" would be
        # unactionable, so the short line only
        a = _char(1)
        with patch.object(cu, "logger"):
            removed = self._run(self._handler([_entry(a, target=999)]))
        self.assertIn(a, removed)
        line = a.msg.call_args[0][0]
        self.assertIn("no longer there", line)
        self.assertNotIn("Choose a new target", line)

    def test_a_queued_action_at_the_dead_target_is_dropped_with_it(self):
        from world.combat.constants import DB_COMBAT_ACTION, DB_COMBAT_ACTION_TARGET
        a, b = _char(1), _char(2)
        ea = _entry(a, target=999)
        ea[DB_COMBAT_ACTION] = "advance"
        ea[DB_COMBAT_ACTION_TARGET] = None      # the deleted object, deserialized
        eb = _entry(b, target=1)
        with patch.object(cu, "logger"):
            self._run(self._handler([ea, eb]))
        self.assertIsNone(ea[DB_COMBAT_ACTION])  # one report, not two
        self.assertEqual(a.msg.call_count, 1)

    def test_but_someone_still_targeting_you_keeps_you_in(self):
        a, b = _char(1), _char(2)
        ea = _entry(a, target=999)          # a's target is gone
        eb = _entry(b, target=1)            # b is still on a
        with patch.object(cu, "logger"):
            removed = self._run(self._handler([ea, eb]))
        self.assertNotIn(a, removed)
        self.assertIsNone(ea[DB_TARGET_DBREF])   # cleared all the same
        line = a.msg.call_args[0][0]
        self.assertIn("no longer there", line)
        self.assertIn("Choose a new target", line)   # staying: actionable

    def test_a_live_target_is_untouched(self):
        a, b = _char(1), _char(2)
        ea, eb = _entry(a, target=2), _entry(b, target=1)
        removed = self._run(self._handler([ea, eb]))
        self.assertEqual(removed, [])
        self.assertEqual(ea[DB_TARGET_DBREF], 2)
        a.msg.assert_not_called()
