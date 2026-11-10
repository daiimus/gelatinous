"""No command matches typed text to an object by hand (#3783).

AGENTS.md: "Need search? `caller.search` in a command." and "Always check
`evennia.utils` before writing your own helper."

The game has one matcher for "which object did the player mean":
`Character.search`. It knows keys, aliases, ordinals, identity for people and
what the character can perceive. Commands that compared the typed text against
`.key` or walked `.aliases.all()` themselves each knew a different subset, so
an alias worked in `wield` and not in `rig`, and `2nd` narrowed a twin in one
verb and not the next. Forty such sites were found; the helpers `match_held`
and `pick_worn` were two more hand-rolled matchers written to fix earlier
instances of the same thing.

This test reads the command modules and fails when a function reads
`<obj>.key.lower()`, `<obj>.key.startswith(...)`, `<obj>.key.endswith(...)` or
`<obj>.aliases.all()`, unless it is listed below with the reason it stays.
A listed function that no longer does so also fails, so the list cannot rot.

It reads the syntax tree, so prose in a comment or a docstring does not count.
"""
import ast
from pathlib import Path
from unittest import TestCase

COMMANDS = Path(__file__).resolve().parents[2] / "commands"

#: (file under commands/, qualified function) -> why it is allowed to read
#: a key or an alias list. Every entry is either not typed-name matching at
#: all, or a site #3783 has scheduled and not yet moved.
ALLOWED = {
    ("CmdDoors.py", "find_door"):
        "exit names; scheduled in #3783 (exits and directions)",
    ("CmdStealth.py", "CmdSneak.func"):
        "exit names; scheduled in #3783 (exits and directions)",
    ("combat/core_actions.py", "CmdAttack.func"):
        "the aimed exit; scheduled in #3783 (exits and directions)",
    ("combat/special_actions.py", "CmdAim.func"):
        "the aimed exit; scheduled in #3783 (exits and directions)",
    ("_identity_targeting.py", "_builder_key_matches"):
        "Builder fallback over people; scheduled in #3783 (people)",
    ("combat/jump.py", "CmdJump.handle_explosive_sacrifice"):
        "a Script's key, not typed text",
    ("combat/jump.py", "CmdJump.handle_explosive_sacrifice.reveal_outcome"):
        "a Script's key, not typed text",
    ("combat/jump.py", "CmdJump.finalize_successful_gap_jump"):
        "the return exit by a computed opposite direction, not typed text",
}


def _reads_a_name(node: ast.AST) -> bool:
    """True for `<x>.key.lower()`, `.key.startswith()`, `.key.endswith()`
    and `<x>.aliases.all()`."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return False
    inner = node.func.value
    if not isinstance(inner, ast.Attribute):
        return False
    if inner.attr == "key" and node.func.attr in ("lower", "startswith", "endswith"):
        return True
    return inner.attr == "aliases" and node.func.attr == "all"


def functions_that_read_names() -> set:
    """Every (file, qualified function) in commands/ that reads a key or an
    alias list directly."""
    found = set()

    def walk(node: ast.AST, scope: tuple, rel: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef,
                                  ast.AsyncFunctionDef)):
                walk(child, scope + (child.name,), rel)
            else:
                if _reads_a_name(child):
                    found.add((rel, ".".join(scope) or "<module>"))
                walk(child, scope, rel)

    for path in sorted(COMMANDS.rglob("*.py")):
        rel = path.relative_to(COMMANDS).as_posix()
        walk(ast.parse(path.read_text()), (), rel)
    return found


class TestCommandsNameThingsThroughTheCoreSearch(TestCase):
    def test_no_command_matches_a_name_by_hand(self):
        offenders = functions_that_read_names() - set(ALLOWED)
        self.assertEqual(
            sorted(offenders), [],
            "These functions read .key or .aliases directly. Resolve the "
            "typed name with caller.search(name, candidates=pool, quiet=True) "
            "instead, or add the function to ALLOWED with the reason.")

    def test_the_allowed_list_holds_nothing_already_fixed(self):
        stale = set(ALLOWED) - functions_that_read_names()
        self.assertEqual(
            sorted(stale), [],
            "These are in ALLOWED but no longer read a key or an alias list. "
            "Remove them from the list.")

    def test_the_deleted_matchers_stay_deleted(self):
        """`match_held` (#2976) and `pick_worn` (#2517) each fixed one
        command's blindness to aliases by adding one more matcher beside
        the core one."""
        for path in sorted(COMMANDS.rglob("*.py")):
            names = {n.name for n in ast.walk(ast.parse(path.read_text()))
                     if isinstance(n, ast.FunctionDef)}
            for gone in ("match_held", "pick_worn", "find_breachable",
                         "_find_held_smokable_matching"):
                self.assertNotIn(gone, names, f"{gone} is back in {path.name}")
