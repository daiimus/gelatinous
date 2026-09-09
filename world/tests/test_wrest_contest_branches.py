"""The two wrest branches that decide the contest (#1512).

#1512: *"Wrest — a Grit-vs-Grit contest with grapple disadvantage and
instant success against unconscious or dead targets. Only
`test_inventory_command_identity.py` touches it, incidentally."*

`test_a_failed_wrest_gives_it_back` has since covered the TRANSFER half
thoroughly -- who ends up holding what, and the restore path when the
wield fails. What neither file touches is the part that decides whether
a transfer happens at all:

    is_grappled = self._is_target_grappled(target)
    if self._is_target_unconscious_or_dead(target):
        success = True
    else:
        success = self._execute_grit_contest(
            caller, target, is_grappled, roll_stat, roll_with_disadvantage)

Both branches are exactly the kind of thing #1512 warned about: they
break silently under a refactor, because a wrest that quietly stopped
using disadvantage still succeeds often enough to look fine.

The unconscious branch has a scar of its own recorded in the source --
"an unconscious mark rolling full Grit was the stub this replaces" -- so
it has regressed here once already.

Asserted through the real helpers with the roll functions injected, so
the test reads the DECISION rather than a dice outcome; the contest is
random by design and asserting on a random result is how a test earns a
reputation for flaking.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.CmdInventory import CmdWrest


class _Contest(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.cmd = CmdWrest()
        self.cmd.caller = self.char1

    def _contest(self, *, grappled):
        """Run the contest with both rolls stubbed, and report what the
        TARGET's roll was asked for."""
        asked = {}

        def fake_roll_stat(who, stat):
            asked.setdefault("plain", []).append(who)
            return 10

        def fake_disadvantage(value):
            asked["disadvantage"] = value
            return 1, 1, 1

        won = self.cmd._execute_grit_contest(
            self.char1, self.char2, grappled,
            fake_roll_stat, fake_disadvantage)
        return won, asked


class TestAGrappledTargetRollsWithDisadvantage(_Contest):

    def test_an_ungrappled_target_rolls_plainly(self):
        """Control: without this, 'uses disadvantage' would also be true
        of code that always used it."""
        _won, asked = self._contest(grappled=False)
        self.assertNotIn("disadvantage", asked)
        self.assertIn(self.char2, asked["plain"])

    def test_a_grappled_target_does_not(self):
        _won, asked = self._contest(grappled=True)
        self.assertIn("disadvantage", asked,
                      "a grappled target rolled a plain Grit check")
        self.assertNotIn(self.char2, asked.get("plain", []))

    def test_the_caller_always_rolls_plainly(self):
        """The disadvantage belongs to the person being held, not the
        person doing the holding."""
        _won, asked = self._contest(grappled=True)
        self.assertEqual(asked["plain"], [self.char1])


class TestAnUnconsciousTargetGivesNoContest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.cmd = CmdWrest()

    def test_a_conscious_target_is_contested(self):
        """Control. `is_conscious` is the medical layer's answer, and
        the branch must actually consult it."""
        with mock.patch("world.consent.is_conscious", return_value=True):
            self.assertFalse(
                self.cmd._is_target_unconscious_or_dead(self.char2))

    def test_an_unconscious_target_is_not(self):
        with mock.patch("world.consent.is_conscious", return_value=False):
            self.assertTrue(
                self.cmd._is_target_unconscious_or_dead(self.char2))

    def test_an_unreadable_target_is_contested(self):
        """Fails CONTESTED, not free: an unreadable body must not become
        a free steal. The source says so -- "unreadable state = contest
        it"."""
        with mock.patch("world.consent.is_conscious",
                        side_effect=RuntimeError("no medical state")):
            self.assertFalse(
                self.cmd._is_target_unconscious_or_dead(self.char2))
