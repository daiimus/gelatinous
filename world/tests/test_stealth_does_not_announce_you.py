"""A hidden search stays hidden, and a refused sneak costs nothing
(#2562, #2563).

## #2562, superseded by #3769 (owner, 2026-10-25: "Search reveals")

#2562 found that a **hidden** character running `search` announced
themselves to observers who could not see them and stayed hidden, so
those observers could not target the person they had just been told
about. Its fix hid the line from them. The 2026-10-24 rulings resolve
the same contradiction the other way: every act a hidden character
announces reveals them, so `msg_room_identity` breaks the hide first
and the whole room, the formerly unaware included, reads the emergence
beat and then the search. The exclude list is the searcher alone.

## #2563 — the contest paid for a move that never happened

`sneak <exit>` hid you and rewrote every watcher's awareness *before*
attempting the move, then discovered whether the move was possible by
comparing locations afterwards — and returned with no rollback. A
refused traversal left you silently hidden, with every observer's
awareness already rolled and persisted, from an action that did not
happen.

The hide genuinely has to come first: witnesses in the room you are
*leaving* get their contest, which is how they keep track of your exit.
So the fix is to refuse early what can be refused early — a locked or
unusable exit is now caught by `access(caller, "traverse")` before
anything is rolled — and to put back the hidden flag when something
`access` cannot see refuses the move (combat, an aim-lock, a sky edge).

**Stated plainly, because it is a partial fix:** awareness stamps
already written cannot be unrolled. What this guarantees is that the
state a player can observe matches the action that failed, and that the
common refusal costs nothing at all.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdStealth import CmdSearch, CmdSneak
from world.stealth import ALERT, UNAWARE, get_awareness, set_awareness


class _StealthCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1


class TestASearchRevealsTheSearcher(_StealthCase):
    """#3769 (owner, 2026-10-25: "Search reveals"). The exclude list is
    read off the broadcast call because the end delivery is not
    observable in this harness; the reveal is read off the flag."""

    def exclude_list(self):
        with mock.patch("world.identity_utils.msg_room_identity") as say:
            self.call(CmdSearch(), "", caller=self.char1)
        self.assertTrue(say.call_args, "the search never broadcast")
        return list(say.call_args.kwargs.get("exclude") or [])

    def test_an_unaware_observer_is_told(self):
        self.char1.db.hidden = True
        set_awareness(self.char2, self.char1, UNAWARE)
        self.assertEqual(self.exclude_list(), [self.char1])

    def test_an_alert_observer_is_told(self):
        self.char1.db.hidden = True
        set_awareness(self.char2, self.char1, ALERT)
        self.assertEqual(self.exclude_list(), [self.char1])

    def test_a_hidden_searcher_is_revealed(self):
        self.char1.db.hidden = True
        set_awareness(self.char2, self.char1, UNAWARE)
        self.call(CmdSearch(), "", caller=self.char1)
        self.assertFalse(self.char1.db.hidden)

    def test_the_broadcast_is_an_act(self):
        """Default `acting`, so the announcer does the revealing."""
        with mock.patch("world.identity_utils.msg_room_identity") as say:
            self.call(CmdSearch(), "", caller=self.char1)
        self.assertNotIn("acting", say.call_args.kwargs)

    def test_the_search_still_runs(self):
        """Filtering the broadcast must not skip the sweep itself."""
        self.char1.db.hidden = True
        out = self.call(CmdSearch(), "", caller=self.char1)
        self.assertTrue(out.strip())


class TestARefusedSneakCostsNothing(_StealthCase):
    def blocked_exit(self):
        ex = create_object("typeclasses.exits.Exit", key="north",
                           location=self.room1, destination=self.room2)
        ex.locks.add("traverse:false()")
        return ex

    def open_exit(self):
        return create_object("typeclasses.exits.Exit", key="north",
                             location=self.room1, destination=self.room2)

    def test_a_locked_exit_does_not_hide_you(self):
        self.blocked_exit()
        self.call(CmdSneak(), "north", caller=self.char1)
        self.assertFalse(self.char1.db.hidden)

    def test_and_rolls_nobody_s_awareness(self):
        self.blocked_exit()
        self.call(CmdSneak(), "north", caller=self.char1)
        self.assertEqual(get_awareness(self.char2, self.char1), UNAWARE)

    def test_it_says_you_cannot_get_through(self):
        self.blocked_exit()
        out = self.call(CmdSneak(), "north", caller=self.char1)
        self.assertIn("can't get through", out)

    def test_an_open_exit_still_sneaks(self):
        self.open_exit()
        self.call(CmdSneak(), "north", caller=self.char1)
        self.assertIs(self.char1.location, self.room2)
        self.assertTrue(self.char1.db.hidden)

    def test_a_late_refusal_puts_the_flag_back(self):
        """Something `access` cannot see refuses the move."""
        self.open_exit()
        with mock.patch.object(type(self.char1), "execute_cmd",
                               return_value=None):
            self.call(CmdSneak(), "north", caller=self.char1)
        self.assertIs(self.char1.location, self.room1)
        self.assertFalse(self.char1.db.hidden)

    def test_someone_already_hidden_stays_hidden_on_refusal(self):
        """Only a hide THIS command performed is rolled back."""
        self.char1.db.hidden = True
        self.blocked_exit()
        self.call(CmdSneak(), "north", caller=self.char1)
        self.assertTrue(self.char1.db.hidden)


class TestASneakTellsTheBrainsThatCaughtIt(_StealthCase):
    """#2589 review: the room announces an arrival BEFORE the sneak's
    fresh contest in the new room, so an LLM brain is told with stale
    awareness and ignores it (`notice_presence_change` returns early
    while the mover is mid-sneak). After the contest, CmdSneak re-issues
    the notice to the observers who kept track, and to nobody else.

    `notice_presence_change` is duck-typed on the observer, so a
    recorder on char2 stands in for an LLM brain. The recorder notes
    whether the mover was still mid-sneak when each call came in."""

    def setUp(self):
        super().setUp()
        self.char2.location = self.room2
        create_object("typeclasses.exits.Exit", key="north",
                      location=self.room1, destination=self.room2)
        self.calls = []
        char1 = self.char1

        def notice(mover, entered):
            self.calls.append((mover, entered, bool(char1.ndb.sneaking)))
        self.char2.notice_presence_change = notice

    def after_contest(self):
        return [c for c in self.calls if not c[2]]

    def test_a_watcher_who_kept_track_is_told_after_the_contest(self):
        with mock.patch("world.stealth.contest", return_value=1):
            self.call(CmdSneak(), "north", caller=self.char1)
        self.assertEqual(get_awareness(self.char2, self.char1), ALERT)
        self.assertEqual(self.after_contest(), [(self.char1, True, False)])

    def test_a_watcher_who_lost_you_is_told_nothing(self):
        with mock.patch("world.stealth.contest", return_value=0):
            self.call(CmdSneak(), "north", caller=self.char1)
        self.assertEqual(get_awareness(self.char2, self.char1), UNAWARE)
        self.assertEqual(self.after_contest(), [])

    def test_the_room_s_own_notice_came_mid_sneak(self):
        """The control for the brain's early return: the room's hook
        fires while the mover is still mid-sneak."""
        with mock.patch("world.stealth.contest", return_value=0):
            self.call(CmdSneak(), "north", caller=self.char1)
        self.assertIn((self.char1, True, True), self.calls)
