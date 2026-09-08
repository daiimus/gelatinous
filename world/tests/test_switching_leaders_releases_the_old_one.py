"""Changing who you follow tells the person you left (#2572).

`CmdFollow.func` established a new coupling with a bare re-assignment:

```python
caller.db.following = target
```

`sever_follow` is the ONLY other writer of that attribute in the tree,
and it is the thing that notifies both parties. So `follow bob` while
already following alice dropped alice's link silently — alice was never
told, and simply stopped having anyone arrive behind her. The state was
right; the person was not informed.

The room half is the same omission seen from outside. Every
ESTABLISHMENT is broadcast — the room reads *"{actor} falls in behind
{target}"* — and no RELEASE ever was. Bystanders watched couplings form
and never watched one end, so a follow a room had witnessed was, to
anyone standing in it, permanent.

The release broadcast lives in `sever_follow`, not in the commands,
because `stop following` and a leader switch both owe it and that is the
single door. It fires only while the two are still in the same room: a
follower who loses the trail is already a room away, and no room saw
them part — those paths pass `silent=True` and say something more
specific anyway.

MagicMock stand-ins, matching `test_movement_coupling.py`: the contract
here is which functions get called and who gets messaged, not database
behaviour. Note the two patch targets — `CmdFollow` binds
`msg_room_identity` at module scope, `sever_follow` imports it inside
the function, so patching one does not catch the other.
"""
from unittest import TestCase
from unittest.mock import MagicMock, patch


def _room(*contents):
    room = MagicMock()
    room.contents = list(contents)
    return room


def _char(location=None, sdesc="a lean man"):
    c = MagicMock()
    c.location = location
    c.db.following = None
    c.db.escorting = None
    # `msg_room_identity` substitutes the result of `get_display_name`
    # into the template with `str.replace`, so a bare MagicMock raises
    # `TypeError: replace() argument 2 must be str`. The existing
    # coupling tests set `get_sdesc` for the same reason.
    c.get_sdesc = lambda *a, **kw: sdesc
    c.get_display_name = lambda *a, **kw: sdesc
    return c


def _exit(destination, key="north"):
    """`_exit_to` matches on `.destination`, and `usher_escortee` pushes
    the escortee through `.key`."""
    ex = MagicMock()
    ex.destination = destination
    ex.key = key
    return ex


def _said(char):
    return " ".join(str(call.args[0]) for call in char.msg.call_args_list
                    if call.args)


class _FollowCase(TestCase):
    def _cmd(self, caller, args):
        from commands.CmdFollow import CmdFollow
        cmd = CmdFollow()
        cmd.caller = caller
        cmd.args = args
        return cmd

    def _switch(self):
        """Caller already follows `old`; `follow <new>` resolves to `new`."""
        room = _room()
        caller, old, new = (_char(room, "the caller"),
                            _char(room, "the old leader"),
                            _char(room, "the new leader"))
        room.contents = [caller, old, new]
        caller.db.following = old
        caller.search.return_value = new
        return caller, old, new


class TestSwitchingLeadersReleasesTheOldOne(_FollowCase):
    def test_the_old_leader_is_told(self):
        caller, old, new = self._switch()
        self._cmd(caller, "new").func()
        self.assertIn("stops following", _said(old))

    def test_the_switcher_is_told_they_left(self):
        caller, old, new = self._switch()
        self._cmd(caller, "new").func()
        self.assertIn("stop following", _said(caller))

    def test_the_new_link_is_established_anyway(self):
        caller, old, new = self._switch()
        self._cmd(caller, "new").func()
        self.assertIs(caller.db.following, new)

    def test_the_switcher_is_still_told_they_fell_in(self):
        caller, old, new = self._switch()
        self._cmd(caller, "new").func()
        self.assertIn("fall in behind", _said(caller))

    def test_it_goes_through_sever_follow(self):
        """The named door, not an equivalent inline assignment — that is
        the whole defect."""
        caller, old, new = self._switch()
        with patch("commands.CmdFollow.sever_follow") as severed:
            self._cmd(caller, "new").func()
        severed.assert_called_once_with(caller)


class TestFollowingFromNobodyIsUnchanged(_FollowCase):
    def _fresh(self):
        room = _room()
        caller, target = _char(room), _char(room)
        room.contents = [caller, target]
        caller.search.return_value = target
        return caller, target

    def test_no_spurious_release_line(self):
        caller, target = self._fresh()
        self._cmd(caller, "them").func()
        self.assertNotIn("stop following", _said(caller))

    def test_the_link_is_made(self):
        caller, target = self._fresh()
        self._cmd(caller, "them").func()
        self.assertIs(caller.db.following, target)

    def test_re_following_the_same_person_refuses(self):
        caller, target = self._fresh()
        caller.db.following = target
        self._cmd(caller, "them").func()
        self.assertIn("already following", _said(caller))

    def test_and_the_refusal_does_not_drop_the_link(self):
        """The equality check returns BEFORE the severance, so a no-op
        `follow` must not sever what it was reaffirming."""
        caller, target = self._fresh()
        caller.db.following = target
        self._cmd(caller, "them").func()
        self.assertIs(caller.db.following, target)


class TestTheRoomSeesTheRelease(TestCase):
    def _pair(self, same_room=True):
        room = _room()
        follower, leader = _char(room), _char(room if same_room else _room())
        room.contents = [follower, leader]
        follower.db.following = leader
        return follower, leader

    def _templates(self, sent):
        return " ".join(str(kw.get("template", "")) for kw in sent)

    def test_a_severance_is_broadcast(self):
        from world.movement_coupling import sever_follow
        follower, leader = self._pair()
        sent = []
        with patch("world.identity_utils.msg_room_identity",
                   side_effect=lambda **kw: sent.append(kw)):
            sever_follow(follower)
        self.assertIn("stops following", self._templates(sent))

    def test_the_two_parties_are_excluded_from_it(self):
        from world.movement_coupling import sever_follow
        follower, leader = self._pair()
        sent = []
        with patch("world.identity_utils.msg_room_identity",
                   side_effect=lambda **kw: sent.append(kw)):
            sever_follow(follower)
        self.assertEqual(set(sent[0]["exclude"]), {follower, leader})

    def test_a_silent_severance_stays_silent(self):
        from world.movement_coupling import sever_follow
        follower, leader = self._pair()
        sent = []
        with patch("world.identity_utils.msg_room_identity",
                   side_effect=lambda **kw: sent.append(kw)):
            sever_follow(follower, silent=True)
        self.assertEqual(sent, [])

    def test_a_parting_across_two_rooms_is_not_broadcast(self):
        from world.movement_coupling import sever_follow
        follower, leader = self._pair(same_room=False)
        sent = []
        with patch("world.identity_utils.msg_room_identity",
                   side_effect=lambda **kw: sent.append(kw)):
            sever_follow(follower)
        self.assertEqual(sent, [])

    def test_the_establishment_is_still_broadcast(self):
        from commands.CmdFollow import CmdFollow
        room = _room()
        caller, target = _char(room), _char(room)
        room.contents = [caller, target]
        caller.search.return_value = target
        cmd = CmdFollow()
        cmd.caller, cmd.args = caller, "them"
        sent = []
        with patch("commands.CmdFollow.msg_room_identity",
                   side_effect=lambda **kw: sent.append(kw)):
            cmd.func()
        self.assertIn("falls in behind", self._templates(sent))


class TestMutualEscortCannotRecurse(TestCase):
    """A escorting B while B escorts A made ANY movement recurse until
    the interpreter stack blew (#2454).

    A's `at_pre_move` ushers B; B's `at_pre_move` ushers A; neither can
    reach `move_to`'s actual relocation until its escortee has already
    moved, so no state changes between iterations and every early-out
    in `usher_escortee` is false. The player got a RecursionError
    traceback and BOTH characters were wedged, because every later move
    by either re-triggered it.

    The follow direction is safe and the author knew it —
    `bring_followers` runs from `at_post_move` AFTER the leader has
    arrived and only moves followers still in the SOURCE room, so each
    hop empties that room. Escort is the exact inverse and never got
    the equivalent reasoning.

    Reachable by any two players with mutual `escort` trust: the
    command guarded `caller.db.escorting == target` and the
    follow-inverse, never `target.db.escorting == caller`. Measured
    live: 0 mutual pairs today — armed, not fired.
    """

    def _pair(self):
        dest = _room()
        room = _room()
        ex = MagicMock()
        ex.destination = dest
        ex.key = "north"
        room.contents = [ex]
        a, b = _char(room), _char(room)
        room.contents += [a, b]
        a.db.escorting = b
        b.db.escorting = a
        return a, b, dest, ex

    def test_the_reentrant_usher_does_not_push_the_escortee_again(self):
        """Asserting only the RETURN VALUE passed against the unfixed
        tree too: without the guard the call still returns False,
        because the mock escortee never actually arrives and the
        "the way refuses them" branch answers False as well. What
        discriminates is whether the escortee is pushed through the
        door a SECOND time."""
        from world.movement_coupling import usher_escortee
        a, b, dest, _ex = self._pair()
        setattr(a.ndb, "ushering_escortee", True)   # already in flight
        # Consent has to pass or the function returns True from an
        # EARLIER early-out and the guard is never reached.
        with patch("world.consent.check_consent", return_value=True), \
                patch("world.consent.is_conscious", return_value=True):
            result = usher_escortee(a, dest)
        b.execute_cmd.assert_not_called()
        self.assertFalse(result)

    def test_a_real_mutual_pair_does_not_blow_the_stack(self):
        """The defect itself, end to end.

        `_walker` relocates directly and never routes through
        `at_pre_move`, so it cannot reproduce the loop. Production
        wires it as `at_pre_move -> usher_escortee -> escortee.
        execute_cmd -> at_pre_move ...`, so the stand-in has to make
        that same hop: usher first, then move. Without the guard that
        recurses until the interpreter stack blows.
        """
        from world.movement_coupling import usher_escortee
        dest = _room()
        room = _room()
        ex = _exit(dest)
        a, b = _char(room), _char(room)
        a.get_display_name = lambda *x, **k: "the other one"
        b.get_display_name = lambda *x, **k: "the other one"
        room.contents = [ex, a, b]
        a.db.escorting = b
        b.db.escorting = a

        def _move(who):
            def _go(_cmd):
                # what `at_pre_move` does before relocating
                if usher_escortee(who, dest) is False:
                    return
                who.location = dest
            return _go

        a.execute_cmd.side_effect = _move(a)
        b.execute_cmd.side_effect = _move(b)

        with patch("world.consent.check_consent", return_value=True), \
                patch("world.consent.is_conscious", return_value=True):
            try:
                usher_escortee(a, dest)
            except RecursionError:
                self.fail("mutual escort recursed until the stack blew")

    def test_an_ordinary_escort_is_not_refused(self):
        """The guard must be a re-entrancy check, not a ban on escorts.
        `ndb` returns None for a missing key and a MagicMock
        auto-creates a truthy one, so this only holds with a strict
        `is True`."""
        from world.movement_coupling import usher_escortee
        a, _b, dest, _ex = self._pair()
        with patch("world.consent.check_consent", return_value=True), \
                patch("world.consent.is_conscious", return_value=True):
            usher_escortee(a, dest)   # must not raise RecursionError

    def test_the_flag_does_not_leak_after_the_call(self):
        from world.movement_coupling import usher_escortee
        a, _b, dest, _ex = self._pair()
        with patch("world.consent.check_consent", return_value=True), \
                patch("world.consent.is_conscious", return_value=True):
            usher_escortee(a, dest)
        self.assertIsNot(getattr(a.ndb, "ushering_escortee", None), True)

    def test_the_command_refuses_to_arm_it(self):
        from commands.CmdFollow import CmdEscort
        room = _room()
        caller, target = _char(room), _char(room)
        room.contents = [caller, target]
        target.db.escorting = caller          # they already lead me
        caller.search.return_value = target
        cmd = CmdEscort()
        cmd.caller, cmd.args = caller, "them"
        cmd.func()
        self.assertIsNot(caller.db.escorting, target)
        self.assertIn("lead each other", _said(caller))
