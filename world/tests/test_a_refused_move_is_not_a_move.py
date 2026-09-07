"""A refused move is not a traversal (#2594).

`Exit.at_traverse` called `super().at_traverse(...)` and never checked
whether the move happened. Evennia's hook returns **None on both success
and failure** — it branches internally on `move_to` and neither branch
returns anything — so every post-move consequence fired regardless:

* `temp_place` was wiped, clearing a posture the character still holds
* `check_rigged_grenade` **detonated a trap in the room the player never
  left**
* on the drag path, the victim was teleported alone into a room the
  grappler never reached

**Refusal is designed behaviour, not an edge case.**
`Character.at_pre_move` refuses while channeling —
CHANNELED_ACTIONS_SPEC §2.2, *"channels prevent movement; leaving
requires an explicit `stop`"* — and a bounced escortee refuses too.
Graffiti and breach both open channels, and **surgery became one in
#2926**, so this now fires whenever a surgeon tries to walk out of an
operation.

The only way a subclass can know is to re-read the location, which is
what `_traverse` does. Failure is "the location did not change", which
is exactly what `move_to` leaves behind when `at_pre_move` returns False
— it bails before touching the location.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest


class _ExitCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1

    def refuse_movement(self):
        """The real refusal path: `at_pre_move` returns False."""
        return mock.patch.object(type(self.char1), "at_pre_move",
                                 return_value=False)


class TestEvenniaTellsYouNothing(EvenniaTest):
    """The premise, read off the installed Evennia — if a future version
    starts returning a result, this fix is redundant and should say so."""

    def test_at_traverse_has_no_return(self):
        import inspect

        from evennia.objects.objects import DefaultExit
        src = inspect.getsource(DefaultExit.at_traverse)
        body = [ln.strip() for ln in src.splitlines()]
        self.assertFalse([ln for ln in body if ln.startswith("return ")],
                         "at_traverse now returns something")

    def test_it_branches_on_move_to(self):
        import inspect

        from evennia.objects.objects import DefaultExit
        self.assertIn("move_to(",
                      inspect.getsource(DefaultExit.at_traverse))


class TestARefusedMoveStaysPut(_ExitCase):
    def test_the_character_does_not_move(self):
        with self.refuse_movement():
            self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_temp_place_is_not_wiped(self):
        """It describes a posture the character still holds."""
        self.char1.temp_place = "sitting on a stool."
        with self.refuse_movement():
            self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.temp_place, "sitting on a stool.")

    def test_no_rigged_grenade_is_triggered(self):
        with mock.patch("commands.explosion_utils.check_rigged_grenade") as rig:
            with self.refuse_movement():
                self.exit.at_traverse(self.char1, self.room2)
        rig.assert_not_called()

    def test_no_auto_defuse_is_offered(self):
        with mock.patch("commands.explosion_utils.check_auto_defuse") as fuse:
            with self.refuse_movement():
                self.exit.at_traverse(self.char1, self.room2)
        fuse.assert_not_called()


class TestASuccessfulMoveStillDoesEverything(_ExitCase):
    """The fix must gate the consequences on the move, not remove
    them."""

    def test_the_character_moves(self):
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_temp_place_is_wiped(self):
        self.char1.temp_place = "sitting on a stool."
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.temp_place, "")

    def test_the_rigged_grenade_check_runs(self):
        with mock.patch("commands.explosion_utils.check_rigged_grenade") as rig:
            self.exit.at_traverse(self.char1, self.room2)
        rig.assert_called_once()

    def test_the_auto_defuse_check_runs(self):
        with mock.patch("commands.explosion_utils.check_auto_defuse") as fuse:
            self.exit.at_traverse(self.char1, self.room2)
        fuse.assert_called_once()


class TestTheHelperReportsHonestly(_ExitCase):
    def test_it_reports_true_on_a_real_move(self):
        self.assertTrue(self.exit._traverse(self.char1, self.room2))

    def test_it_reports_false_on_a_refusal(self):
        with self.refuse_movement():
            self.assertFalse(self.exit._traverse(self.char1, self.room2))


class TestChannelingIsTheLiveRefusal(_ExitCase):
    """Not a hypothetical: this is the route the spec mandates, and
    surgery joined it in #2926."""

    def test_a_channeling_character_cannot_traverse(self):
        from world.channeled import begin_channel
        self.assertTrue(begin_channel(
            self.char1, 30, tell="working",
            on_complete=lambda: None, on_interrupt=lambda f: None,
            key="operating"), "the channel did not open")
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_and_keeps_their_posture(self):
        from world.channeled import begin_channel
        self.char1.temp_place = "kneeling over a patient."
        self.assertTrue(begin_channel(
            self.char1, 30, tell="working",
            on_complete=lambda: None, on_interrupt=lambda f: None,
            key="operating"), "the channel did not open")
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.temp_place, "kneeling over a patient.")
