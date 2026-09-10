"""Chargen's menu builtins are actually off (#2551).

Every chargen node passed `"auto_help": False, "auto_look": False`
inside its OPTION dicts — 42 keys across 21 dicts. Those are `EvMenu`
CONSTRUCTOR arguments. The option homogeniser
(`evennia/utils/evmenu.py`) reads exactly four keys from an option dict
— `key`, `desc`/`text`, `goto`, `exec` — and silently discards the
rest, so the flags did nothing and the defaults (all True) stood.

`auto_quit` was not even among the keys being uselessly passed, so `q`
was never addressed at all. It closed the menu at every node —
including the final confirmation screen, which advertises exactly
`[Y]` and `[N]` — and `_charcreate_exit_callback` DISCONNECTS a session
that has no sleeve yet, while `start_character_creation` resets
`charcreate_data` on reconnect. One keystroke threw away the name, sex,
height, build, hair, and the whole 300-point G.R.I.M. distribution.

`look` and `help` were swallowed the same way: the aliases are
installed as menu-level commands matching BEFORE a node's `_default`,
so they could not be used as chargen input either.
"""
import inspect
import re

from evennia.utils import evmenu
from evennia.utils.test_resources import EvenniaTest

from commands import charcreate

#: Read off the module with an EMPTY default rather than imported by
#: name. An import that fails makes this file ERROR against the unfixed
#: tree, and an error stops a test before it can assert anything — and
#: an empty mapping is exactly the unfixed reality, so the assertions
#: below fail there for the right reason.
NO_MENU_BUILTINS = getattr(charcreate, "_NO_MENU_BUILTINS", {})


class TestTheHomogeniserIgnoresThem(EvenniaTest):
    """The premise, read off the Evennia the game actually imports —
    not off the version this was written against."""

    def test_an_option_dict_carries_only_four_keys(self):
        source = inspect.getsource(evmenu.EvMenu._parse_menudata) \
            if hasattr(evmenu.EvMenu, "_parse_menudata") else ""
        homogenise = inspect.getsource(evmenu.EvMenu)
        self.assertIn('dic.get("key")', homogenise)
        self.assertNotIn('dic.get("auto_help")', homogenise,
                         "EvMenu now reads auto_help per option; the "
                         "constructor arguments below may be redundant")

    def test_the_flags_are_constructor_arguments(self):
        signature = inspect.signature(evmenu.EvMenu.__init__)
        for flag in ("auto_quit", "auto_look", "auto_help"):
            self.assertIn(flag, signature.parameters)


class TestChargenTurnsThemOff(EvenniaTest):

    def test_no_option_dict_still_carries_them(self):
        """Comment lines are stripped first: the constant's own
        docstring quotes the defect, and counting that as an occurrence
        would make this test fail for describing itself."""
        code = "\n".join(line for line in
                         inspect.getsource(charcreate).splitlines()
                         if not line.lstrip().startswith("#"))
        stray = re.findall(r'"auto_(?:help|look|quit)":\s*False', code)
        # three survive, in the constructor kwargs dict itself
        self.assertEqual(
            len(stray), 3,
            "an inert per-option auto_* key is back in a chargen node")

    def test_every_menu_is_built_with_them_off(self):
        """Both instantiations — the first-character menu and the
        respawn menu. A fix applied to one is the same defect twice."""
        source = inspect.getsource(charcreate)
        built = source.count("CharCreateEvMenu(\n")
        passed = source.count("**_NO_MENU_BUILTINS,")
        self.assertEqual(built, passed,
                         "a chargen menu is still built with the "
                         "builtins on")

    def test_quit_is_among_them(self):
        """The one that actually discarded a character, and the one
        that was never passed at all."""
        self.assertIs(NO_MENU_BUILTINS.get("auto_quit"), False)

    def test_and_so_are_look_and_help(self):
        self.assertIs(NO_MENU_BUILTINS.get("auto_look"), False)
        self.assertIs(NO_MENU_BUILTINS.get("auto_help"), False)


class TestTheAliasesFollowTheFlags(EvenniaTest):
    """Drive Evennia's own alias installation rather than trusting the
    flag names: this is the step that turns a constructor argument into
    a command that eats `q`."""

    def _aliases(self, **flags):
        menu = evmenu.EvMenu.__new__(evmenu.EvMenu)
        for name, value in (("auto_quit", True), ("auto_look", True),
                            ("auto_help", True)):
            setattr(menu, name, flags.get(name, value))
        cmd = evmenu.CmdEvMenuNode()
        cmd.aliases = []
        # `_update_aliases` ends with a `self.msg(...)` debug line that
        # wants a caller. Stubbed rather than worked around, so the
        # method under test is Evennia's real one.
        cmd.msg = lambda *a, **kw: None
        cmd._update_aliases(menu)
        return set(cmd.aliases)

    def test_the_defaults_install_q(self):
        """Control: with the flags left alone, `q` IS a command — which
        is what was happening, because the option dicts never reached
        the constructor."""
        self.assertIn("q", self._aliases())

    def test_chargen_flags_do_not(self):
        self.assertNotIn("q", self._aliases(**NO_MENU_BUILTINS))
        self.assertNotIn("quit", self._aliases(**NO_MENU_BUILTINS))

    def test_nor_look_nor_help(self):
        aliases = self._aliases(**NO_MENU_BUILTINS)
        for alias in ("l", "look", "h", "help"):
            self.assertNotIn(alias, aliases)
