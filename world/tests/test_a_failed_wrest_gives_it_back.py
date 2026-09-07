""""A failed snatch does not disarm you (#2489, #2536).

Both issues report the same thing: three call sites mutate the dict
returned by ``character.hands``, which since PR-H2 is a **derived view
rebuilt on every read**, so the mutation is discarded.

**Two of the three were already fixed** by the #2421/#2468 work, and
both carry a comment saying so — `world/combat/actions.py`
(combat `disarm`) and `commands/CmdExplosives.py` (`rig_grenade`). The
write-back was not re-added; it was *removed*, because
``Character.at_object_leave`` releases the slot off the move. One
invariant instead of an obligation on every call site.

**The third site's forward path was fixed by that same invariant**, so
the headline claim — *"wrest does not take"* — is no longer true.
Measured through `_execute_transfer` against the current tree:

```
before:  target held_items = {'left_hand': a knife}
after:   target held_items = {}          <- the hand IS released
         caller held_items = {'left_hand': a knife}
```

**What is still broken is the restore path**, and neither issue names
it. When the contest is won but the wield then fails, the code did:

```python
target_hands[target_hand] = target_object   # throwaway view: no-op
target_object.move_to(target, quiet=True)
```

The move puts the item back in the victim's *inventory*; nothing puts it
back in their *hand*. Measured:

```
after a failed wield:  target held_items = {}
                       knife location     = the target
```

So a wrest that failed still disarmed its victim — quietly, and without
the attacker gaining anything. The invariant that releases a hand on the
way out cannot re-wield on the way back in; that has to be asked for.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.CmdInventory import CmdWrest


class _WrestCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.knife = create_object("typeclasses.items.Item",
                                   key="a knife", location=self.char2)
        self.char2.wield_item(self.knife, "left_hand")
        self.cmd = CmdWrest()

    def transfer(self):
        return self.cmd._execute_transfer(
            self.char1, self.char2, self.knife, "left_hand", "left_hand")

    def held(self, char):
        return dict(char.held_items or {})


class TestTheHandStartsFull(_WrestCase):
    def test_the_target_is_holding_it(self):
        self.assertEqual(self.held(self.char2).get("left_hand"), self.knife)


class TestASuccessfulWrestTakesIt(_WrestCase):
    """Already working, via `at_object_leave` — pinned so the invariant
    cannot quietly regress."""

    def test_it_reports_success(self):
        self.assertTrue(self.transfer())

    def test_the_target_hand_is_released(self):
        self.transfer()
        self.assertIsNone(self.held(self.char2).get("left_hand"))

    def test_the_caller_is_holding_it(self):
        self.transfer()
        self.assertEqual(self.held(self.char1).get("left_hand"), self.knife)

    def test_the_item_moved(self):
        self.transfer()
        self.assertEqual(self.knife.location, self.char1)


class TestAFailedWrestGivesItBack(_WrestCase):
    """The defect neither issue names."""

    def fail_the_wield(self):
        """Patch the INSTANCE, not the class. char1 and char2 share a
        typeclass, so a class-level patch also blocks the target's
        re-wield on the restore path and the test proves nothing."""
        return mock.patch.object(self.char1, "wield_item",
                                 return_value="Your hands are full.")

    def test_it_reports_failure(self):
        with self.fail_the_wield():
            self.assertFalse(self.transfer())

    def test_the_item_returns_to_the_target(self):
        with self.fail_the_wield():
            self.transfer()
        self.assertEqual(self.knife.location, self.char2)

    def test_the_target_is_holding_it_again(self):
        with self.fail_the_wield():
            self.transfer()
        self.assertEqual(self.held(self.char2).get("left_hand"), self.knife,
                         "a failed wrest left the victim disarmed")

    def test_the_caller_gains_nothing(self):
        with self.fail_the_wield():
            self.transfer()
        self.assertNotIn(self.knife, self.held(self.char1).values())


class TestTheOtherTwoSitesStayFixed(EvenniaTest):
    """Pinned against the source. Both were repaired by REMOVING a
    write-back into a derived view, so a well-meaning future reader
    "restoring" it would silently reintroduce the bug."""

    def _source(self, relpath):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / relpath).read_text(errors="ignore")

    def test_combat_disarm_does_not_assign_into_the_view(self):
        body = self._source("world/combat/actions.py")
        self.assertNotIn("hands[weapon_hand] = None", body)

    def test_wrest_does_not_assign_into_the_view(self):
        body = self._source("commands/CmdInventory.py")
        self.assertNotIn("target_hands[target_hand]", body)

    def test_every_hands_mutation_writes_back(self):
        """Any remaining `hands[...] = ...` must be followed by an
        assignment through the setter within a few lines."""
        import pathlib
        import re
        root = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for sub in ("commands", "world", "typeclasses"):
            for path in (root / sub).rglob("*.py"):
                if "/tests/" in str(path):
                    continue
                lines = path.read_text(errors="ignore").splitlines()
                for i, line in enumerate(lines):
                    if not re.search(r"\bhands\[[^\]]+\]\s*=", line):
                        continue
                    window = "\n".join(lines[i:i + 12])
                    if not re.search(r"\.hands\s*=", window):
                        offenders.append(f"{path.name}:{i + 1}")
        self.assertEqual(offenders, [], f"mutations with no write-back: {offenders}")
