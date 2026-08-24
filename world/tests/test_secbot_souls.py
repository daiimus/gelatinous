"""A unit is enlisted at birth (#2254).

The six units walking around were ensouled by a build script; the
RESPAWN path was not. So every unit lost in the field would have cycled
back out of a charging alcove soulless — no needs, no charge, no wear —
and attrition would have quietly undone the whole thing one casualty at
a time. The force would have drifted into a mix, and the longer it ran
the fewer souled units there'd be.

A fresh chassis starts clean: neglect has to earn its defects again on
the new body.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import engine, needs as needs_mod


class TestReplacementsAreEnlisted(EvenniaCommandTest):
    def _spawn(self):
        from world.director.population import spawn_secbot
        with mock.patch("world.director.population.get_security_base",
                        return_value=self.room1):
            return spawn_secbot(self.room1)

    def test_a_new_unit_has_a_soul(self):
        bot = self._spawn()
        self.assertTrue(bot.tags.get(engine.SOUL_TAG[0],
                                     category=engine.SOUL_TAG[1]))

    def test_it_runs_on_the_robot_profile(self):
        """Charge and maintenance in place of hunger and rest — it has
        no stomach to fill."""
        bot = self._spawn()
        self.assertEqual(needs_mod.profile_name(bot), "robot")
        profile = needs_mod.profile_of(bot)
        self.assertIn("charge", profile)
        self.assertNotIn("hunger", profile)

    def test_it_never_clocks_off(self):
        """A machine has no shift to end. What takes a unit out of
        service is a flat battery or a fault."""
        bot = self._spawn()
        self.assertEqual(bot.db.soul_schedule, "always")

    def test_it_draws_no_wage(self):
        """Property, not staff — and a rate of ZERO has to survive the
        `or 0.02` that used to read it as unset."""
        bot = self._spawn()
        self.assertEqual(bot.db.soul_wage_rate, 0.0)
        from world.souls.engine import _wage_rate
        self.assertEqual(_wage_rate(bot), 0.0)

    def test_it_belongs_to_its_base(self):
        bot = self._spawn()
        self.assertIs(bot.db.soul_post, self.room1)
        self.assertIs(bot.db.post, self.room1)

    def test_it_starts_clean(self):
        """No inherited defects: a new chassis is genuinely new."""
        from world.souls import traits as traits_mod
        bot = self._spawn()
        self.assertFalse(traits_mod.defects_of(bot)
                         if hasattr(traits_mod, "defects_of")
                         else bot.db.soul_defects or [])


class TestTheWageRateFix(EvenniaCommandTest):
    """`rate or 0.02` read a rate of NOTHING as "unset" and paid the
    default. Latent until robots became the first thing that earns
    nothing."""

    def test_zero_is_a_rate_not_an_absence(self):
        from world.souls.engine import _wage_rate
        self.char1.db.soul_wage_rate = 0.0
        self.assertEqual(_wage_rate(self.char1), 0.0)

    def test_unset_still_takes_the_default(self):
        from world.souls.engine import _wage_rate
        self.char1.db.soul_wage_rate = None
        self.assertEqual(_wage_rate(self.char1), 0.02)


class TestAlwaysOnShift(EvenniaCommandTest):
    def test_every_hour_is_a_working_hour(self):
        from world.souls.engine import SCHEDULES, _in_block
        work = SCHEDULES["always"]["work"]
        for hour in (0, 5.5, 13.9, 14, 21.99, 23.5):
            self.assertTrue(_in_block(hour, work), hour)

    def test_it_never_sleeps(self):
        from world.souls.engine import SCHEDULES, _in_block
        sleep = SCHEDULES["always"]["sleep"]
        for hour in (0, 6, 12, 18, 23):
            self.assertFalse(_in_block(hour, sleep), hour)
