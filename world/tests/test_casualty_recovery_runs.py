"""Casualty recovery has never run (#2712).

`is_grappled(combat_handler, character)` takes TWO arguments. Three of
the four call sites in the repo passed one.

The one in `world/director/medical.py` sat inside a `try` whose `except`
returns False -- the same thing the success branch returns -- so the
function could never return anything but False. A medic has NEVER
started a casualty recovery: nine days and 54,000 log lines show
`goal=recover` elected zero times.

What that made unreachable: the `recover` plan and its `lift` step, and
`world/director/disposal.py` entirely, whose only production caller is
inside the recovery job. So a destroyed unit was never stripped -- and a
unit's weapon is an augment organ, so an unstripped wreck is a working
shotgun nobody is holding (#2284).

`world/consent.py:64` is the one correct call and shows the shape: find
the handler first.
"""
import ast
import inspect
import pathlib
from unittest import TestCase, mock

from world.combat.grappling import is_grappled


class TestEveryCallPassesBothArguments(TestCase):
    """AST-level, so a call cannot hide behind a name or a comment."""

    FILES = ("world/director/medical.py", "world/souls/jobs.py",
             "world/consent.py")

    def _repo_root(self):
        import world
        return pathlib.Path(world.__file__).resolve().parent.parent

    def test_the_signature_still_takes_two(self):
        """If this ever changes, the call sites below are wrong again."""
        self.assertEqual(list(inspect.signature(is_grappled).parameters),
                         ["combat_handler", "character"])

    def test_no_call_site_passes_one_argument(self):
        root = self._repo_root()
        offenders = []
        for rel in self.FILES:
            tree = ast.parse((root / rel).read_text())
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call)
                        and getattr(node.func, "id", None) == "is_grappled"
                        and len(node.args) != 2):
                    offenders.append((rel, node.lineno, len(node.args)))
        self.assertEqual(offenders, [])

    def test_a_one_argument_call_really_does_raise(self):
        """Pins the premise rather than taking it on trust."""
        with self.assertRaises(TypeError):
            is_grappled(object())


class TestTheExceptNoLongerHidesACallShapeBug(TestCase):
    """Both the success branch and the except branch returned False, so
    a TypeError was indistinguishable from "somebody already has it".
    The except is narrowed to the failure it was written for."""

    def _units(self):
        """Two security units — `recover_casualty` is deliberately narrow:
        only a unit recovers, and only a unit is recovered."""
        soul, casualty = mock.MagicMock(), mock.MagicMock()
        for u in (soul, casualty):
            u.db.role = "security"
            u.db.species = "robot"
        soul.db.soul_recovering = None
        return soul, casualty

    def test_a_type_error_is_not_swallowed(self):
        from world.director import medical
        soul, casualty = self._units()
        with mock.patch("world.combat.utils.find_character_handler",
                        side_effect=TypeError("wrong arity")):
            with self.assertRaises(TypeError):
                medical.recover_casualty(soul, casualty)

    def test_an_unreadable_hold_is_still_swallowed(self):
        """The pin: the except exists for a real reason — an unreadable
        hold — and must keep covering it."""
        from world.director import medical
        soul, casualty = self._units()
        with mock.patch("world.combat.utils.find_character_handler",
                        side_effect=RuntimeError("combat state gone")):
            self.assertFalse(medical.recover_casualty(soul, casualty))

    def test_a_free_casualty_gets_past_the_hold_check(self):
        """The whole point: with no handler the errand is now REACHABLE.
        Before the fix this branch could never be entered at all."""
        from world.director import medical
        soul, casualty = self._units()
        with mock.patch("world.combat.utils.find_character_handler",
                        return_value=None), \
             mock.patch("world.souls.actions.plan_for",
                        return_value=None) as planned:
            medical.recover_casualty(soul, casualty)
        self.assertTrue(planned.called,
                        "recovery never reached the planner")

    def test_a_held_casualty_is_left_alone(self):
        from world.director import medical
        soul, casualty = self._units()
        with mock.patch("world.combat.utils.find_character_handler",
                        return_value=object()), \
             mock.patch("world.combat.grappling.is_grappled",
                        return_value=True), \
             mock.patch("world.souls.actions.plan_for") as planned:
            self.assertFalse(medical.recover_casualty(soul, casualty))
        self.assertFalse(planned.called)
