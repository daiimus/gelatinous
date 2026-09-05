"""An item leaving a body gives up its slots — as an invariant (#2468).

`held_items` and `worn_items` are the backing stores behind `hands` and
the clothing view, and they were maintained ONLY by explicit code at each
call site. `Character` defined neither `at_object_leave` nor
`at_object_delete`. Rooms, corpses and cigarette packs all hooked object
departure; the one type with a hand-slot ledger to keep did not.

So every removal path carried an obligation, and several dropped it:

    resolve_disarm / rig_grenade   mutate a throwaway view      #2421
    LockerBank.stash               moves out of caller.contents #2457
    anything self-deleting held    leaves a dead row            #2467

A packed-structure sweep found 68 dead `held_items` references live. They
were harmless only because `deserialize` renders a dead reference as
``None``, so the slot reads as a free hand — silent, unbounded drift in
the production database.

These tests pin the invariant at the three doors it has to hold at: an
ordinary move, a delete, and the `move_hooks=False` path that skips the
hook entirely and therefore has to release by hand.
"""
from evennia.utils.test_resources import EvenniaTest


class _LedgerCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.item = self.obj1
        self.item.location = self.char
        self.char.held_items = {"right_hand": self.item}

    def held(self):
        return dict(self.char.held_items or {})


class TestAnOrdinaryMoveReleasesTheHand(_LedgerCase):
    def test_moving_the_item_away_frees_the_slot(self):
        self.item.move_to(self.room1, quiet=True)
        self.assertNotIn("right_hand", self.held())

    def test_the_derived_hands_view_agrees(self):
        """`hands` is what every consumer actually reads."""
        self.item.move_to(self.room1, quiet=True)
        self.assertIsNone(self.char.hands.get("right_hand"))

    def test_another_body_taking_it_frees_the_first(self):
        self.item.move_to(self.char2, quiet=True)
        self.assertNotIn("right_hand", self.held())


class TestDeletingAHeldItemReleasesTheHand(_LedgerCase):
    def test_self_deletion_does_not_leave_a_dead_row(self):
        """The #2467 mechanism: a cigarette pack deletes itself when the
        last cigarette is drawn, while someone is holding it."""
        self.item.delete()
        self.assertNotIn("right_hand", self.held())

    def test_the_delete_still_happens(self):
        """A ledger repair must never be what stops a delete."""
        self.assertTrue(self.item.delete())


class TestTheMoveHooksFalsePath(_LedgerCase):
    """`move_hooks=False` suppresses `at_object_leave`, so any site using
    it to stay quiet has to release the slot itself. This is the trap
    that makes the hook alone insufficient."""

    def test_a_quiet_move_still_bypasses_the_hook(self):
        """Pinning the hazard itself, so it stays visible: if Evennia
        ever starts firing hooks on a quiet move, this test says so."""
        self.item.move_to(self.room1, quiet=True, move_hooks=False)
        self.assertIn("right_hand", self.held())

    def test_release_slots_is_what_those_sites_must_call(self):
        self.item.move_to(self.room1, quiet=True, move_hooks=False)
        self.char.release_slots(self.item)
        self.assertNotIn("right_hand", self.held())


class TestWornItemsAreReleasedToo(_LedgerCase):
    def setUp(self):
        super().setUp()
        self.garment = self.obj2
        self.garment.location = self.char
        self.char.worn_items = {"chest": [self.garment]}

    def test_a_garment_leaving_the_body_leaves_the_ledger(self):
        self.garment.move_to(self.room1, quiet=True)
        self.assertNotIn("chest", dict(self.char.worn_items or {}))

    def test_other_layers_at_the_location_survive(self):
        self.char.worn_items = {"chest": [self.garment, self.item]}
        self.garment.move_to(self.room1, quiet=True)
        self.assertEqual(dict(self.char.worn_items or {})["chest"],
                         [self.item])


class TestHistoricalDriftHealsOnTouch(_LedgerCase):
    def test_an_empty_slot_is_pruned_when_anything_is_released(self):
        """The 68 dead references read as ``None`` after deserialize.
        Repairing them on the next release means no migration script."""
        self.char.held_items = {"right_hand": self.item, "left_hand": None}
        self.item.move_to(self.room1, quiet=True)
        self.assertEqual(self.held(), {})

    def test_a_live_slot_is_not_disturbed(self):
        self.char.held_items = {"right_hand": self.item, "left_hand": self.obj2}
        self.item.move_to(self.room1, quiet=True)
        self.assertEqual(self.held(), {"left_hand": self.obj2})


class TestReleaseIsSafeToCallAnyTime(_LedgerCase):
    def test_an_object_never_held_changes_nothing(self):
        self.char.release_slots(self.obj2)
        self.assertEqual(self.held(), {"right_hand": self.item})

    def test_it_is_idempotent(self):
        self.char.release_slots(self.item)
        self.char.release_slots(self.item)
        self.assertEqual(self.held(), {})

    def test_a_body_holding_nothing_is_fine(self):
        self.char.held_items = {}
        self.char.release_slots(self.item)
        self.assertEqual(self.held(), {})
