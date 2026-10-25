"""#3773 (slice four of #3659): three places that still acted on a hidden
person or thing as if it were visible.

1. A hidden leader who sneaks out leaves behind every follower who lost
   track of them, silently: no line to the follower, none to the room.
   Owner: "The onus is on them to 'look' and notice someone is gone."
   A follower who kept track (ALERT) still trails.
2. Walking into a room no longer refreshes your recognition memory of
   anyone you cannot perceive.
3. A stashed item that falls through open air lands in plain sight.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaTest

from world.gravity import _land_item, _strand
from world.movement_coupling import bring_followers
from world.perception import can_perceive
from world.stealth import ALERT, UNAWARE, set_awareness


# --------------------------------------------------------------------------
# 1. The follow coupling, with the same MagicMock stand-ins as
#    test_movement_coupling.py: the contract is who moves and who is told.
# --------------------------------------------------------------------------

def _room(*contents):
    room = MagicMock()
    room.contents = list(contents)
    return room


def _exit(destination, key="north"):
    ex = MagicMock()
    ex.destination = destination
    ex.key = key
    return ex


def _walker(location, leader):
    c = MagicMock()
    c.location = location
    c.db.following = leader
    c.db.escorting = None

    def _go(cmd):
        for obj in c.location.contents:
            if getattr(obj, "key", None) == cmd and hasattr(obj, "destination"):
                c.location = obj.destination
                return
    c.execute_cmd.side_effect = _go
    return c


class _Coupling(TestCase):
    def scene(self, hidden):
        dest = _room()
        leader = MagicMock()
        leader.location = dest                      # leader already arrived
        leader.db.hidden = hidden
        source = _room(_exit(dest))
        return leader, source, dest

    def follower(self, source, leader):
        f = _walker(source, leader)
        source.contents.append(f)
        return f


class TestAHiddenLeaderLeavesTheLostBehind(_Coupling):
    def run_with(self, perceive):
        leader, source, dest = self.scene(hidden=True)
        follower = self.follower(source, leader)
        with patch("world.perception.can_perceive", perceive):
            bring_followers(leader, source)
        return leader, source, dest, follower

    def test_a_follower_who_lost_track_does_not_move(self):
        _, source, _, follower = self.run_with(lambda f, l: False)
        follower.execute_cmd.assert_not_called()
        self.assertIs(follower.location, source)

    def test_the_link_is_gone(self):
        _, _, _, follower = self.run_with(lambda f, l: False)
        self.assertIsNone(follower.db.following)

    def test_nobody_is_told(self):
        """Not the follower, not the leader, not the room: the sever is the
        silent one, and silent returns before every message."""
        leader, source, dest, follower = self.run_with(lambda f, l: False)
        follower.msg.assert_not_called()
        leader.msg.assert_not_called()
        source.msg_contents.assert_not_called()
        dest.msg_contents.assert_not_called()

    def test_a_follower_who_kept_track_still_trails(self):
        _, _, dest, follower = self.run_with(lambda f, l: True)
        follower.execute_cmd.assert_called_once_with("north")
        self.assertIs(follower.location, dest)
        self.assertIsNotNone(follower.db.following)

    def test_each_follower_is_judged_alone(self):
        leader, source, dest = self.scene(hidden=True)
        lost = self.follower(source, leader)
        kept = self.follower(source, leader)
        with patch("world.perception.can_perceive",
                   lambda f, l: f is kept):
            bring_followers(leader, source)
        self.assertIs(lost.location, source)
        self.assertIsNone(lost.db.following)
        self.assertIs(kept.location, dest)
        self.assertIs(kept.db.following, leader)


class TestAVisibleLeaderIsUnchanged(_Coupling):
    def test_followers_trail_without_consulting_perception(self):
        leader, source, dest = self.scene(hidden=False)
        follower = self.follower(source, leader)
        perceive = MagicMock(return_value=False)
        with patch("world.perception.can_perceive", perceive):
            bring_followers(leader, source)
        perceive.assert_not_called()
        self.assertIs(follower.location, dest)
        self.assertIs(follower.db.following, leader)

    def test_a_truthy_flag_is_not_hidden(self):
        """Strict `is True`, as every other reader of `db.hidden`."""
        leader, source, dest = self.scene(hidden=1)
        follower = self.follower(source, leader)
        with patch("world.perception.can_perceive", lambda f, l: False):
            bring_followers(leader, source)
        self.assertIs(follower.location, dest)


# --------------------------------------------------------------------------
# 2. Recognition recency on arrival, with real characters: the gate is the
#    one `look` uses, so a kept-track observer still refreshes.
# --------------------------------------------------------------------------

class TestArrivingDoesNotRememberTheUnseen(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.char1.recognition_memory = {"someone": {"name": "Someone"}}

    def refresh(self):
        with patch("world.identity.bump_recognition_recency") as bump:
            self.char1._refresh_recognition_recency()
        return [call.args[1] for call in bump.call_args_list]

    def test_a_visible_person_is_refreshed(self):
        """Control: the pass still runs for people you can see."""
        self.assertIn(self.char2, self.refresh())

    def test_a_hidden_person_you_lost_is_not(self):
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, UNAWARE)
        self.assertFalse(can_perceive(self.char1, self.char2), "premise")
        self.assertNotIn(self.char2, self.refresh())

    def test_a_hidden_person_you_kept_track_of_is(self):
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, ALERT)
        self.assertTrue(can_perceive(self.char1, self.char2), "premise")
        self.assertIn(self.char2, self.refresh())


class TestAHiderSpottedOnArrivalIsMarkedSeen(EvenniaTest):
    """The recency pass runs after the arrival's glances. Pinned on the
    path where the arrival look itself does not run (the room refuses
    view), so only the passive tier in at_post_move can make the spot."""

    def setUp(self):
        super().setUp()
        self.char1.location = self.room2
        self.char2.location = self.room2
        self.char1.recognition_memory = {"someone": {"name": "Someone"}}
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, UNAWARE)

    def arrive(self, glance):
        with patch.object(type(self.room2), "access", return_value=False), \
                patch("world.stealth.passive_check", glance), \
                patch("world.identity.bump_recognition_recency") as bump:
            self.char1.at_post_move(None)
        return [call.args[1] for call in bump.call_args_list]

    def test_a_spot_on_the_way_in_marks_them_seen(self):
        def spot(observer, hider):
            set_awareness(observer, hider, ALERT)
        self.assertIn(self.char2, self.arrive(spot))

    def test_a_missed_glance_leaves_no_mark(self):
        self.assertNotIn(self.char2, self.arrive(lambda o, h: None))


# --------------------------------------------------------------------------
# 3. A stashed item whose fall ends: landed, or stranded in open air.
# --------------------------------------------------------------------------

class TestAFallenStashLandsInPlainSight(EvenniaTest):
    def land(self, stashed):
        item = self.obj1
        if stashed:
            item.db.hidden = True
            item.db.stash_roll = 17
        item.location = self.room1
        with patch("world.gravity.msg_room_identity") as announce:
            _land_item(item, self.room1, 2)
        return item, announce

    def test_the_stash_flag_is_gone(self):
        item, _ = self.land(stashed=True)
        self.assertIsNone(item.db.hidden)

    def test_the_hiders_difficulty_is_gone_too(self):
        """Otherwise the landing room has a hiding place nobody worked for."""
        item, _ = self.land(stashed=True)
        self.assertIsNone(item.db.stash_roll)

    def test_it_can_be_seen_where_it_fell(self):
        item, _ = self.land(stashed=True)
        self.assertTrue(can_perceive(self.char1, item))

    def test_the_clatter_is_still_announced(self):
        _, announce = self.land(stashed=True)
        announce.assert_called_once()
        self.assertIn("clatter", announce.call_args.kwargs["template"])

    def test_an_ordinary_item_lands_as_before(self):
        item, announce = self.land(stashed=False)
        self.assertIsNone(item.db.hidden)
        announce.assert_called_once()


class TestAStrandedStashIsInPlainSightToo(EvenniaTest):
    """`_strand` ends a fall as `_land_item` does and announces the thing
    to the cell; it forgets the stash the same way."""

    def strand(self, stashed):
        item = self.obj1
        if stashed:
            item.db.hidden = True
            item.db.stash_roll = 17
        item.location = self.room2
        with patch("world.gravity.msg_room_identity") as announce:
            _strand(item, {}, self.room2, "no_down")
        return item, announce

    def test_the_stash_flag_is_gone(self):
        item, _ = self.strand(stashed=True)
        self.assertIsNone(item.db.hidden)
        self.assertIsNone(item.db.stash_roll)

    def test_it_is_still_announced(self):
        _, announce = self.strand(stashed=True)
        announce.assert_called_once()
        self.assertIn("comes to rest", announce.call_args.kwargs["template"])

    def test_a_stranded_person_is_not_touched(self):
        """Only things: a hidden body's concealment is break_stealth's,
        not gravity's."""
        self.char2.location = self.room2
        self.char2.db.hidden = True
        with patch("world.gravity.msg_room_identity"):
            _strand(self.char2, {}, self.room2, "no_down")
        self.assertIs(self.char2.db.hidden, True)
