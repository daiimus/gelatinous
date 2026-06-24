"""Furniture & posture (FURNITURE_AND_POSTURE).

The Furniture base (occupancy/capacity/postures) and the sit/lie/stand verbs:
posture is recorded on the character, surfaced via temp_place, capacity is
enforced, the wrong posture is refused, and moving auto-stands you.
"""

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from commands.CmdFurniture import CmdSit, CmdLie, CmdStand
from typeclasses.furniture import AutoDoc, Furniture


def _char(location, key="Tester"):
    """A game-typeclass character (BaseEvenniaTest's default chars are vanilla
    DefaultCharacters, which lack our posture hooks)."""
    return create_object("typeclasses.characters.Character", key=key,
                         location=location)


def _run(char, cmdcls, args=""):
    """Drive a posture command directly (bypasses cmdset routing, which needs a
    puppeting session; the verbs are registered in CMDSET_CHARACTER for play)."""
    cmd = cmdcls()
    cmd.caller = char
    cmd.obj = char
    cmd.args = args
    cmd.cmdstring = cmdcls.key
    cmd.raw_string = f"{cmdcls.key} {args}".strip()
    cmd.func()


class TestFurnitureModel(BaseEvenniaTest):
    """The derived-occupancy + posture/capacity model on the typeclass."""

    def setUp(self):
        super().setUp()
        self.stool = create_object(Furniture, key="bar stool",
                                   location=self.room1)
        self.pod = create_object(AutoDoc, key="autodoc", location=self.room1)

    def test_defaults(self):
        self.assertEqual(self.stool.db.postures, ("sitting",))
        self.assertEqual(self.stool.db.preposition, "on")
        self.assertEqual(self.pod.db.postures, ("lying",))
        self.assertEqual(self.pod.db.preposition, "in")
        self.assertTrue(self.pod.db.is_medical)

    def test_allows(self):
        self.assertTrue(self.stool.allows("sitting"))
        self.assertFalse(self.stool.allows("lying"))
        self.assertTrue(self.pod.allows("lying"))

    def test_occupancy_is_derived(self):
        sitter = _char(self.room1)
        self.assertEqual(self.stool.occupants(), [])
        sitter.db.furniture = self.stool
        self.assertIn(sitter, self.stool.occupants())
        self.assertTrue(self.stool.is_full())   # capacity 1
        sitter.db.furniture = None
        self.assertEqual(self.stool.occupants(), [])


class TestPostureCommands(BaseEvenniaTest):
    """sit / lie / stand and the auto-stand-on-move hook."""

    def setUp(self):
        super().setUp()
        self.stool = create_object(Furniture, key="bar stool",
                                   aliases=["stool"], location=self.room1)
        self.pod = create_object(AutoDoc, key="autodoc",
                                 aliases=["pod"], location=self.room1)
        self.me = _char(self.room1, key="Sitter")

    def test_sit_sets_posture_and_placement(self):
        _run(self.me, CmdSit, "on stool")
        self.assertEqual(self.me.db.posture, "sitting")
        self.assertEqual(self.me.db.furniture, self.stool)
        self.assertIn("sitting on a bar stool", self.me.temp_place)

    def test_lie_in_autodoc(self):
        _run(self.me, CmdLie, "in autodoc")
        self.assertEqual(self.me.db.posture, "lying")
        self.assertEqual(self.me.db.furniture, self.pod)
        self.assertIn("lying in an autodoc", self.me.temp_place)

    def test_cannot_lie_on_a_stool(self):
        _run(self.me, CmdLie, "on stool")
        self.assertNotEqual(self.me.db.posture, "lying")
        self.assertIsNone(self.me.db.furniture)

    def test_capacity_blocks_second_occupant(self):
        _run(self.me, CmdSit, "on stool")
        other = _char(self.room1, key="Other")
        _run(other, CmdSit, "on stool")
        self.assertIsNone(other.db.furniture)   # stool was full

    def test_stand_clears_posture(self):
        _run(self.me, CmdSit, "on stool")
        _run(self.me, CmdStand)
        self.assertEqual(self.me.db.posture, "standing")
        self.assertIsNone(self.me.db.furniture)
        self.assertEqual(self.me.temp_place, "")

    def test_moving_auto_stands(self):
        _run(self.me, CmdSit, "on stool")
        self.me.move_to(self.room2, quiet=True)
        self.assertEqual(self.me.db.posture, "standing")
        self.assertIsNone(self.me.db.furniture)

    def test_sit_with_no_target_takes_nearest_seat(self):
        _run(self.me, CmdSit)
        self.assertEqual(self.me.db.furniture, self.stool)


class TestAutoDocApparatus(BaseEvenniaTest):
    """The AutoDoc as a treatment station: it floors the kit rating with its own
    supplies and adds a bonus to the treatment roll for a patient lying in it."""

    def setUp(self):
        super().setUp()
        self.pod = create_object(AutoDoc, key="autodoc", location=self.room1)
        self.patient = _char(self.room1, key="Patient")
        self.medic = _char(self.room1, key="Medic")

    def test_station_detected_only_when_lying_on_a_medical_one(self):
        from world.medical.utils import treatment_station
        self.assertIsNone(treatment_station(self.patient))
        self.patient.db.furniture = self.pod
        self.assertEqual(treatment_station(self.patient), self.pod)

    def test_live_treatment_path_gets_station_bonus(self):
        # The WIRED path: calculate_treatment_success, called by apply/inject.
        from unittest.mock import MagicMock
        from world.medical.utils import calculate_treatment_success
        item = MagicMock()
        item.attributes.get.return_value = {"bleeding": 5}
        self.medic.db.intellect = 3
        self.patient.db.furniture = self.pod
        res = calculate_treatment_success(item, self.medic, self.patient, "bleeding")
        self.assertEqual(res["station_bonus"], 3)
        self.assertGreaterEqual(res["total"], res["roll"] + res["medical_skill"] + 3)

    def test_no_station_no_bonus(self):
        from unittest.mock import MagicMock
        from world.medical.utils import calculate_treatment_success
        item = MagicMock()
        item.attributes.get.return_value = {"bleeding": 5}
        self.medic.db.intellect = 3
        res = calculate_treatment_success(item, self.medic, self.patient, "bleeding")
        self.assertEqual(res["station_bonus"], 0)   # patient not on the pod

    def test_wound_care_roll_also_gets_station_bonus(self):
        # The OTHER live treatment path (treatments.roll_treatment, via
        # apply_wound_care) gets the AutoDoc bonus too.
        from world.medical.treatments import roll_treatment
        self.patient.db.furniture = self.pod
        r = roll_treatment(self.medic, target_difficulty=10, item_rating=0,
                           target=self.patient)
        self.assertEqual(r["station_bonus"], 3)


class TestFurnitureIntegration(BaseEvenniaTest):
    """An @integrate Furniture (a fixed AutoDoc) is woven into the room desc and
    NOT listed as a loose object."""

    def test_integrated_autodoc_woven_not_listed(self):
        room = create_object("typeclasses.rooms.Room", key="op")
        pod = create_object(AutoDoc, key="autodoc", location=room)
        pod.db.integrate = True
        pod.db.integration_fallback = "An autodoc squats at the center of the room."
        looker = _char(room)
        self.assertNotIn("autodoc", room.get_display_things(looker))
        self.assertIn("squats at the center",
                      room.get_integrated_objects_content(looker))


class TestBarSeating(BaseEvenniaTest):
    """The bar IS the seating — `sit at bar` fills one of its slots; no loose
    stool objects clutter the room."""

    def test_bar_is_sittable_capacity_ten(self):
        from typeclasses.bar import BarCounter, BAR_STOOL_COUNT
        from typeclasses.furniture import Seating
        bar = create_object(BarCounter, key="bar", location=self.room1)
        self.assertIsInstance(bar, Seating)
        self.assertTrue(bar.allows("sitting"))
        self.assertEqual(bar.db.capacity, BAR_STOOL_COUNT)
        # no loose stool objects spawned into the room
        self.assertEqual(
            [o for o in self.room1.contents if isinstance(o, Furniture)], [])

    def test_many_sit_at_the_bar(self):
        from typeclasses.bar import BarCounter
        bar = create_object(BarCounter, key="bar", location=self.room1)
        sitters = [_char(self.room1, key=f"P{i}") for i in range(3)]
        for s in sitters:
            _run(s, CmdSit, "at bar")
        # all seated, all on the one fixture (the bar), filling its slots
        self.assertTrue(all(s.db.furniture == bar for s in sitters))
        self.assertEqual(len(bar.occupants()), 3)
