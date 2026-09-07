"""The staff guards were dead (#2591).

Twenty-one guards across two files passed a **lockstring** where
`LockHandler.check` expects an **access type**:

```python
if target.locks.check(target, "perm(Builder)"):
```

Evennia's signature is `check(accessing_obj, access_type, default=False,
...)`. The second argument is a key looked up in `self.locks`.
`"perm(Builder)"` is a lockstring, not an access type — **no object
carries a lock keyed `perm(Builder)`** — so the lookup missed and the
`default=False` came back. For everyone, including superusers on the
non-bypass paths.

Measured against a real staff character in the running game:

```
drek (Developer):  locks.check(c, "perm(Builder)")  = False
                   c.check_permstring("Builder")    = True
```

The `@murder` rank-protection block is built entirely on this, so it was
unreachable — the guard that stops a lower-ranked staffer killing a
higher-ranked one never fired.

`check_permstring` is the form this codebase already uses correctly in
`_identity_targeting.py`, `CmdCharacter.py` and `world/emote.py`, and it
honours `PERMISSION_HIERARCHY` — a Developer passes a Builder gate, which
is what every one of these sites intends.

**An observation, not fixed here:** a character whose staff permission
lives only on the **account** rather than the object passes *neither*
form. `Iver Kestrel I` has `developer` on the account and `player` on the
character, and reads False through `check_permstring`,
`check_lockstring(... perm(Builder))` and the old broken call alike. That
is a separate question about where permissions are granted; this change
does not alter it, and the character was outside these guards before and
after.
"""
from evennia.utils.test_resources import EvenniaTest


class TestTheOldFormIsAlwaysFalse(EvenniaTest):
    """Pinned against the installed Evennia: if `check` ever starts
    accepting a lockstring, this fix becomes unnecessary and should say
    so loudly rather than sit there.

    Uses `char2`, which starts with NO permissions — `char1` ships with
    `developer` in this harness, so granting it "Builder" proves nothing
    about a builder.
    """

    def test_a_developer_fails_the_lockstring_form(self):
        self.char2.permissions.add("Developer")
        self.assertFalse(self.char2.locks.check(self.char2, "perm(Builder)"))

    def test_even_an_exact_permission_fails_it(self):
        self.char2.permissions.add("Builder")
        self.assertFalse(self.char2.locks.check(self.char2, "perm(Builder)"))

    def test_the_second_argument_is_documented_as_an_access_type(self):
        import inspect
        from evennia.locks.lockhandler import LockHandler
        sig = inspect.signature(LockHandler.check)
        self.assertEqual(list(sig.parameters)[1:3],
                         ["accessing_obj", "access_type"])


class TestTheNewFormWorks(EvenniaTest):
    def test_a_builder_passes(self):
        self.char2.permissions.add("Builder")
        self.assertTrue(self.char2.check_permstring("Builder"))

    def test_a_developer_passes_a_builder_gate(self):
        """The hierarchy is the whole point — every one of these sites
        means "this rank or above"."""
        self.char2.permissions.add("Developer")
        self.assertTrue(self.char2.check_permstring("Builder"))

    def test_a_player_does_not(self):
        self.assertFalse(self.char2.check_permstring("Builder"))

    def test_a_builder_does_not_pass_a_developer_gate(self):
        """It must not open everything — rank still means something.

        `char2` starts with no permissions; `char1` already carries
        `developer` in this harness, so it passes every gate and would
        make this assertion vacuous.
        """
        self.char2.permissions.add("Builder")
        self.assertFalse(self.char2.check_permstring("Developer"))


class TestNoDeadGuardSurvives(EvenniaTest):
    """The defect is a call that looks exactly like a permission check,
    so the regression is someone writing one again."""

    FILES = ("commands/CmdAdmin.py", "typeclasses/characters.py")

    def _source(self, relpath):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / relpath).read_text(errors="ignore")

    def test_no_lockstring_is_passed_as_an_access_type(self):
        import re
        offenders = []
        for relpath in self.FILES:
            for i, line in enumerate(self._source(relpath).splitlines(), 1):
                if line.lstrip().startswith("#") or "`" in line:
                    continue          # the fix's own notes and docstrings,
                                      # which quote the broken call in
                                      # backticks; real code has none
                if re.search(r'locks\.check\([^,]*,\s*"perm\(', line):
                    offenders.append(f"{relpath}:{i}")
        self.assertEqual(offenders, [])

    def test_the_repo_wide_sweep_is_clean(self):
        """Not just the two files touched — the shape anywhere."""
        import pathlib
        import re
        root = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for sub in ("commands", "world", "typeclasses"):
            for path in (root / sub).rglob("*.py"):
                if "/tests/" in str(path):
                    continue
                for i, line in enumerate(
                        path.read_text(errors="ignore").splitlines(), 1):
                    if line.lstrip().startswith("#") or "`" in line:
                        continue      # notes / docstrings quote the broken
                                      # call in backticks; code does not
                    if re.search(r'locks\.check\([^,]*,\s*"perm\(', line):
                        offenders.append(f"{path.name}:{i}")
        self.assertEqual(offenders, [])

    def test_the_rank_guards_are_still_there(self):
        """Converted, not deleted — @murder's rank protection must
        still exist, now that it can actually run."""
        body = self._source("commands/CmdAdmin.py")
        for rank in ("Builder", "Admin", "Developer"):
            self.assertIn(f'check_permstring("{rank}")', body)
