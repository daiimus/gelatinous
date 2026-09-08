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
