""""throws a rock None" (#2548).

`obj.ndb` returns a `DbHolder` whose `__getattribute__` **returns** the
handler's `get()` — `None` for a missing key — rather than raising. So
`getattr`'s third argument is unreachable: the default never fires and
you get `None` instead.

Seven sites passed a non-None default and read the `None`:

```
commands/CmdThrow.py    x2   "that direction" / "nearby"
commands/bar_menu.py    x2   "house mix"
commands/CmdOperate.py  x2   "?"
commands/combat/jump.py x1   "someone"
```

**The visible one.** In `announce_throw_origin`'s fallback branch, with
no aim set — which is every bare `throw <thing>` — `aim_direction` was
`None`, so the `== "nearby"` test failed and the room got
`MSG_THROW_ORIGIN_FALLBACK`:

```
Jorge throws a rock None
```

instead of the spec'd `MSG_THROW_ORIGIN_HERE`, *"Jorge tosses a rock
nearby"*. The default was doing exactly the work it looks like it does
— and never ran.

The fix is `getattr(..., None) or default`, which is the idiom the
codebase already uses (`world/llm/reflex.py:122`).

**Not changed, and deliberately.** Three sites pass a *container*
default — `set()` in `actions.py` and `attack.py`, `[]` in
`throwing.py`. Those also receive `None`, but each is followed
immediately by a real `if not proximity_set:` or `isinstance` check that
catches it, so the behaviour is correct today. #2487 documented that
family; re-touching them here would be churn, not a fix.

Two more pass `False` (`death_processed`, `NDB_CHARGE_BONUS`). `None` is
falsy, so those are exactly equivalent.
"""
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import (MSG_THROW_ORIGIN_FALLBACK,
                                    MSG_THROW_ORIGIN_HERE)


class TestTheDefaultIsUnreachable(EvenniaTest):
    """The mechanism, pinned against the installed Evennia — an upgrade
    that made `ndb` raise on a miss would make all seven fixes
    unnecessary, and this should say so loudly rather than silently."""

    def test_a_string_default_does_not_fire(self):
        self.assertIsNone(
            getattr(self.char1.ndb, "probe_never_set", "a fallback"))

    def test_a_container_default_does_not_fire_either(self):
        self.assertIsNone(getattr(self.char1.ndb, "probe_never_set", set()))

    def test_the_or_idiom_does_fire(self):
        self.assertEqual(
            getattr(self.char1.ndb, "probe_never_set", None) or "a fallback",
            "a fallback")

    def test_a_real_value_still_wins(self):
        self.char1.ndb.probe_set = "east"
        self.assertEqual(
            getattr(self.char1.ndb, "probe_set", None) or "a fallback",
            "east")


class TestTheThrowLineReadsRight(EvenniaTest):
    """The branch the player actually sees."""

    def line_for(self, aim_direction):
        """`announce_throw_origin`'s fallback branch, as it now reads."""
        direction = aim_direction or "nearby"
        if direction == "nearby":
            return MSG_THROW_ORIGIN_HERE.format(
                thrower="Jorge", object="rock")
        return MSG_THROW_ORIGIN_FALLBACK.format(
            thrower="Jorge", object="rock", direction=direction)

    def test_no_aim_tosses_it_nearby(self):
        self.assertEqual(self.line_for(None), "Jorge tosses a rock nearby")

    def test_an_aim_still_names_the_direction(self):
        self.assertEqual(self.line_for("east"),
                         "Jorge throws a rock east")

    def test_the_word_none_never_reaches_the_room(self):
        self.assertNotIn("None", self.line_for(None))

    def test_the_old_shape_did_leak_it(self):
        """Demonstrates the defect rather than asserting it: with the
        unreachable default, `aim_direction` was None and fell through
        to the directional template."""
        old = MSG_THROW_ORIGIN_FALLBACK.format(
            thrower="Jorge", object="rock", direction=None)
        self.assertEqual(old, "Jorge throws a rock None")


class TestEverySiteUsesTheIdiom(EvenniaTest):
    """Pinned against the source: the bug is a plausible-looking third
    argument, so a future edit re-adding one is the regression."""

    FILES = ("commands/CmdThrow.py", "commands/bar_menu.py",
             "commands/CmdOperate.py", "commands/combat/jump.py")

    def _source(self, relpath):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / relpath).read_text(errors="ignore")

    def test_no_string_default_survives(self):
        import re
        offenders = []
        for relpath in self.FILES:
            for i, line in enumerate(self._source(relpath).splitlines(), 1):
                if re.search(r'getattr\([^)]*\.ndb,[^,)]+,\s*"', line):
                    offenders.append(f"{relpath}:{i}")
        self.assertEqual(offenders, [])

    def test_the_fixed_sites_read_none_then_or(self):
        body = self._source("commands/CmdThrow.py")
        self.assertIn('None) or "nearby"', body)
        self.assertIn('None) or "that direction"', body)

    def test_the_other_three_files_too(self):
        self.assertIn('None) or "house mix"',
                      self._source("commands/bar_menu.py"))
        self.assertIn('None) or "?"',
                      self._source("commands/CmdOperate.py"))
        self.assertIn('or "someone"',
                      self._source("commands/combat/jump.py"))


class TestTheHarmlessOnesAreLeftAlone(EvenniaTest):
    """Stated as a decision, not an oversight: these receive `None` too,
    and a real check immediately below catches it."""

    def _source(self, relpath):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / relpath).read_text(errors="ignore")

    def test_the_proximity_sites_still_guard_themselves(self):
        for relpath in ("world/combat/actions.py", "world/combat/attack.py"):
            body = self._source(relpath)
            self.assertIn("if not proximity_set:", body,
                          f"{relpath} lost the check that makes the "
                          f"unreachable default harmless")

    def test_the_grenade_site_still_checks_the_type(self):
        body = self._source("world/combat/throwing.py")
        self.assertIn("if not isinstance(grenade_proximity, list):", body)
