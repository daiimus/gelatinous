"""Movement coupling (world/movement_coupling.py + commands/CmdFollow.py) —
TRUST_AND_CONSENT_SPEC §9 Phase 3.

MagicMock stand-ins throughout: the contract under test is that every
coupled move goes through the REAL exit command (execute_cmd) and that the
escort path re-checks consent per move. Ordering: followers trail (leader
already arrived), escortees are ushered ahead (before the leader moves).
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.movement_coupling import (
    bring_followers, followers_of, sever_follow, usher_escortee,
)


def _room(*contents):
    room = MagicMock()
    room.contents = list(contents)
    return room


def _exit(destination, key="north"):
    ex = MagicMock()
    ex.destination = destination
    ex.key = key
    return ex


def _char(location=None):
    c = MagicMock()
    c.location = location
    c.db.following = None
    c.db.escorting = None
    return c


def _walker(location):
    """A char whose execute_cmd actually 'moves' it to the exit's room."""
    c = _char(location)

    def _go(cmd):
        for obj in c.location.contents:
            if getattr(obj, "key", None) == cmd and hasattr(obj, "destination"):
                c.location = obj.destination
                return
    c.execute_cmd.side_effect = _go
    return c


class TestFollow(TestCase):
    def _setup(self):
        dest = _room()
        leader = _char(dest)                      # leader already arrived
        source = _room(_exit(dest))
        follower = _walker(source)
        follower.db.following = leader
        source.contents.append(follower)
        return leader, source, dest, follower

    def test_follower_trails_through_the_real_exit(self):
        leader, source, dest, follower = self._setup()
        bring_followers(leader, source)
        follower.execute_cmd.assert_called_once_with("north")
        self.assertIs(follower.location, dest)
        self.assertIs(follower.db.following, leader)   # link holds

    def test_follower_who_bounces_loses_the_trail(self):
        leader, source, dest, follower = self._setup()
        follower.execute_cmd.side_effect = None        # lock: no movement
        bring_followers(leader, source)
        self.assertIsNone(follower.db.following)
        self.assertIn("lose", follower.msg.call_args.args[0])

    def test_teleporting_leader_sheds_followers(self):
        leader, source, dest, follower = self._setup()
        source.contents = [follower]                   # no traceable exit
        bring_followers(leader, source)
        follower.execute_cmd.assert_not_called()
        self.assertIsNone(follower.db.following)

    def test_only_source_room_followers_move(self):
        # chain termination: a follower already elsewhere isn't yanked
        leader, source, dest, follower = self._setup()
        elsewhere = _room()
        follower.location = elsewhere
        source.contents.remove(follower)
        bring_followers(leader, source)
        follower.execute_cmd.assert_not_called()

    def test_sever_notifies_both(self):
        leader, source, dest, follower = self._setup()
        sever_follow(follower)
        self.assertIsNone(follower.db.following)
        self.assertIn("stop following", follower.msg.call_args.args[0])
        self.assertIn("stops following you", leader.msg.call_args.args[0])


class TestEscort(TestCase):
    def _setup(self):
        dest = _room()
        source = _room(_exit(dest))
        leader = _char(source)
        escortee = _walker(source)
        source.contents.append(escortee)
        leader.db.escorting = escortee
        return leader, source, dest, escortee

    def test_escortee_ushered_ahead(self):
        leader, source, dest, escortee = self._setup()
        with patch("world.consent.check_consent", return_value=True), \
                patch("world.consent.is_conscious", return_value=True):
            ok = usher_escortee(leader, dest)
        self.assertTrue(ok)                            # leader may proceed
        escortee.execute_cmd.assert_called_once_with("north")
        self.assertIs(escortee.location, dest)         # they went FIRST
        self.assertIs(leader.db.escorting, escortee)   # coupling holds

    def test_refused_doorway_stops_the_leader(self):
        leader, source, dest, escortee = self._setup()
        escortee.execute_cmd.side_effect = None        # they bounce
        with patch("world.consent.check_consent", return_value=True), \
                patch("world.consent.is_conscious", return_value=True):
            ok = usher_escortee(leader, dest)
        self.assertFalse(ok)                           # move aborted
        self.assertIs(leader.db.escorting, escortee)   # coupling holds
        self.assertIn("refuses them", leader.msg.call_args.args[0])

    def test_revoked_consent_releases_at_the_next_move(self):
        leader, source, dest, escortee = self._setup()
        with patch("world.consent.check_consent", return_value=False), \
                patch("world.consent.is_conscious", return_value=True):
            ok = usher_escortee(leader, dest)
        self.assertTrue(ok)                            # leader walks on alone
        self.assertIsNone(leader.db.escorting)
        escortee.execute_cmd.assert_not_called()

    def test_unconscious_escortee_released(self):
        leader, source, dest, escortee = self._setup()
        with patch("world.consent.is_conscious", return_value=False):
            ok = usher_escortee(leader, dest)
        self.assertTrue(ok)
        self.assertIsNone(leader.db.escorting)

    def test_separated_escortee_dissolves_link(self):
        leader, source, dest, escortee = self._setup()
        escortee.location = _room()                    # they're gone
        ok = usher_escortee(leader, dest)
        self.assertTrue(ok)
        self.assertIsNone(leader.db.escorting)


class TestFollowCommands(TestCase):
    def _cmd(self, cls, caller, args=""):
        cmd = cls()
        cmd.caller = caller
        cmd.args = args
        return cmd

    def test_follow_sets_link(self):
        from commands.CmdFollow import CmdFollow
        room = _room()
        caller, target = _char(room), _char(room)
        target.get_sdesc = lambda: "a lean man"
        caller.search.return_value = target
        self._cmd(CmdFollow, caller, "lean man").func()
        self.assertIs(caller.db.following, target)
        self.assertIn("fall in behind", caller.msg.call_args.args[0])

    def test_cannot_follow_self(self):
        from commands.CmdFollow import CmdFollow
        caller = _char(_room())
        caller.search.return_value = caller
        self._cmd(CmdFollow, caller, "me").func()
        self.assertIsNone(caller.db.following)

    def test_stop_following_breaks_escort_of_me(self):
        from commands.CmdFollow import CmdStopFollowing
        room = _room()
        caller, leader = _char(room), _char(room)
        leader.db.escorting = caller
        room.contents = [caller, leader]
        self._cmd(CmdStopFollowing, caller).func()
        self.assertIsNone(leader.db.escorting)
        self.assertIn("break away", caller.msg.call_args.args[0])


class TestEscortCommand(TestCase):
    def _pair(self):
        room = _room()
        caller, target = _char(room), _char(room)
        target.get_sdesc = lambda: "a lean man"
        caller.search.return_value = target
        return caller, target

    def _run(self, caller):
        from commands.CmdFollow import CmdEscort
        cmd = CmdEscort()
        cmd.caller = caller
        cmd.args = "lean man"
        cmd.func()

    def test_trusted_escort_couples(self):
        caller, target = self._pair()
        with patch("world.consent.check_consent", return_value=True), \
                patch("world.consent.is_conscious", return_value=True):
            self._run(caller)
        self.assertIs(caller.db.escorting, target)

    def test_untrusting_conscious_target_refused(self):
        caller, target = self._pair()
        with patch("world.consent.check_consent", return_value=False), \
                patch("world.consent.is_conscious", return_value=True):
            self._run(caller)
        self.assertIsNone(caller.db.escorting)
        self.assertIn("won't be led", caller.msg.call_args.args[0])

    def test_unconscious_target_cannot_walk(self):
        caller, target = self._pair()
        with patch("world.consent.is_conscious", return_value=False):
            self._run(caller)
        self.assertIsNone(caller.db.escorting)
        self.assertIn("carry or drag", caller.msg.call_args.args[0])
