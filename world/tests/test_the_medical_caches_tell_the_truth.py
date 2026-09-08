"""A seated organ moves the death verdict, and a dressing that heals
nothing does not keep a script alive (#2494, #2495).

## #2494 defect 1 — a cache that was never read

`_cache_dirty` was initialised `True`, set `True` in five places, and
set `False` in **none**. So

```python
if not self._cache_dirty and capacity_name in self._capacity_cache:
    return self._capacity_cache[capacity_name]
```

could never pass: the early return was unreachable, and
`self._capacity_cache[capacity_name] = capacity_level` was a write-only
store that grew and was never consulted. Confirmed by repro — after a
`calculate_body_capacity("sight")` the flag is still `True` and the dict
holds seven keys nobody will ever read.

Deleted rather than repaired. `_cached_is_dead` already absorbs the hot
path it was meant to protect (`Character.msg` calls `is_dead()` on every
message), and a capacity cache that *did* work would have made defect 2
strictly worse, because stale capacities would then be served too.

## #2494 defect 2 — the invalidation contract was wrong about "every"

Stated twice in `core.py`: *"invalidated by the `blood_level` /
`Organ.current_hp` setters and by condition add/remove — every input
that can flip the verdict."* `_compute_is_dead` reads four **capacities**,
and a capacity is computed from the organs *present in the dict*. Nine
sites mutated that dict directly, and `procedures.py` contains no
invalidation call of any kind.

The issue asked for a repro before fixing, because surgery might
invalidate incidentally through tissue damage. Two things came back:

* the **removal** direction is not reachable — a missing organ reads as
  *full* capacity (a body with no heart still scores 1.0 blood_pumping),
  and harvest doesn't delete anyway, it zeroes HP through
  `_mark_organ_removed`, which the capacity math does read;
* the **seating** direction is real, and it is the one that matters.
  Destroy a heart → `blood_pumping` 0.0, verdict True, cached by the
  next message. Seat a fresh one → capacity back to 1.0,
  `_compute_is_dead()` says False, and `is_dead()` still answers
  **True**.

That is the clinic's cyber-heart install leaving the patient reading
dead.

## #2495 — an immortal no-op script

Two functions decided "is there healing work?" with different
predicates. `_has_healing_work` kept the script alive on
`dressing_rate > 0`; `_process_healing` did the work only when
`_hp_per_tick(rate) > 0`. With `WOUND_HEALING_DIVISOR = 5` and
`WOUND_HEALING_FLOOR_HP_PER_TICK = 0`, a rate of 1–4 gives `4 // 5 = 0`
— satisfying the first and failing the second, for a script that ticks
forever, heals nothing, and never deletes itself.

They share one predicate now. Which way it resolves is worth saying
plainly: a rate of 1–4 dresses a wound without healing it, and the
script stops rather than idling. If weak dressings should inch a wound
back, `WOUND_HEALING_FLOOR_HP_PER_TICK` is the lever — that is balance,
and this is correctness.
"""
from evennia.utils.test_resources import EvenniaTest

from world.medical.core import Organ
from world.medical.script import (_has_healing_work, _hp_per_tick,
                                  _process_healing)


class _StateCase(EvenniaTest):
    def state(self):
        return self.char2.medical_state


class TestSeatingAnOrganMovesTheVerdict(_StateCase):
    def kill_the_heart(self):
        state = self.state()
        state.organs["heart"].current_hp = 0
        self.assertTrue(state.is_dead(), "fixture: the patient should be dying")
        return state

    def fresh_heart(self, state):
        spec = dict(state.organs["heart"].data)
        organ = Organ("heart", organ_data=spec)
        organ.medical_state = state
        return organ

    def test_a_replacement_heart_brings_them_back(self):
        state = self.kill_the_heart()
        state.add_organ("heart", self.fresh_heart(state))
        self.assertFalse(state.is_dead(),
                         "the patient still reads dead with a working heart")

    def test_the_capacity_really_did_recover(self):
        state = self.kill_the_heart()
        state.add_organ("heart", self.fresh_heart(state))
        self.assertEqual(state.calculate_body_capacity("blood_pumping"), 1.0)

    def test_the_cached_and_computed_verdicts_agree(self):
        state = self.kill_the_heart()
        state.add_organ("heart", self.fresh_heart(state))
        self.assertEqual(state.is_dead(), state._compute_is_dead())

    def test_the_door_sets_the_back_reference(self):
        """`Organ.__init__` sets HP before `medical_state` is assigned,
        so the setter's own invalidation is a no-op against None."""
        state = self.state()
        spec = dict(state.organs["heart"].data)
        organ = Organ("heart", organ_data=spec)
        self.assertIsNone(getattr(organ, "medical_state", None))
        state.add_organ("heart", organ)
        self.assertIs(organ.medical_state, state)

    def test_removing_an_organ_invalidates_too(self):
        state = self.state()
        state.is_dead()
        self.assertIsNotNone(state._cached_is_dead)
        state.remove_organ("heart")
        self.assertIsNone(state._cached_is_dead)

    def test_removing_something_absent_is_a_no_op(self):
        state = self.state()
        self.assertIsNone(state.remove_organ("a_nonexistent_organ"))


class TestTheDeadCacheIsGone(_StateCase):
    def test_the_flag_does_not_exist(self):
        self.assertFalse(hasattr(self.state(), "_cache_dirty"))

    def test_the_store_does_not_exist(self):
        self.assertFalse(hasattr(self.state(), "_capacity_cache"))

    def test_capacity_still_computes(self):
        self.assertEqual(self.state().calculate_body_capacity("sight"), 1.0)

    def test_capacity_still_falls_when_the_organ_dies(self):
        state = self.state()
        state.organs["heart"].current_hp = 0
        self.assertEqual(state.calculate_body_capacity("blood_pumping"), 0.0)

    def test_the_death_verdict_cache_still_works(self):
        """Cleared first: `Character.msg` calls `is_dead()`, so by the
        time a test looks the verdict is already primed."""
        state = self.state()
        state._invalidate_derived_state()
        self.assertIsNone(state._cached_is_dead)
        state.is_dead()
        self.assertIsNotNone(state._cached_is_dead)


class TestOnePredicateForHealing(_StateCase):
    def dressed(self, rate):
        organ = self.state().organs["heart"]
        organ.current_hp = max(1, organ.max_hp - 5)
        organ.stabilized = True
        organ.dressing_rate = rate
        return organ

    def test_a_rate_below_the_divisor_heals_nothing(self):
        self.dressed(4)
        self.assertEqual(_hp_per_tick(4), 0)
        self.assertEqual(_process_healing(self.char2, self.state()), [])

    def test_and_therefore_does_not_keep_the_script_alive(self):
        """The stall: alive by one predicate, skipped by the other."""
        self.dressed(4)
        self.assertFalse(_has_healing_work(self.state()))

    def test_a_real_dressing_still_counts_as_work(self):
        self.dressed(5)
        self.assertTrue(_has_healing_work(self.state()))

    def test_and_still_heals(self):
        organ = self.dressed(5)
        before = organ.current_hp
        _process_healing(self.char2, self.state(), elapsed_minutes=1.0)
        self.assertGreater(organ.current_hp, before)

    def test_the_two_answers_cannot_disagree(self):
        """Same list, both callers — that is the whole fix. Imported
        here rather than at module scope: `_healing_organs` is new, and
        a module-scope import of it turns this whole file into a loader
        error against the unfixed code, which proves nothing."""
        from world.medical.script import _healing_organs
        for rate in (0, 1, 3, 4, 5, 10, 20):
            self.dressed(rate)
            self.assertEqual(
                _has_healing_work(self.state()),
                bool(_healing_organs(self.state())),
                f"rate {rate}")

    def test_a_full_organ_is_not_work(self):
        organ = self.dressed(10)
        organ.current_hp = organ.max_hp
        self.assertFalse(_has_healing_work(self.state()))

    def test_an_undressed_organ_is_not_work(self):
        organ = self.dressed(10)
        organ.stabilized = False
        self.assertFalse(_has_healing_work(self.state()))


class TestThroughTheProcedureItself(EvenniaTest):
    """A PIN, not evidence — and worth saying why.

    This drives the real install resolver, and it passes against the
    unfixed code too. `_resolve_install` assigns `organ.medical_state`
    and *then* `organ.current_hp`, so the HP setter's own invalidation
    fires and the verdict is cleared incidentally. The issue predicted
    exactly this ("I did not confirm that a real procedure removes an
    organ without also writing some organ's current_hp"), and it is
    what makes defect 2 latent rather than live.

    Kept because that incidental save is a coincidence of statement
    order: reorder those two lines and the bug is live again, with no
    other test noticing.
    """

    def setUp(self):
        super().setUp()
        from unittest import mock
        from evennia import create_object
        self.char2.location = self.room1
        kit = create_object("typeclasses.items.Item", key="a surgical kit",
                            location=self.char1)
        mock.patch("world.medical.utils.find_surgical_kit",
                   return_value=kit).start()
        self.addCleanup(mock.patch.stopall)
        self.char2.db.surgical_state = {"incisions": {"chest": True},
                                        "active_procedure": None}

    def dying(self):
        state = self.char2.medical_state
        state.organs["heart"].current_hp = 0
        self.char2.save_medical_state()
        self.assertTrue(state.is_dead(), "fixture: should be dying")
        return state

    def replacement(self):
        from evennia import create_object
        state = self.char2.medical_state
        item = create_object("typeclasses.items.Organ", key="a heart",
                             location=self.char1)
        item.db.organ_name = "heart"
        item.db.condition = "pristine"
        item.db.organ_spec = dict(state.organs["heart"].data)
        return item

    def install(self):
        from unittest import mock
        from world.medical import procedures as P
        self.char1.msg = lambda text=None, **kw: None
        with mock.patch("world.medical.procedures.roll_procedure",
                        return_value={"outcome": "success", "margin": 9}):
            P._resolve_install(self.char1, self.char2,
                               organ_item=self.replacement(),
                               location="chest")

    def test_a_new_heart_stops_them_reading_dead(self):
        state = self.dying()
        self.install()
        self.assertFalse(state.is_dead(),
                         "the patient still reads dead with a new heart")

    def test_the_cached_and_computed_verdicts_agree_afterwards(self):
        state = self.dying()
        self.install()
        self.assertEqual(state.is_dead(), state._compute_is_dead())
