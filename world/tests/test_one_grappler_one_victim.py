"""A grappler holds one person, and the validator converges (#2486).

## The overwrite

A character already grappling someone could start grappling a second
person. The three live resolvers all assign the reference without
reading it:

```python
char_entry[DB_GRAPPLING_DBREF] = get_character_dbref(target)   # x3
```

so the hold on victim #1 was silently replaced, and nothing cleared
victim #1's `grappled_by`. `validate_grapple_action` then refused that
victim's actions with *"you can't do that while grappled by C"* — pinned
by a phantom.

`establish_grapple` has exactly this guard and refuses outright. It is
also unreachable: repo-wide it has one non-definition occurrence, an
unused import. **Releasing rather than refusing** is the smaller change
— it keeps every action the command layer already accepts, where
refusing would remove the ability to switch grapple targets mid-fight,
which is a design call nobody has made.

## Why the validator could never repair it

`validate_and_cleanup_grapple_state` runs at the start of every
`at_repeat`, and its two cross-reference repairs each took *their own
side* as ground truth:

* branch 1 trusts `grappling`, rewrites the victim's `grappled_by`
* branch 2 trusts `grappled_by`, rewrites the grappler's `grappling`

With two victims both claiming the same grappler, both fired on every
pass, the last entry visited won, and `cleanup_needed` was `True`
forever — the handler rewrote `db.combatants` every round for the rest
of the fight without converging. Neither branch ever *cleared* anything,
which is why the corrupt state was a fixed point rather than something
repairable.

`grappling` is a single field and cannot be duplicated; `grappled_by`
can be, and that is exactly the corruption. So `grappling` is the
authority now, and a `grappled_by` that does not match is cleared.

The issue asked for a live repro of the never-converging loop. There is
no live fight to inspect and starting one in the world is not an option,
so it is reproduced here instead: `TestTheValidatorConverges` builds the
exact two-victim state and runs the validator repeatedly.
"""
from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import (DB_CHAR, DB_GRAPPLED_BY_DBREF,
                                    DB_GRAPPLING_DBREF)
from world.combat.grappling import validate_and_cleanup_grapple_state
from world.combat.utils import get_character_dbref


class _GrappleCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.a = self.char1
        self.b = self.char2
        self.c = create_object("typeclasses.characters.Character",
                               key="Cee", location=self.room1)
        self.d = create_object("typeclasses.characters.Character",
                               key="Dee", location=self.room1)
        for char in (self.a, self.b, self.c, self.d):
            char.location = self.room1

    def entry(self, char, grappling=None, grappled_by=None):
        # `get_character_dbref` returns `char.id` — a plain int, NOT the
        # "#8" string `char.dbref` gives. The production resolvers use
        # it on both sides, so a fixture that writes `.dbref` builds
        # state the validator reads as mismatched and my first version
        # of these tests failed for that reason rather than a real one.
        return {
            DB_CHAR: char,
            DB_GRAPPLING_DBREF: get_character_dbref(grappling),
            DB_GRAPPLED_BY_DBREF: get_character_dbref(grappled_by),
        }

    def handler(self, entries):
        handler = MagicMock()
        handler.db.combatants = entries
        return handler

    def corrupt(self):
        """C holds D, then takes B as well — the state the overwrite
        left behind."""
        return [
            self.entry(self.a),
            self.entry(self.b, grappled_by=self.c),
            self.entry(self.c, grappling=self.b),
            self.entry(self.d, grappled_by=self.c),   # orphan
        ]

    def by_char(self, entries, char):
        return next(e for e in entries if e[DB_CHAR] == char)


class TestTheValidatorConverges(_GrappleCase):
    def run_validator(self, entries, passes=1):
        handler = self.handler(entries)
        for _ in range(passes):
            validate_and_cleanup_grapple_state(handler)
            entries = handler.db.combatants
        return entries

    def test_the_orphaned_hold_is_cleared(self):
        entries = self.run_validator(self.corrupt())
        self.assertIsNone(
            self.by_char(entries, self.d)[DB_GRAPPLED_BY_DBREF],
            "D is still pinned by a grappler who is not holding them")

    def test_the_real_grapple_survives(self):
        entries = self.run_validator(self.corrupt())
        self.assertEqual(self.by_char(entries, self.c)[DB_GRAPPLING_DBREF],
                         get_character_dbref(self.b))
        self.assertEqual(self.by_char(entries, self.b)[DB_GRAPPLED_BY_DBREF],
                         get_character_dbref(self.c))

    def snapshot(self, entries):
        return [(e[DB_CHAR].key, e[DB_GRAPPLING_DBREF],
                 e[DB_GRAPPLED_BY_DBREF]) for e in entries]

    def test_it_reaches_a_fixed_point(self):
        """A CORRECTION to the issue, which predicted the state would
        oscillate forever with "the last one visited winning".

        Traced against the real walk order it does not: the visible
        state settles after one pass. What does not stop is the WRITE —
        `cleanup_needed` is True on every pass, so the handler
        re-persists `db.combatants` every combat round for the rest of
        the fight, writing the same corrupt values back. The corruption
        is stable, not oscillating; and it is never repaired.

        Kept, and compared between CONSECUTIVE passes rather than pass 1
        against pass 4 — an oscillation of period 2 makes those two
        agree, so my first version would have passed against a bug that
        did oscillate.
        """
        entries = self.corrupt()
        for _ in range(5):
            before = self.snapshot(entries)
            entries = self.run_validator(entries, passes=1)
            after = self.snapshot(entries)
            if before == after:
                return
        self.fail(f"the validator never settled: {after}")

    def test_the_handler_stops_being_rewritten_every_round(self):
        """The half of the issue's claim that IS true: `cleanup_needed`
        was True on every pass, so the handler persisted
        `db.combatants` once per combat round for the rest of the fight.

        Counted with a real recording object rather than off
        `mock_calls` — a MagicMock records reads and writes alike, so
        counting calls that mention "combatants" measures nothing.
        """
        class _Db:
            def __init__(self, entries):
                object.__setattr__(self, "_entries", entries)
                object.__setattr__(self, "writes", 0)

            def __getattr__(self, name):
                if name == "combatants":
                    return object.__getattribute__(self, "_entries")
                raise AttributeError(name)

            def __setattr__(self, name, value):
                if name == "combatants":
                    object.__setattr__(self, "writes",
                                       object.__getattribute__(self, "writes") + 1)
                    object.__setattr__(self, "_entries", value)
                else:
                    object.__setattr__(self, name, value)

        handler = MagicMock()
        handler.db = _Db(self.corrupt())
        validate_and_cleanup_grapple_state(handler)      # the repair
        after_repair = handler.db.writes
        self.assertEqual(after_repair, 1, "the repair should write once")
        validate_and_cleanup_grapple_state(handler)      # nothing to do
        self.assertEqual(handler.db.writes, after_repair,
                         "the validator rewrote a chart it had nothing "
                         "to change")

    def test_it_settles_on_the_first_pass(self):
        entries = self.run_validator(self.corrupt(), passes=1)
        before = self.snapshot(entries)
        entries = self.run_validator(entries, passes=1)
        self.assertEqual(self.snapshot(entries), before)

    def test_a_healthy_pair_is_left_alone(self):
        entries = [self.entry(self.a, grappling=self.b),
                   self.entry(self.b, grappled_by=self.a)]
        out = self.run_validator(entries)
        self.assertEqual(self.by_char(out, self.a)[DB_GRAPPLING_DBREF],
                         get_character_dbref(self.b))
        self.assertEqual(self.by_char(out, self.b)[DB_GRAPPLED_BY_DBREF],
                         get_character_dbref(self.a))

    def test_a_missing_backreference_is_still_repaired(self):
        """Branch 1 still trusts `grappling` — that half was correct."""
        entries = [self.entry(self.a, grappling=self.b),
                   self.entry(self.b)]
        out = self.run_validator(entries)
        self.assertEqual(self.by_char(out, self.b)[DB_GRAPPLED_BY_DBREF],
                         get_character_dbref(self.a))


class TestAGrapplerHoldsOnePerson(_GrappleCase):
    def release(self, entries, grappler):
        from world.combat.grappling import release_existing_grapple
        return release_existing_grapple(self.by_char(entries, grappler),
                                        entries)

    def test_taking_a_new_hold_frees_the_old_victim(self):
        entries = [self.entry(self.c, grappling=self.d),
                   self.entry(self.d, grappled_by=self.c),
                   self.entry(self.b)]
        self.release(entries, self.c)
        self.assertIsNone(self.by_char(entries, self.d)[DB_GRAPPLED_BY_DBREF])
        self.assertIsNone(self.by_char(entries, self.c)[DB_GRAPPLING_DBREF])

    def test_it_returns_who_was_let_go(self):
        entries = [self.entry(self.c, grappling=self.d),
                   self.entry(self.d, grappled_by=self.c)]
        self.assertIs(self.release(entries, self.c), self.d)

    def test_holding_nobody_is_a_no_op(self):
        entries = [self.entry(self.c), self.entry(self.d)]
        self.assertIsNone(self.release(entries, self.c))
        self.assertIsNone(self.by_char(entries, self.d)[DB_GRAPPLED_BY_DBREF])

    def test_it_does_not_free_somebody_elses_victim(self):
        """Only a `grappled_by` that names THIS grappler is cleared."""
        entries = [self.entry(self.c, grappling=self.d),
                   self.entry(self.d, grappled_by=self.a)]
        self.release(entries, self.c)
        self.assertEqual(self.by_char(entries, self.d)[DB_GRAPPLED_BY_DBREF],
                         get_character_dbref(self.a))

    def test_a_vanished_victim_does_not_raise(self):
        entries = [self.entry(self.c)]
        entries[0][DB_GRAPPLING_DBREF] = 999999
        self.release(entries, self.c)      # must not raise
        self.assertIsNone(self.by_char(entries, self.c)[DB_GRAPPLING_DBREF])


class TestTheResolversCallIt(EvenniaTest):
    """Pinned: three resolvers, and the guard that should have covered
    them lives on a function nobody calls."""

    def source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "world" / "combat" /
                "grappling.py").read_text(errors="ignore")

    def test_every_assignment_is_preceded_by_a_release(self):
        body = self.source()
        takes = body.count(
            "char_entry[DB_GRAPPLING_DBREF] = get_character_dbref(target)")
        releases = body.count(
            "release_existing_grapple(char_entry, combatants_list")
        self.assertEqual(takes, releases)
        self.assertEqual(takes, 3)
