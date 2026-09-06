"""The medical tick has to persist what it changed (#2418).

`Character._medical_state` is a plain in-memory instance; persistence
happens only through an explicit `save_medical_state()`. Nothing in
`MedicalScript.at_repeat` called it — so `blood_level`, condition
severities, clot and pain decay, `last_processed`, dressed-organ HP and
`dressing_progress` all lived in memory until some other path happened to
save. In practice the only regular saver was combat damage.

**So a reload healed bleeding.** A character who bled from 100% down to
40% over twenty minutes snapped back to their blood level at the moment
of their last wound. And a wound dressing applied to a patient who then
took no further damage was silently lost on the next reload, with the
bleeding resuming unbraked.

That contradicted the script's own lifecycle docstring — *"SURVIVES
reload… Conditions apply capped elapsed time via `process()`"* — which is
only true if `last_processed` round-trips. `CONDITION_CADENCE_SPEC`
§4.3/§7 is marked SHIPPED and states the contract explicitly.

`apply_wound_care` had the same gap while its siblings `apply_tourniquet`
and `clear_tourniquet` both save.

Cost: the tick is 60s and only runs for characters with active
conditions — the script stops and deletes itself when none remain — so
this is one attribute write per wounded body per minute.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest


class _TickCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.patient = self.char1
        self.patient.location = self.room1

    def run_tick(self, state):
        from evennia import create_script
        from world.medical.script import MedicalScript
        script = create_script(MedicalScript, obj=self.patient,
                               autostart=False)
        with mock.patch.object(type(self.patient), "medical_state",
                               new_callable=mock.PropertyMock,
                               return_value=state):
            script.at_repeat()
        return script

    def stored(self):
        return self.patient.db.medical_state


class TestTheTickWritesItDown(_TickCase):
    def test_a_tick_persists_the_state(self):
        state = mock.MagicMock()
        state.conditions = [mock.MagicMock(requires_ticker=False)]
        state.is_dead.return_value = False
        state.is_unconscious.return_value = False
        state.to_dict.return_value = {"blood_level": 40.0}
        self.run_tick(state)
        self.assertEqual(self.stored(), {"blood_level": 40.0})

    def test_the_blood_level_that_lands_is_the_ticked_one(self):
        """The reported symptom: a reload used to restore the blood
        level from the last WOUND, not the last tick."""
        state = mock.MagicMock()
        state.conditions = [mock.MagicMock(requires_ticker=False)]
        state.is_dead.return_value = False
        state.is_unconscious.return_value = False
        state.to_dict.return_value = {"blood_level": 40.0}
        self.patient.db.medical_state = {"blood_level": 100.0}
        self.run_tick(state)
        self.assertEqual(self.stored()["blood_level"], 40.0)

    def test_the_final_state_survives_the_script_stopping(self):
        """Saved BEFORE the stop check, so a body that finishes healing
        does not lose the tick that finished it."""
        state = mock.MagicMock()
        state.conditions = []
        state.is_dead.return_value = False
        state.is_unconscious.return_value = False
        state.to_dict.return_value = {"blood_level": 97.0}
        with mock.patch("world.medical.script._has_healing_work",
                        return_value=True):
            self.run_tick(state)
        self.assertEqual(self.stored(), {"blood_level": 97.0})


class TestWoundCareIsWrittenDown(EvenniaTest):
    """Its siblings `apply_tourniquet` and `clear_tourniquet` both save;
    it did not, so a dressing was lost on the next reload."""

    def test_it_saves_like_its_siblings(self):
        import inspect
        from world.medical import treatments
        src = inspect.getsource(treatments.apply_wound_care)
        self.assertIn("save_medical_state", src)

    def test_a_real_dressing_is_persisted(self):
        """Drives `apply_wound_care` on a real patient and checks the
        state reached the database, rather than asserting a mock is
        callable -- which is what this test did when first written, and
        proved nothing at all."""
        from world.medical.conditions import BleedingCondition
        from world.medical.treatments import apply_wound_care

        patient = self.char1
        patient.location = self.room1
        state = patient.medical_state
        # A DAMAGED organ at the location, or the treatment no-ops and
        # correctly saves nothing.
        organ = next(o for o in state.organs.values()
                     if o.container == "left_arm")
        organ.current_hp = organ.max_hp - 5
        state.add_condition(BleedingCondition(4, "left_arm"))
        patient.db.medical_state = None

        item = mock.MagicMock()
        item.db.wound_care = 3
        item.db.uses_left = 2
        result = apply_wound_care(self.char2, patient, item, "left_arm")

        self.assertTrue(result.get("stabilized"),
                        f"the dressing did not land: {result}")
        self.assertIsNotNone(
            patient.db.medical_state,
            "the dressing never reached the database, so a reload would "
            "lose it")


class TestTheContractIsWhatTheSpecSays(EvenniaTest):
    def test_last_processed_round_trips(self):
        """The docstring's claim — capped elapsed time across a reload —
        only holds if this field is persisted."""
        from world.medical.core import MedicalState
        from world.medical.conditions import BleedingCondition
        state = MedicalState(character=None)
        cond = BleedingCondition(4, "left_arm")
        cond.last_processed = 1234.5
        state.add_condition(cond)
        restored = MedicalState.from_dict(state.to_dict(), character=None)
        self.assertEqual(restored.conditions[0].last_processed, 1234.5)
