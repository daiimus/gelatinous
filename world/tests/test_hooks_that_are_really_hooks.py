"""Two handlers named for methods that do not exist (#2590, #2592).

## #2590 — `at_delete` is not an Evennia hook

`DefaultObject.delete` calls **`at_object_delete()`**:

```python
if not self.pk or not self.at_object_delete():
    # object already deleted or deletion vetoed
    return False
```

`at_delete` appears nowhere in Evennia. Two cleanup handlers in
`typeclasses/items.py` were named for it, so **neither has ever run** —
and two detonators in the live game hold references to explosives that
no longer exist.

The return value matters: a False return **vetoes the deletion**, so the
handlers now return `super().at_object_delete()` rather than calling it
bare. That also chains into `ObjectParent.at_object_delete`, which
releases equipment slots (#2467) — the one place in this codebase that
already had the name right.

## #2592 — no Evennia Script has `restart`

`DefaultScript` exposes `start` / `stop` / `pause` / `unpause`.
`at_start` called `self.restart(interval=...)`, so the #501 Phase 2
guarantee — *"persisted scripts never trust persisted config"* — was a
guaranteed `AttributeError` the first time it was needed.

`start(interval=...)` is documented as *"Start/Unpause timer component,
optionally with new values"*, which is exactly the intent. Safe to call
from inside `at_start`: `_start_task` manages the twisted task and does
not re-invoke `at_start`, so there is no recursion.

**#2592 named only the death-progression copy. There is a sibling** in
`world/medical/script.py` — the tick that runs bleeding — with the same
call. Both are fixed.

**What this does NOT explain.** I checked whether the medical sibling
was the cause of #2938's stale, active-but-unscheduled scripts. It is
not: all eight live `medical_script` rows already carry
`interval == MEDICAL_TICK_INTERVAL`, so the branch containing the bad
call never fires for them. #2938 stays open on its own evidence.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestTheDeleteHookHasTheRightName(EvenniaTest):
    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "typeclasses" / "items.py").read_text(errors="ignore")

    def test_no_handler_is_named_at_delete(self):
        self.assertNotIn("def at_delete(self)", self._source())

    def test_both_are_named_at_object_delete(self):
        self.assertEqual(self._source().count("def at_object_delete(self)"), 2)

    def test_neither_calls_the_nonexistent_super(self):
        self.assertNotIn("super().at_delete()", self._source())

    def test_evennia_calls_at_object_delete(self):
        """Read off the installed Evennia, so a rename upstream fails
        loudly rather than silently disarming these again."""
        import inspect

        from evennia.objects.objects import DefaultObject
        src = inspect.getsource(DefaultObject.delete)
        self.assertIn("at_object_delete()", src)
        self.assertNotIn("at_delete()", src)

    def test_evennia_has_no_at_delete_at_all(self):
        from evennia.objects.objects import DefaultObject
        self.assertFalse(hasattr(DefaultObject, "at_delete"))


class TestTheCleanupActuallyRuns(EvenniaTest):
    """The behaviour the dead hook was written for."""

    def _pair(self):
        detonator = create_object("typeclasses.items.RemoteDetonator",
                                  key="a detonator", location=self.room1)
        charge = create_object("typeclasses.items.Item", key="a charge",
                               location=self.room1)
        charge.db.scanned_by_detonator = detonator.id
        detonator.db.scanned_explosives = [charge.id]
        return detonator, charge

    def test_deleting_the_explosive_clears_the_detonator(self):
        detonator, charge = self._pair()
        charge_id = charge.id          # `.id` is None AFTER deletion, so
        charge.delete()                # reading it later makes the
        self.assertNotIn(charge_id,    # assertion vacuously true — it
                         detonator.db.scanned_explosives or [])  # passed
        # unfixed until this was captured up front.

    def test_deleting_the_detonator_clears_the_explosive(self):
        detonator, charge = self._pair()
        detonator.delete()
        self.assertIsNone(charge.db.scanned_by_detonator)

    def test_the_delete_still_happens(self):
        """A handler returning False would VETO the deletion — the
        reason the super() return is passed through."""
        _detonator, charge = self._pair()
        charge.delete()
        self.assertFalse(charge.pk)


class TestTheScriptUsesARealMethod(EvenniaTest):
    def test_no_script_has_restart(self):
        from evennia.scripts.scripts import DefaultScript
        self.assertFalse(hasattr(DefaultScript, "restart"))

    def test_start_takes_an_interval(self):
        import inspect

        from evennia.scripts.scripts import DefaultScript
        self.assertIn("interval",
                      inspect.signature(DefaultScript.start).parameters)

    def test_neither_script_calls_restart(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        for relpath in ("typeclasses/death_progression.py",
                        "world/medical/script.py"):
            body = (root / relpath).read_text(errors="ignore")
            self.assertNotIn("self.restart(", body, f"{relpath}")

    def test_the_sweep_is_clean_repo_wide(self):
        """#2592 named one site; there were two."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for sub in ("commands", "world", "typeclasses"):
            for path in (root / sub).rglob("*.py"):
                if "/tests/" in str(path):
                    continue
                if "self.restart(" in path.read_text(errors="ignore"):
                    offenders.append(path.name)
        self.assertEqual(offenders, [])


class TestReAssertingTheIntervalWorks(EvenniaTest):
    """The #501 Phase 2 guarantee, exercised rather than described."""

    def test_a_stale_interval_is_corrected_on_start(self):
        from evennia import create_script

        from world.medical.constants import MEDICAL_TICK_INTERVAL
        from world.medical.script import MedicalScript
        script = create_script(MedicalScript, obj=self.char1,
                               autostart=False)
        script.interval = MEDICAL_TICK_INTERVAL + 7
        script.at_start()
        self.assertEqual(script.interval, MEDICAL_TICK_INTERVAL)

    def test_a_correct_interval_is_left_alone(self):
        from evennia import create_script

        from world.medical.constants import MEDICAL_TICK_INTERVAL
        from world.medical.script import MedicalScript
        script = create_script(MedicalScript, obj=self.char1,
                               autostart=False)
        script.interval = MEDICAL_TICK_INTERVAL
        script.at_start()
        self.assertEqual(script.interval, MEDICAL_TICK_INTERVAL)

    def test_at_start_terminates(self):
        """`start()` from inside `at_start` DOES re-enter the hook —
        `_start_task` calls it at `scripts.py:254`. My first version of
        this comment claimed it did not, and this test is what caught
        that. It terminates because the second pass finds the interval
        already correct and does not call `start()` again: two calls,
        not two thousand.
        """
        from unittest import mock

        from evennia import create_script

        from world.medical.constants import MEDICAL_TICK_INTERVAL
        from world.medical.script import MedicalScript
        script = create_script(MedicalScript, obj=self.char1,
                               autostart=False)
        script.interval = MEDICAL_TICK_INTERVAL + 7
        calls = []
        real = type(script).at_start

        def counting(self_):
            calls.append(1)
            if len(calls) > 10:
                raise AssertionError("at_start recursed without bound")
            return real(self_)

        with mock.patch.object(type(script), "at_start", counting):
            script.at_start()
        self.assertEqual(len(calls), 2, "expected exactly one re-entry")
