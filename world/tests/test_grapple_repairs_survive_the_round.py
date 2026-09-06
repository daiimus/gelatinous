"""The grapple validator's repairs have to survive the round (#2422).

`at_repeat` snapshots `db.combatants` into plain dicts, works from that
snapshot, and writes it back at the end of the round. The grapple
validator, called mid-round, reads and writes `db.combatants` — a
DIFFERENT list. The snapshot was re-fetched only when
`detect_and_remove_orphaned_combatants` had actually removed someone.

So unless an orphan happened to be removed in the same round, every
repair was reverted and re-detected next round, forever: cleared
self-grapples, cleared cross-room grapples, cleared dead-participant
grapples, repaired one-sided cross-references.

`GRAPPLE_SYSTEM_SPEC` §State Cleanup System marks the validator shipped,
trigger "Every combat round (proactive)". It ran. Its output was
discarded.

The authors knew the shape: `handler.set_target` dual-writes with the
comment *"CRITICAL: Also update active processing list... This prevents
the working copy from reverting the change at end of round."* Only
`set_target` got that treatment.

**Why it partly hid.** `resolve_auto_escape` independently heals the
common "grappled by someone not in combat" case on the local list. But a
YIELDING victim is intercepted first by `_handle_yielding_turn` and never
reaches that heal — leaving them permanently `grappled_by` a phantom and
hard-blocked from `flee`, `retreat`, `advance` and `charge`, all of which
gate on `get_grappled_by_obj`.

These tests assert the invariant rather than the round: whatever the
stored list says after a mid-round edit is what the snapshot must carry.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import DB_CHAR


class _HandlerCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        from evennia import create_script
        from world.combat.handler import CombatHandler
        self.room1.key = "the ring"
        self.handler = create_script(CombatHandler, obj=self.room1,
                                     autostart=False)
        self.a, self.b = self.char1, self.char2
        for c in (self.a, self.b):
            c.location = self.room1
        self.handler.db.combatants = [{DB_CHAR: self.a}, {DB_CHAR: self.b}]

    def snapshot(self):
        return self.handler._refetch_combatants()


class TestTheSnapshotFollowsTheStoredList(_HandlerCase):
    def test_it_reads_what_is_stored_now(self):
        self.assertEqual(len(self.snapshot()), 2)

    def test_a_mid_round_removal_is_picked_up(self):
        self.handler.db.combatants = [{DB_CHAR: self.a}]
        self.assertEqual(len(self.snapshot()), 1)

    def test_a_mid_round_edit_is_picked_up(self):
        """The validator's actual shape: it clears a field in the stored
        list, and the snapshot has to see it."""
        self.handler.db.combatants = [
            {DB_CHAR: self.a, "grappling_dbref": None},
            {DB_CHAR: self.b},
        ]
        entry = next(e for e in self.snapshot() if e[DB_CHAR] == self.a)
        self.assertIsNone(entry.get("grappling_dbref"))

    def test_the_entries_are_plain_dicts(self):
        """`at_repeat` converts away from `_SaverList` deliberately; the
        refresh must not reintroduce it."""
        for entry in self.snapshot():
            self.assertIs(type(entry), dict)

    def test_the_active_list_is_repointed(self):
        """`set_target` writes through `_active_combatants_list` during
        the round; it has to be the list actually in use."""
        fresh = self.snapshot()
        self.assertIs(self.handler._active_combatants_list, fresh)


class TestTheRoundRefreshesAfterTheValidator(_HandlerCase):
    """Ordering is the whole defect: refresh must follow the validator,
    not depend on an orphan being removed in the same round."""

    def test_the_refresh_is_not_gated_on_orphan_removal(self):
        import inspect
        from world.combat.handler import CombatHandler
        src = inspect.getsource(CombatHandler.at_repeat)
        after = src[src.index("validate_and_cleanup_grapple_state"):]
        before_orphans = after[:after.index("detect_and_remove_orphaned")]
        self.assertIn("_refetch_combatants", before_orphans,
                      "the snapshot is not refreshed before the orphan "
                      "sweep, so validator repairs are still discarded")

    def test_a_repair_made_by_the_validator_reaches_the_snapshot(self):
        """Drive the real validator, then refresh, and check the repair
        is in the working list the round will write back."""
        self.a.location = self.room1
        self.b.location = self.room2          # cross-room: not grappleable
        self.handler.db.combatants = [
            {DB_CHAR: self.a, "grappling_dbref": self.b.dbref},
            {DB_CHAR: self.b, "grappled_by_dbref": self.a.dbref},
        ]
        with mock.patch.object(type(self.handler), "msg_contents",
                               create=True):
            self.handler.validate_and_cleanup_grapple_state()
        entry = next(e for e in self.snapshot() if e[DB_CHAR] == self.a)
        self.assertFalse(entry.get("grappling_dbref"),
                         "the cross-room grapple survived into the round's "
                         "working copy")
