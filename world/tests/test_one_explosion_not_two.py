"""A grenade cooking off in the hands is an ordinary detonation.

Regression pin for #2555. `validate_grenade_throw` did not validate --
on an expired timer it hand-rolled a second, divergent explosion:
damage the thrower, delete the grenade, return.

That skipped everything `explode_standalone_grenade` does:

* the DUD ROLL, so a cook-off could never be a dud;
* clearing `detonation_deadline`, so the reload sweep still held one;
* the room broadcast, so nobody saw it;
* bystander damage, so only the thrower was hurt;
* the chain cascade, so a bag of grenades did not go up.

And it DELETED an object a live timer still referenced.

The only thing special about a cook-off is where it happens, and the
canonical path already reads the location.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from commands.CmdThrow import CmdThrow
from world.combat.constants import NDB_COUNTDOWN_REMAINING


def _cmd(remaining):
    cmd = CmdThrow()
    cmd.caller = MagicMock()
    grenade = MagicMock()
    setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, remaining)
    return cmd, grenade


class TestOneExplosionNotTwo(TestCase):

    def test_a_cook_off_uses_the_canonical_path(self):
        cmd, grenade = _cmd(0)
        with patch("commands.explosion_utils.explode_standalone_grenade") as boom:
            self.assertFalse(cmd.validate_grenade_throw(grenade))
        boom.assert_called_once_with(grenade)

    def test_the_validator_no_longer_deletes_the_grenade(self):
        """A live timer still references it; the canonical path owns
        its disposal."""
        cmd, grenade = _cmd(0)
        with patch("commands.explosion_utils.explode_standalone_grenade"):
            cmd.validate_grenade_throw(grenade)
        grenade.delete.assert_not_called()

    def test_the_validator_no_longer_damages_directly(self):
        cmd, grenade = _cmd(0)
        with patch("commands.explosion_utils.explode_standalone_grenade"):
            cmd.validate_grenade_throw(grenade)
        cmd.caller.take_damage.assert_not_called()

    def test_the_thrower_is_still_told(self):
        cmd, grenade = _cmd(0)
        with patch("commands.explosion_utils.explode_standalone_grenade"):
            cmd.validate_grenade_throw(grenade)
        cmd.caller.msg.assert_called()

    # -- controls ----------------------------------------------------

    def test_a_live_timer_still_throws(self):
        """The control — a validator that always exploded would pass
        every test above."""
        cmd, grenade = _cmd(3)
        with patch("commands.explosion_utils.explode_standalone_grenade") as boom:
            self.assertTrue(cmd.validate_grenade_throw(grenade))
        boom.assert_not_called()

    def test_an_unprimed_grenade_still_throws(self):
        cmd, grenade = _cmd(None)
        with patch("commands.explosion_utils.explode_standalone_grenade") as boom:
            self.assertTrue(cmd.validate_grenade_throw(grenade))
        boom.assert_not_called()
