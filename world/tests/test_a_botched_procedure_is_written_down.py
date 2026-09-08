"""A botched procedure's consequences tick, and survive (#2506, #2508).

## #2506 — the seeds went through the list, not the door

`seed_infection` and `seed_pain` deliver every botched-procedure
consequence in the surgical system, and both appended straight to
`state.conditions`:

```python
state.conditions.append(InfectionCondition(severity, location))
```

`MedicalState.add_condition` is the door, and does four more things —
all of which mattered here:

* the archived-character guard;
* `_invalidate_derived_state()`, because a condition can disable an
  organ outright and is therefore a **death-verdict input**;
* `condition.start_condition(character)`, which is what starts the
  medical script — both `PainCondition` and `InfectionCondition` inherit
  `requires_ticker = True`;
* `save_medical_state()`, the only thing that writes it down.

So a botched surgery's infection neither progressed nor survived a
reload. It read as working because of two accidents: on a patient who
already had conditions the running script walks the whole list anyway,
and after any unrelated reload `load_medical_state` re-runs
`start_condition` and brings it alive. Intermittent, never absent.

The rest of the codebase already uses the door —
`substances/registry.py`, `CmdAdmin.py`, `characters.py`. This file was
the outlier, and it had copied *one* of `add_condition`'s guards inline
(the synthetic infection-immunity check) rather than calling the
function that carries all of them.

## #2508 — and nothing was flushed

`_resolve_incise` writes live `Organ` objects through
`_apply_collateral_damage` — 2 HP off everything in the location on a
partial, 3 on a failure — and neither persisted nor re-read vitals.
`save_medical_state` is the only persistence path and
`MedicalScript.at_repeat` never calls it, so a reload restored those
organs to their pre-incise HP while `db.surgical_state["incisions"]`
**did** survive: an open incision on undamaged anatomy.

Repeated failed incises can also take a vital organ to 0. Nothing on
this path fired `at_death` or started a script — the "walking dead"
state that `_mark_organ_removed`'s own comment goes out of its way to
prevent, in the same file.

`_resolve_suture` sets `organ.wound_stage = "treated"` and never wrote
it, while `target.db.sutured_stumps` on the line above does. After a
reload the wound renderer reverted harvested organs to "fresh" — still
wet and red — while `sutured_stumps` said they were closed.

Every sibling resolver flushes. These two were the gaps.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical import procedures as P


class _SeedCase(EvenniaTest):
    def conditions(self, target=None):
        target = target or self.char2
        return list(target.medical_state.conditions or [])

    def types(self, target=None):
        return [getattr(c, "condition_type", None)
                for c in self.conditions(target)]


class TestASeededConditionGoesThroughTheDoor(_SeedCase):
    def test_infection_is_added_via_add_condition(self):
        with mock.patch.object(type(self.char2.medical_state),
                               "add_condition") as add:
            P.seed_infection(self.char2, "chest")
        add.assert_called_once()

    def test_pain_is_added_via_add_condition(self):
        with mock.patch.object(type(self.char2.medical_state),
                               "add_condition") as add:
            P.seed_pain(self.char2, "chest", 20)
        add.assert_called_once()

    def test_the_infection_actually_lands(self):
        P.seed_infection(self.char2, "chest")
        self.assertIn("infection", self.types())

    def test_the_pain_actually_lands(self):
        P.seed_pain(self.char2, "chest", 20)
        self.assertIn("pain", self.types())


class TestTheSeedStartsTicking(_SeedCase):
    """`start_condition` is what creates the MedicalScript. Without it
    the condition object exists and does nothing."""

    def test_a_seeded_infection_starts_the_script(self):
        self.assertEqual(list(self.char2.scripts.get("medical_script")), [])
        P.seed_infection(self.char2, "chest")
        self.assertEqual(len(list(self.char2.scripts.get("medical_script"))),
                         1)

    def test_a_seeded_pain_starts_the_script(self):
        P.seed_pain(self.char2, "chest", 20)
        self.assertTrue(list(self.char2.scripts.get("medical_script")))

    def test_it_does_not_stack_a_second_script(self):
        P.seed_infection(self.char2, "chest")
        P.seed_pain(self.char2, "chest", 20)
        self.assertEqual(len(list(self.char2.scripts.get("medical_script"))),
                         1)


class TestTheSeedIsWrittenDown(_SeedCase):
    def stored(self):
        raw = self.char2.attributes.get("medical_state") or {}
        return [c.get("condition_type") for c in (raw.get("conditions") or [])]

    def test_a_seeded_infection_persists(self):
        P.seed_infection(self.char2, "chest")
        self.assertIn("infection", self.stored())

    def test_a_seeded_pain_persists(self):
        P.seed_pain(self.char2, "chest", 20)
        self.assertIn("pain", self.stored())


class TestTheGuardsStillHold(_SeedCase):
    def test_a_corpse_is_still_a_no_op(self):
        corpse = create_object("typeclasses.corpse.Corpse", key="a corpse",
                               location=self.room1)
        P.seed_infection(corpse, "chest")     # must not raise
        P.seed_pain(corpse, "chest", 20)

    def test_an_unconscious_patient_feels_no_pain(self):
        with mock.patch.object(type(self.char2), "is_unconscious",
                               return_value=True):
            P.seed_pain(self.char2, "chest", 20)
        self.assertNotIn("pain", self.types())

    def test_an_infection_immune_body_does_not_go_septic(self):
        with mock.patch.object(type(self.char2.medical_state),
                               "is_infection_immune", return_value=True):
            P.seed_infection(self.char2, "chest")
        self.assertNotIn("infection", self.types())


class _FlushCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char2.location = self.room1
        self.kit = create_object("typeclasses.items.Item",
                                 key="a surgical kit", location=self.char1)
        mock.patch("world.medical.utils.find_surgical_kit",
                   return_value=self.kit).start()
        self.addCleanup(mock.patch.stopall)

    def stored_hp(self):
        raw = self.char2.attributes.get("medical_state") or {}
        return {o.get("name"): o.get("current_hp")
                for o in (raw.get("organs") or {}).values()}

    def live_hp(self):
        return {n: o.current_hp
                for n, o in self.char2.medical_state.organs.items()}


class TestAFailedInciseIsWrittenDown(_FlushCase):
    def botch(self):
        before = dict(self.live_hp())
        with mock.patch("world.medical.procedures.roll_procedure",
                        return_value={"outcome": "failure", "margin": -9}):
            P._resolve_incise(self.char1, self.char2, location="chest")
        return before

    def test_the_damage_reaches_the_database(self):
        before = self.botch()
        after = self.live_hp()
        hurt = [n for n in before if after[n] < before[n]]
        self.assertTrue(hurt, "fixture: nothing was damaged")
        stored = self.stored_hp()
        for name in hurt:
            self.assertEqual(stored.get(name), after[name],
                             f"{name} was damaged in memory only")

    def test_the_infection_reaches_the_database(self):
        self.botch()
        raw = self.char2.attributes.get("medical_state") or {}
        types = [c.get("condition_type") for c in (raw.get("conditions") or [])]
        self.assertIn("infection", types)

    def test_a_script_is_running_afterwards(self):
        self.botch()
        self.assertTrue(list(self.char2.scripts.get("medical_script")))


class TestASutureIsWrittenDown(_FlushCase):
    """The mutation only fires for a HARVESTED organ still reading
    "fresh" — my first fixture set neither, so the test compared two
    unchanged values and passed against the bug."""

    def harvested_organ(self):
        state = self.char2.medical_state
        organ = next(o for o in state.organs.values()
                     if o.container == "chest")
        organ.injury_type = "harvested"
        organ.wound_stage = "fresh"
        self.char2.save_medical_state()
        return organ

    def suture(self):
        self.char2.db.surgical_state = {"incisions": {"chest": True},
                                        "active_procedure": None}
        with mock.patch("world.medical.procedures.roll_procedure",
                        return_value={"outcome": "success", "margin": 9}):
            P._resolve_suture(self.char1, self.char2)

    def stored_stage(self, name):
        raw = self.char2.attributes.get("medical_state") or {}
        for o in (raw.get("organs") or {}).values():
            if o.get("name") == name:
                return o.get("wound_stage")
        return None

    def test_the_organ_is_treated_in_memory(self):
        organ = self.harvested_organ()
        self.suture()
        self.assertEqual(
            self.char2.medical_state.organs[organ.name].wound_stage,
            "treated", "fixture: the suture did not treat anything")

    def test_and_the_treated_stage_reaches_the_database(self):
        organ = self.harvested_organ()
        self.suture()
        self.assertEqual(self.stored_stage(organ.name), "treated",
                         "the suture lived in memory only")

    def test_the_two_records_agree(self):
        """`sutured_stumps` persisted while the wound stage did not, so
        after a reload the renderer said "still wet and red" about an
        organ the stump record called closed."""
        organ = self.harvested_organ()
        self.suture()
        self.assertEqual(
            self.stored_stage(organ.name),
            self.char2.medical_state.organs[organ.name].wound_stage)


class TestTheFlushIsActuallyCalled(EvenniaTest):
    """Pinned at the source: both resolvers are one line away from
    silently reverting to memory-only again."""

    def test_incise_flushes(self):
        import inspect
        self.assertIn("apply_vital_consequences(target)",
                      inspect.getsource(P._resolve_incise))

    def test_suture_flushes(self):
        import inspect
        self.assertIn("apply_vital_consequences(target)",
                      inspect.getsource(P._resolve_suture))
