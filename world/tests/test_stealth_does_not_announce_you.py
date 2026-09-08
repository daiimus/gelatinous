"""A hidden search stays hidden, and a refused sneak costs nothing
(#2562, #2563).

## #2562 — the search that announced you to people who can't see you

`msg_room_identity` does **no** perception filtering. It walks
`location.contents`, skips the exclude set, and messages everyone else.
The `search` broadcast excluded only the actor.

So a **hidden** character running `search` announced themselves to the
very observers who cannot see them — and stayed hidden afterwards, so
those same observers still could not target, or even list, the person
they had just been told about.

`is_hidden_from` is the display gate the rest of the codebase uses for
this question. `CmdCommunication` filters a whisper's bystanders on it,
because a whisper is a visual event. So is a search.

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


class TestAHiddenSearchIsNotAnnounced(_StealthCase):
    """Asserted on the EXCLUDE LIST handed to the broadcast, because the
    end delivery is not observable in this harness.

    `msg_room_identity` has a session gate — it skips observers with no
    connected session, deliberately (#462: per-observer name resolution
    is the most expensive render in the game, and messages to
    session-less objects are discarded by Evennia anyway). Harness
    characters other than the caller have no session, so a
    hand-patched `.msg` on them never fires. Two probes tonight failed
    that way before I read the gate.

    Patched on `world.identity_utils`, not on `commands.CmdStealth` —
    the import is inside the function, so the module attribute is the
    one that resolves at call time.
    """

    def exclude_list(self):
        with mock.patch("world.identity_utils.msg_room_identity") as say:
            self.call(CmdSearch(), "", caller=self.char1)
        self.assertTrue(say.call_args, "the search never broadcast")
        return list(say.call_args.kwargs.get("exclude") or [])

    def test_an_unaware_observer_is_excluded(self):
        self.char1.db.hidden = True
        set_awareness(self.char2, self.char1, UNAWARE)
        self.assertIn(self.char2, self.exclude_list())

    def test_an_alert_observer_is_not(self):
        self.char1.db.hidden = True
        set_awareness(self.char2, self.char1, ALERT)
        self.assertNotIn(self.char2, self.exclude_list())

    def test_an_unhidden_searcher_excludes_only_themselves(self):
        self.char1.db.hidden = False
        self.assertEqual(self.exclude_list(), [self.char1])

    def test_the_searcher_is_always_excluded(self):
        self.char1.db.hidden = True
        self.assertIn(self.char1, self.exclude_list())

    def test_the_gate_is_the_shared_one(self):
        """`is_hidden_from` is what `CmdCommunication` filters a
        whisper's bystanders on — same question, same answer."""
        from world.stealth import is_hidden_from
        self.char1.db.hidden = True
        set_awareness(self.char2, self.char1, UNAWARE)
        self.assertTrue(is_hidden_from(self.char1, self.char2))
        set_awareness(self.char2, self.char1, ALERT)
        self.assertFalse(is_hidden_from(self.char1, self.char2))

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
