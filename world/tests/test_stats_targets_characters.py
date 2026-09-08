"""`@stats <target>` resolves a character, or says it could not
(#2518).

Two defects in the same twenty-five lines, both confirmed live before
fixing.

## Unfiltered global search

```python
matches = search_object(args.strip(), exact=False)
if matches:
    target = matches[0]
grit = target.grit
```

`search_object(exact=False)` is global, partial-matching and
**typeclass-unfiltered**, and `matches[0]` was taken with no check. Run
against the live game:

```
> stats bar
AttributeError: 'BarCounter' object has no attribute 'grit'
```

And `if matches:` had no `else`, so a miss left `target` as the caller —
a staffer who mistyped a name was shown their **own** sheet with no
indication anything had gone wrong.

Every sibling in this file already used `resolve_admin_target`, which
filters to Characters and does a room-identity pass first. This is the
one that did not.

## The permission gate

`self.account.check_permstring(...)` was read unconditionally, so an
account-less caller (an NPC running `score`) raised AttributeError on
the way past — and reading the account directly ignores `@quell`, which
exists so a builder can play without staff powers.

**The fix for that was wrong twice before it was right, and only live
testing caught it.** `caller.check_permstring("Builder")` returns False
for a character puppeted by a Developer account — the object carries
only `player` — so the first version locked staff out of
`@stats <target>` entirely. The working idiom is the `perm()` lockfunc,
which resolves through the puppeting account and honours quell, and
`CmdDescribe` forty lines down was already using it.

Verified end to end in the running game, quelled and unquelled:

```
quelled     stats bar     -> "You can only check your own evaluation."
unquelled   stats bar     -> "No character matches 'bar'."
unquelled   stats sully   -> Sully's sheet        (global key search)
unquelled   stats stocky  -> Pia's sheet          (room sdesc match)
```
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

# `_staff_view` is NEW, so a module-scope import of it turns this whole
# file into a loader error against the unfixed code. Imported per test.
from commands.CmdCharacter import CmdStats


class _StatsCase(EvenniaCommandTest):
    def as_staff(self, on=True):
        return mock.patch("commands.CmdCharacter._staff_view",
                          return_value=on)


class TestANonCharacterIsRefused(_StatsCase):
    def test_a_bar_counter_does_not_crash_it(self):
        create_object("typeclasses.bar.BarCounter", key="the hull-slab bar",
                      location=self.room1)
        with self.as_staff():
            out = self.call(CmdStats(), "bar", caller=self.char1)
        self.assertIn("No character matches", out)

    def test_a_plain_object_is_refused_too(self):
        create_object("typeclasses.objects.Object", key="a crate",
                      location=self.room1)
        with self.as_staff():
            out = self.call(CmdStats(), "crate", caller=self.char1)
        self.assertIn("No character matches", out)

    def test_it_does_not_fall_back_to_your_own_sheet(self):
        """The silent case: a miss used to leave `target` as the
        caller."""
        with self.as_staff():
            out = self.call(CmdStats(), "nobodybythatname",
                            caller=self.char1)
        self.assertNotIn("PSYCHOPHYSICAL", out)

    def test_the_miss_points_at_the_bare_form(self):
        with self.as_staff():
            out = self.call(CmdStats(), "nobodybythatname",
                            caller=self.char1)
        self.assertIn("stats", out)


class TestARealCharacterStillResolves(_StatsCase):
    def test_a_character_in_the_room_resolves(self):
        self.char2.location = self.room1
        with self.as_staff():
            out = self.call(CmdStats(), self.char2.key, caller=self.char1)
        self.assertIn("PSYCHOPHYSICAL", out)

    def test_your_own_sheet_still_works_bare(self):
        out = self.call(CmdStats(), "", caller=self.char1)
        self.assertIn("PSYCHOPHYSICAL", out)


class TestTheGateIsNotStaffOnlyByAccident(_StatsCase):
    def test_a_non_staff_caller_cannot_target(self):
        self.char2.location = self.room1
        with self.as_staff(False):
            out = self.call(CmdStats(), self.char2.key, caller=self.char1)
        self.assertIn("only check your own", out)

    def test_a_non_staff_caller_still_sees_their_own(self):
        with self.as_staff(False):
            out = self.call(CmdStats(), "", caller=self.char1)
        self.assertIn("PSYCHOPHYSICAL", out)


class TestTheGateDoesNotReachThroughAccount(EvenniaCommandTest):
    """An account-less caller — an NPC running `score` — used to raise
    AttributeError on `self.account.check_permstring`."""

    def test_an_account_less_caller_is_not_staff(self):
        npc = create_object("typeclasses.characters.Character",
                            key="an NPC", location=self.room1)
        cmd = CmdStats()
        cmd.caller = npc
        cmd.account = None
        from commands.CmdCharacter import _staff_view
        self.assertFalse(_staff_view(cmd))

    def test_and_the_command_still_runs_for_them(self):
        npc = create_object("typeclasses.characters.Character",
                            key="an NPC", location=self.room1)
        out = self.call(CmdStats(), "", caller=npc)
        self.assertIn("PSYCHOPHYSICAL", out)

    def test_it_uses_the_lock_idiom_not_a_bare_permstring(self):
        """`caller.check_permstring("Builder")` is False for a character
        puppeted by a Developer account — the object carries only
        `player`. Confirmed live; the first fix locked staff out."""
        import inspect

        from commands.CmdCharacter import _staff_view
        body = inspect.getsource(_staff_view)
        self.assertIn("check_lockstring", body)
        self.assertNotIn("cmd.account", body.split('"""')[-1])
