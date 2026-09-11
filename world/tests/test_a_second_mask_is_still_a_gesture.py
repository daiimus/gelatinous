"""An essential garment that doesn't move the UID is still a gesture.

Regression pin for #2609.  An unconditional suppression paired with a
conditional emission.

For a `disguise_essential` garment, `wear_item` / `remove_item` skip the
plain action broadcast entirely, on the stated grounds that
`apply_signature_change.__exit__` emits a combined action+reveal line.
It does — **unless the apparent UID did not move**, in which case
`_broadcast_unmask_with_action` returns early and NOTHING is broadcast.
The action and the reveal are one message by design, so dropping the
reveal dropped the action with it.

REACHABILITY, measured rather than assumed.  The apparent UID is built
from the sorted, DEDUPLICATED set of `disguise_type_id`s, so a second
garment of a type already worn does not move it.  Across all 13
essential garments in the catalogue the only shared type_ids are
`balaclava` (balaclava + ski mask) and `wig` (three wigs), and every one
of those pairs ALSO collides on `hair`+`head` coverage — so they can
never be worn together, and a successful wear or remove always moves the
UID.

**So this is unreachable with current content**, and becomes reachable
the moment someone authors two essentials sharing a type_id in
NON-OVERLAPPING slots.  The fixture below is exactly that: a face
garment typed `balaclava`.

The fix lives in the mixin rather than in `on_committed`, because the
command layer branches BEFORE calling `wear_item` and supplies that
callback only on the non-essential path — on this branch it is always
`None`.  Everything the broadcast needs is already a parameter,
including the pre-mutation `pre_resolved_refs` snapshot.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.identity import _broadcast_unmask_with_action


class TestASecondMaskIsStillAGesture(TestCase):

    # -- the engine reports whether it emitted ----------------------

    def _call(self, old_uid, new_uid):
        char = MagicMock()
        char.location = MagicMock()
        return _broadcast_unmask_with_action(
            char, old_uid, new_uid,
            action_template="{actor} puts on a mask.",
            action_char_refs={"actor": char},
            action_pre_resolved_refs={},
            action_exclude=[],
        )

    def test_an_unmoved_uid_reports_no_broadcast(self):
        """The signal the caller needs to know it must emit itself."""
        self.assertIs(self._call("same-uid", "same-uid"), False)

    def test_a_missing_uid_reports_no_broadcast(self):
        for old, new in (("uid", None), (None, "uid"), (None, None)):
            with self.subTest(old=old, new=new):
                self.assertIs(self._call(old, new), False)

    def test_a_moved_uid_reports_a_broadcast(self):
        """The positive control — without it, a function that always
        returned False would pass every test above."""
        with patch("world.identity._collect_unmasking_observers",
                   return_value=[]):
            self.assertIs(self._call("old-uid", "new-uid"), True)

    # -- the context manager surfaces it ----------------------------

    def _broadcast_flag(self, manager):
        """Read `.broadcast` defensively.

        On an unfixed tree the attribute does not exist, and a bare
        access ERRORs — which reads like a broken harness rather than a
        missing feature. Say which it is.
        """
        flag = getattr(manager, "broadcast", "MISSING")
        self.assertIsNot(
            flag, "MISSING",
            "apply_signature_change does not report whether it "
            "broadcast, so a caller cannot know to emit the action "
            "itself",
        )
        return flag


    def test_the_context_manager_exposes_whether_it_broadcast(self):
        from world.identity import apply_signature_change

        char = MagicMock()
        with patch("world.identity.get_apparent_uid", return_value="fixed"), \
             patch("world.identity._broadcast_unmask_with_action",
                   return_value=False) as engine:
            with apply_signature_change(
                char, source="wear_item",
                action_template="{actor} puts on a mask.",
                action_char_refs={"actor": char},
                action_pre_resolved_refs={},
                action_exclude=[],
            ) as signature_change:
                pass
            engine.assert_called_once()
        self.assertIs(self._broadcast_flag(signature_change), False)

    def test_a_failed_mutation_never_reports_a_broadcast(self):
        """An exception inside the block must not look like a success,
        or the caller would emit an action that never happened."""
        from world.identity import apply_signature_change

        char = MagicMock()
        with patch("world.identity.get_apparent_uid", return_value="x"):
            manager = apply_signature_change(
                char, source="wear_item",
                action_template="{actor} puts on a mask.",
                action_char_refs={"actor": char},
                action_pre_resolved_refs={}, action_exclude=[],
            )
            with self.assertRaises(RuntimeError):
                with manager:
                    raise RuntimeError("mutation failed")
        self.assertIs(self._broadcast_flag(manager), False)

    # -- the mixin falls back ---------------------------------------

    def test_the_mixin_emits_when_the_signature_did_not(self):
        from typeclasses.clothing_mixin import ClothingMixin
        import inspect

        src = inspect.getsource(ClothingMixin.wear_item)
        self.assertIn("signature_change.broadcast", src)
        # Emitted directly, NOT via on_committed — which the command
        # layer does not pass on this branch.
        self.assertIn("msg_room_identity", src)

    def test_both_doors_fall_back(self):
        """wear and remove are mirrored; neither may be left behind."""
        from typeclasses.clothing_mixin import ClothingMixin
        import inspect

        for method in (ClothingMixin.wear_item, ClothingMixin.remove_item):
            with self.subTest(method.__name__):
                self.assertIn(
                    "signature_change.broadcast",
                    inspect.getsource(method),
                )
