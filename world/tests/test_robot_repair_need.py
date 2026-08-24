"""A damaged unit has somewhere to go (#2262).

The robot profile was `charge`, `maintenance`, `safety`. No `health` —
and `health` is what gives humans the `clinic` shape where the walking
wounded self-deliver. So a secbot could take a shotgun blast, keep
patrolling on a wrecked chassis, and turn up at the bench a week later
for a ROUTINE SERVICE. The wear timer was the only thing that ever
brought one in, and wear is not damage.

Same need and same shape as a person now — but a different door. A
bleeding colonist must not queue at the service rack, and a leaking
unit must not be booked into the operating theatre.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import actions, needs as needs_mod


class TestDamageIsNotWear(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.bot = self.char1
        self.bot.db.species = "robot"

    def test_a_unit_now_has_a_damage_need(self):
        self.assertIn("health", needs_mod.profile_of(self.bot))

    def test_it_is_derived_from_the_body_not_a_timer(self):
        """Same compute-on-read the walking wounded use — no snapshot,
        no decay, and treatment lowers it by actually healing."""
        self.bot.db.medical_state = {"conditions": [{"type": "bleeding"},
                                                    {"type": "fracture"}]}
        self.assertGreater(needs_mod.pressure(self.bot, "health"), 0.4)

    def test_an_intact_unit_wants_nothing(self):
        self.bot.db.medical_state = {"conditions": []}
        self.assertEqual(needs_mod.pressure(self.bot, "health"), 0.0)

    def test_maintenance_is_still_a_separate_timer(self):
        """Wear and damage are different needs and must stay so."""
        profile = needs_mod.profile_of(self.bot)
        self.assertIn("maintenance", profile)
        self.assertNotEqual(profile["health"], profile["maintenance"])


class TestDifferentDoors(EvenniaCommandTest):
    def test_a_machine_looks_for_repair(self):
        self.char1.db.species = "robot"
        self.assertEqual(needs_mod.clinic_service(self.char1), "repair")

    def test_a_person_looks_for_treatment(self):
        self.char1.db.species = "human"
        self.assertEqual(needs_mod.clinic_service(self.char1), "treatment")

    def test_a_synthetic_still_sees_a_doctor(self):
        """Organic-presenting and people-shaped: the human kit is coarse
        rather than wrong, and its own tier comes later."""
        self.char1.db.species = "synthetic_humanoid"
        self.assertEqual(needs_mod.clinic_service(self.char1), "treatment")

    def test_the_wounded_are_sent_to_their_own_door(self):
        self.char1.db.species = "robot"
        self.char1.db.medical_state = {"conditions": [{"type": "bleeding"}]}
        asked = []
        with mock.patch.object(actions, "_advertisers",
                               side_effect=lambda s, need, **kw: asked.append(need) or []):
            actions.plan_for(self.char1, "health")
        self.assertEqual(asked, ["repair"])

    def test_a_person_is_sent_to_the_clinic(self):
        self.char1.db.species = "human"
        self.char1.db.medical_state = {"conditions": [{"type": "bleeding"}]}
        asked = []
        with mock.patch.object(actions, "_advertisers",
                               side_effect=lambda s, need, **kw: asked.append(need) or []):
            actions.plan_for(self.char1, "health")
        self.assertEqual(asked, ["treatment"])


class TestTheBenchIsStocked(EvenniaCommandTest):
    def test_a_mechanic_draws_supplies_on_shift(self):
        self.char1.db.soul_role = "mechanic"
        self.char1.db.soul_post = self.room1
        self.char1.location = self.room1
        from world.souls import salience
        with mock.patch("world.director.medical.restock_mechanic") as drew, \
             mock.patch.object(type(self.char1), "execute_cmd"):
            salience.do_post_work(self.char1)
        drew.assert_called_once_with(self.char1)

    def test_the_par_list_is_not_the_medics(self):
        """A painkiller is no use to something with no nociception."""
        from world.director.medical import MECHANIC_PAR, PAR
        self.assertNotEqual(MECHANIC_PAR, PAR)
        self.assertNotIn("PAINKILLER", MECHANIC_PAR)

    def test_the_tourniquet_is_on_both(self):
        """Clamping a line stops amber hydraulic fluid exactly as well
        as it stops blood."""
        from world.director.medical import MECHANIC_PAR, PAR
        self.assertIn("TOURNIQUET", MECHANIC_PAR)
        self.assertIn("TOURNIQUET", PAR)
