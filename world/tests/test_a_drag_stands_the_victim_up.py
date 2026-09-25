"""A grapple-drag stands the victim up (#3663).

Both drag doors move the victim with hooks OFF (a channeling victim must
not be immune to a grapple, #2774), which skipped `at_post_move` and its
"moving puts you on your feet". A patient dragged out of the AutoDoc kept
`db.furniture` pointing at the pod: the street said "lying in an
autodoc.", `treatment_station` kept the pod's bonus, and since the pod is
a restraint device `is_restrained()` stayed True anywhere, so they could
be robbed uncontested until they typed `stand`.

The two doors share `drag_victim_to` now. These drive BOTH real doors
(`Exit.at_traverse`'s drag branch with a stand-in handler, and
`_do_advance_move`), not just the helper, plus the helper's own
refused-move guard. Controls against master fail on the posture.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdFurniture import CmdLie
from world.combat.constants import DB_IS_YIELDING, NDB_COMBAT_HANDLER
from world.consent import is_restrained
from world.medical.utils import treatment_station


class _PodPatient(EvenniaCommandTest):
    """char1 lies in an AutoDoc in room1; char2 has hold of them."""

    def setUp(self):
        super().setUp()
        self.patient, self.grappler = self.char1, self.char2
        self.pod = create_object("typeclasses.furniture.AutoDoc", key="autodoc",
                                 location=self.room1)
        self.call(CmdLie(), "autodoc", caller=self.patient)
        self.assertEqual(self.patient.db.furniture, self.pod)   # fixture
        self.assertTrue(is_restrained(self.patient))            # fixture

    def assertOnTheirFeet(self):
        # What the drag owns: the furniture half. Restraint by the GRAPPLE
        # itself is the grapple's business and ends with release; these
        # fixtures stand in for the handler, so `is_restrained` is not
        # asserted here (it would pass for the wrong reason).
        self.assertIsNone(self.patient.db.furniture)
        self.assertEqual(self.patient.db.posture, "standing")
        self.assertFalse(self.patient.temp_place)
        self.assertIsNone(treatment_station(self.patient))
        self.assertEqual(self.pod.occupants(), [], "the pod still shows them")


class TheWalkDoor(_PodPatient):
    """`Exit.at_traverse`: the grappler, yielding and unopposed, walks out."""

    def drag_out(self, *, resisted=False):
        handler = mock.MagicMock()
        handler.db.combatants = [
            {"char": self.grappler, DB_IS_YIELDING: True},
            {"char": self.patient, DB_IS_YIELDING: True},
        ]
        handler.get_grappling_obj.side_effect = (
            lambda entry: self.patient if entry["char"] is self.grappler else None)
        handler.get_target_obj.return_value = None
        setattr(self.grappler.ndb, NDB_COMBAT_HANDLER, handler)
        # `at_traverse` rolls the victim's RESIST first, then the drag.
        rolls = [999, 1] if resisted else [1, 999]
        with mock.patch("random.randint", side_effect=lambda a, b: rolls.pop(0)), \
             mock.patch("typeclasses.exits.msg_room_identity"), \
             mock.patch("typeclasses.exits.get_or_create_combat",
                        return_value=mock.MagicMock()), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"):
            self.exit.at_traverse(self.grappler, self.room2)

    def test_the_victim_arrives_on_their_feet(self):
        self.drag_out()
        self.assertEqual(self.patient.location, self.room2)
        self.assertOnTheirFeet()

    def test_control_a_resisted_drag_leaves_them_in_the_pod(self):
        self.drag_out(resisted=True)
        self.assertEqual(self.patient.location, self.room1)
        self.assertEqual(self.patient.db.furniture, self.pod)
        self.assertTrue(is_restrained(self.patient))


class TheAdvanceDoor(_PodPatient):
    """`_do_advance_move`: the grappler advances on someone next door."""

    def test_the_victim_arrives_on_their_feet(self):
        from world.combat.movement_resolution import _do_advance_move
        quarry = create_object("typeclasses.characters.Character", key="quarry",
                               location=self.room2)
        with mock.patch("world.combat.movement_resolution.msg_room_identity"):
            _do_advance_move(mock.MagicMock(), self.grappler, quarry, self.room2,
                             self.exit, self.patient, True, mock.MagicMock())
        self.assertEqual(self.patient.location, self.room2)
        self.assertOnTheirFeet()


class TheAdvanceDoorWhenTheGrapplerIsRefused(_PodPatient):
    """The walk door's #2594 guard, on the advance door: if the grappler's
    own hooked move is refused, the victim is not hauled off alone."""

    def test_the_victim_stays_put(self):
        from world.combat.movement_resolution import _do_advance_move
        quarry = create_object("typeclasses.characters.Character", key="quarry",
                               location=self.room2)
        with mock.patch("world.combat.movement_resolution.msg_room_identity"), \
             mock.patch.object(type(self.grappler), "at_pre_move", return_value=False):
            _do_advance_move(mock.MagicMock(), self.grappler, quarry, self.room2,
                             self.exit, self.patient, True, mock.MagicMock())
        self.assertEqual(self.grappler.location, self.room1)
        self.assertEqual(self.patient.location, self.room1)
        self.assertEqual(self.patient.db.furniture, self.pod)


class TheHelper(_PodPatient):

    def test_a_refused_move_is_not_a_move(self):
        from world.combat.grappling import drag_victim_to
        with mock.patch.object(type(self.patient), "move_to", return_value=False):
            self.assertFalse(drag_victim_to(self.patient, self.room2))
        self.assertEqual(self.patient.db.furniture, self.pod)

    def test_someone_already_standing_is_left_alone(self):
        from world.combat.grappling import drag_victim_to
        walker = create_object("typeclasses.characters.Character", key="walker",
                               location=self.room1)
        with mock.patch.object(type(walker), "_clear_posture") as clear:
            self.assertTrue(drag_victim_to(walker, self.room2))
        self.assertFalse(clear.called)
