"""`look <door>` from the corridor says whether the unit is taken (#3508).

Owner direction 2026-09-14: tenancy is pruned lazily, so a unit whose
tenant was destroyed by hand read as occupied until something asked
after it. Rather than an eager sweep, the state shows where players meet
it: the unit's corridor-side door ends its description with "Occupied.",
"Vacant." or "Being vacated." (the 48-hour relocation window), and that
look is itself the touch that prunes a dead tenancy.

Real objects: a cube with its registered door pair, tenants with real
sleeve ids (assigned at character creation), the rental module's own
claim and release. The look runs through Evennia's `look` command as
well as the door's own hook.
"""
from evennia import create_object
from evennia.commands.default.general import CmdLook
from evennia.utils.test_resources import EvenniaCommandTest

from world import rental


class _UnitCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.aisle = self.room1
        self.char1.location = self.aisle
        self.cube = create_object("typeclasses.rooms.Room", key="R1-01")
        self.cube.db.residence_building = "Queen of Cups"
        # the pair the rental build hangs: the aisle side is registered
        self.door = create_object("typeclasses.doors.DoorExit", key="west",
                                  location=self.aisle, destination=self.cube)
        self.inside = create_object("typeclasses.doors.DoorExit", key="east",
                                    location=self.cube, destination=self.aisle)
        self.cube.db.cube_door = self.door
        self.tenant = self.char2
        self.tenant.location = self.room2

    def look_door(self):
        return self.door.return_appearance(self.char1) or ""

    def status_words(self, text):
        return [w for w in ("Occupied.", "Vacant.", "Being vacated.") if w in text]


class TestTheFixture(_UnitCase):
    def test_the_cube_is_registered_and_claimable(self):
        self.assertEqual(rental.cube_door(self.cube), self.door)
        self.assertTrue(rental.is_free(self.cube))
        self.assertTrue(self.tenant.sleeve_uid)


class TestTheDoorSaysVacant(_UnitCase):
    def test_a_closed_door(self):
        self.assertIs(self.door.db.door_closed, True)
        self.assertEqual(self.status_words(self.look_door()), ["Vacant."])

    def test_an_open_door(self):
        self.door.db.door_closed = False
        self.assertEqual(self.status_words(self.look_door()), ["Vacant."])

    def test_through_the_look_command(self):
        out = self.call(CmdLook(), "west", caller=self.char1)
        self.assertIn("Vacant.", out)
        self.assertIn("It is closed.", out)


class TestTheDoorSaysOccupied(_UnitCase):
    def setUp(self):
        super().setUp()
        rental.claim(self.tenant, self.cube)

    def test_a_live_tenant(self):
        self.assertEqual(self.status_words(self.look_door()), ["Occupied."])

    def test_through_the_look_command(self):
        out = self.call(CmdLook(), "west", caller=self.char1)
        self.assertIn("Occupied.", out)

    def test_the_tenant_moving_out_leaves_it_being_vacated(self):
        rental.release_with_window(self.tenant, self.cube)
        self.assertFalse(rental.is_free(self.cube))
        self.assertEqual(self.status_words(self.look_door()), ["Being vacated."])

    def test_a_deleted_tenant_is_pruned_by_the_look(self):
        """The owner's case: the tenant destroyed by hand. The look is
        the touch; afterwards the record and the grant are gone."""
        self.assertTrue(self.door.db.access_grants)
        self.tenant.delete()
        self.assertEqual(self.status_words(self.look_door()), ["Vacant."])
        self.assertIsNone(self.cube.db.resident)
        self.assertIsNone(self.cube.db.resident_sleeve)
        self.assertEqual(rental._live_grants(self.door), [])
        self.assertTrue(rental.is_free(self.cube))


class TestOnlyTheRegisteredDoorSpeaks(_UnitCase):
    def test_the_door_inside_the_unit_says_nothing(self):
        self.assertEqual(self.status_words(
            self.inside.return_appearance(self.char1) or ""), [])

    def test_an_ordinary_door_says_nothing(self):
        plain = create_object("typeclasses.doors.DoorExit", key="south",
                              location=self.aisle, destination=self.room2)
        self.assertEqual(self.status_words(
            plain.return_appearance(self.char1) or ""), [])

    def test_a_blind_looker_is_not_told(self):
        state = self.char1.medical_state
        for _name, organ in state.organs.items():
            if (organ.data or {}).get("capacity") == "sight":
                organ.current_hp = 0
        self.char1.medical_state = state
        self.char1.save_medical_state()
        self.char1._medical_state = None
        from world.perception import can_perceive_sense
        self.assertFalse(can_perceive_sense(self.char1, "visual"))
        self.assertEqual(self.status_words(self.look_door()), [])
        self.assertIn("A door.", self.look_door())
