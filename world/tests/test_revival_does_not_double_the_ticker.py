"""One MedicalScript per wounded body, revival included (#2461).

`remove_death_state` looked for a STOPPED medical script and created a
fresh one when it found none:

```python
stopped_scripts = [s for s in medical_scripts if not s.is_active]
if stopped_scripts:
    stopped_scripts[0].start()
else:
    script = create_script(MedicalScript, obj=self, autostart=True)
```

Evennia's `Script.stop()` **deletes** the script — this repo's own
`typeclasses/scripts.py` says so — so a stopped medical script can never
be found, and the create path was the only one ever taken.

That would be harmless if nothing else had already restarted the ticker.
Something has: `treatments.py`, `procedures.py` and `medical/utils.py`
all call `start_medical_script` the moment vitals cross back over, and
the death-progression script only notices the revival on its next tick.
So the ordinary revival sequence — medic treats the body, vitals
recover, `DeathProgressionScript` calls `remove_death_state` — left two
persistent MedicalScripts on one patient.

The rates that are elapsed-gated do not double, which is why this reads
as "the messaging is a bit spammy while you recover". What does double:
the consolidated bleeding/pain prose to the player and the room, a
second blood-pool incident every minute, and wound healing, because the
healing clock is per-script `ndb.last_heal_process`.

`start_medical_script` is the guarded door. It returns the running
script instead of making a second one. CONDITION_CADENCE_SPEC §1.4:
*"one MedicalScript per wounded character"*.
"""
from evennia.utils.test_resources import EvenniaTest


class _RevivalCase(EvenniaTest):
    def wound(self):
        """A body with conditions — the branch only runs for one."""
        state = self.char1.medical_state
        self.assertIsNotNone(state)
        self.char1.take_damage(20, location="chest", injury_type="cut")
        self.assertTrue(state.conditions, "fixture: no conditions to tick")
        return state

    def scripts(self):
        return list(self.char1.scripts.get("medical_script"))


class TestRevivalKeepsOneTicker(_RevivalCase):
    def test_a_body_treated_before_revival_ends_with_one_script(self):
        """The real sequence: treatment restarts the ticker, THEN the
        death-progression script calls `remove_death_state`."""
        from world.medical.script import start_medical_script
        self.wound()
        start_medical_script(self.char1)
        self.assertEqual(len(self.scripts()), 1)
        self.char1.remove_death_state()
        self.assertEqual(len(self.scripts()), 1,
                         "revival added a second medical ticker")

    def test_a_body_with_no_script_yet_gets_one(self):
        """The branch still has to DO its job."""
        self.wound()
        for script in self.scripts():
            script.delete()
        self.assertEqual(self.scripts(), [])
        self.char1.remove_death_state()
        self.assertEqual(len(self.scripts()), 1)

    def test_the_surviving_script_is_the_same_object(self):
        from world.medical.script import start_medical_script
        self.wound()
        before = start_medical_script(self.char1)
        self.char1.remove_death_state()
        self.assertEqual(self.scripts()[0].id, before.id)

    def test_reviving_twice_still_leaves_one(self):
        self.wound()
        self.char1.remove_death_state()
        self.char1.remove_death_state()
        self.assertEqual(len(self.scripts()), 1)

    def test_the_script_is_active(self):
        self.wound()
        self.char1.remove_death_state()
        self.assertTrue(self.scripts()[0].is_active)


class TestTheGuardedDoorIsTheOnlyDoor(EvenniaTest):
    def test_revival_no_longer_calls_create_script_directly(self):
        """The defect was a second door onto one decision; pinning the
        door shut is the part a future edit could undo."""
        import inspect

        from typeclasses.characters import Character
        body = inspect.getsource(Character.remove_death_state)
        self.assertNotIn("create_script", body)
        self.assertIn("start_medical_script", body)

    def test_start_medical_script_returns_the_running_one(self):
        from world.medical.script import start_medical_script
        self.char1.take_damage(20, location="chest", injury_type="cut")
        first = start_medical_script(self.char1)
        second = start_medical_script(self.char1)
        self.assertEqual(first.id, second.id)
