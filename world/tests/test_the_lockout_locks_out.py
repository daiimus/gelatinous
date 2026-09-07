"""No actions means no actions (#2528), and a sentence starts with a
capital (#2564).

## #2528 — `no_exits` does not imply `no_objs`

`UnconsciousCmdSet` and `DeathCmdSet` replace the character's default
cmdset and set `no_exits = True`. Neither set `no_objs`. Evennia gates
those independently — `cmdhandler.py`:

```python
case "object":
    if not current.no_objs:
        local_obj_cmdsets = yield _get_local_obj_cmdsets(cmdobj)
        if current.no_exits:
            # filter out all exits
```

`no_exits` only strips `ExitCmdSet` **from the object cmdsets it has
already decided to merge**. So every command a fixture in the room
supplies still merged in: `BarCmdSet` (`order`, `till`, `use`,
`prepare`, `clear`) and `LockerCmdSet` (`rent`, `stash`, `retrieve`).

An unconscious character lying at a bar counter could order a drink out
loud, empty the till, and work a locker. The docstrings say *"no
actions"* three times between them, and two trailing comments repeat it;
the flags implemented *"no exits"* only.

The lockout cmdsets contain nothing but OOC and perm-locked staff
commands — help, who, time, quit, py, reload, and the `@heal` /
`@resetmedical` recovery pair kept deliberately so staff can heal
themselves out of a state. None of that comes from an object, so
declining object cmdsets costs the lockout nothing.

## #2564 — two sentence-initial sdescs

`get_display_name` for an unrecognised person returns
`with_article(compose_sdesc(...))` — *"a lean man"*, lowercase by
construction. Two `CmdStealth` messages opened a sentence with it raw,
so a player read *"a lean man tries to melt out of sight"*.
`capitalize_first` is applied 109 times elsewhere, including by
`world/stealth.py` for the same class of message.
"""
from evennia.utils.test_resources import EvenniaTest


class TestTheLockoutDeclinesObjectCommands(EvenniaTest):
    def test_unconscious_declines_objects(self):
        from commands.default_cmdsets import UnconsciousCmdSet
        self.assertTrue(UnconsciousCmdSet.no_objs)

    def test_death_declines_objects(self):
        from commands.default_cmdsets import DeathCmdSet
        self.assertTrue(DeathCmdSet.no_objs)

    def test_both_still_decline_exits(self):
        from commands.default_cmdsets import (DeathCmdSet,
                                              UnconsciousCmdSet)
        self.assertTrue(UnconsciousCmdSet.no_exits)
        self.assertTrue(DeathCmdSet.no_exits)

    def test_the_normal_cmdset_still_allows_objects(self):
        """The flag must be on the lockouts, not on everything."""
        from commands.default_cmdsets import CharacterCmdSet
        self.assertFalse(getattr(CharacterCmdSet, "no_objs", False))


class TestEvenniaStillGatesOnThatFlag(EvenniaTest):
    """Read off the INSTALLED Evennia, so an upgrade that renames or
    re-scopes the flag fails loudly instead of silently reopening the
    till to the unconscious."""

    def _handler_source(self):
        import inspect
        from evennia.commands import cmdhandler
        return inspect.getsource(cmdhandler)

    def test_object_cmdsets_are_gated_on_no_objs(self):
        self.assertIn("if not current.no_objs:", self._handler_source())

    def test_no_exits_only_filters_exit_cmdsets(self):
        """The distinction the fix depends on."""
        src = self._handler_source()
        idx = src.index("if not current.no_objs:")
        window = src[idx:idx + 400]
        self.assertIn("if current.no_exits:", window)
        self.assertIn("ExitCmdSet", window)

    def test_a_cmdset_defaults_to_allowing_objects(self):
        from evennia.commands.cmdset import CmdSet
        self.assertFalse(CmdSet.no_objs)


class TestTheLockoutKeepsWhatItNeeds(EvenniaTest):
    """Declining object cmdsets must not take away the OOC and staff
    recovery commands the lockout deliberately keeps."""

    def _keys(self, cmdset_cls):
        cs = cmdset_cls()
        cs.at_cmdset_creation()
        return {cmd.key for cmd in cs.commands}

    def test_help_survives(self):
        self.assertIn("help", self._keys(
            __import__("commands.default_cmdsets", fromlist=["x"])
            .UnconsciousCmdSet))

    def test_the_staff_recovery_pair_survives(self):
        from commands.default_cmdsets import UnconsciousCmdSet
        keys = self._keys(UnconsciousCmdSet)
        self.assertIn("@heal", keys | {f"@{k}" for k in keys})

    def test_nothing_in_the_lockout_comes_from_an_object(self):
        """The premise of the fix: no lockout command is object-supplied,
        so `no_objs` costs it nothing."""
        from commands.default_cmdsets import (DeathCmdSet,
                                              UnconsciousCmdSet)
        from typeclasses.bar import BarCmdSet
        from typeclasses.lockers import LockerCmdSet
        object_keys = self._keys(BarCmdSet) | self._keys(LockerCmdSet)
        for cls in (UnconsciousCmdSet, DeathCmdSet):
            self.assertEqual(self._keys(cls) & object_keys, set())


class TestASentenceStartsWithACapital(EvenniaTest):
    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdStealth.py").read_text(
            errors="ignore")

    def test_both_messages_capitalize(self):
        body = self._source()
        self.assertNotIn("f\"{caller.get_display_name(observer)} tries", body)
        self.assertNotIn("f\"{caller.get_display_name(char)}'s eyes", body)

    def test_the_helper_is_imported(self):
        self.assertIn("from world.grammar import capitalize_first",
                      self._source())

    def test_it_actually_capitalizes_an_articled_sdesc(self):
        from world.grammar import capitalize_first
        self.assertEqual(capitalize_first("a lean man"), "A lean man")

    def test_it_leaves_a_capital_alone(self):
        from world.grammar import capitalize_first
        self.assertEqual(capitalize_first("Sully"), "Sully")
