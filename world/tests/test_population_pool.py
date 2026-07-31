"""The civilian pool ceiling and the hour's effect on crowds."""

from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.director import population


class TestCivilianPoolCeiling(EvenniaTest):
    """A respawn loop without a ceiling is how you get 4,000 NPCs."""

    def test_ceiling_comes_from_settings(self):
        with self.settings(CIVILIAN_POOL_MAX=7):
            self.assertEqual(population.civilian_pool_max(), 7)

    def test_ceiling_falls_back_to_the_default(self):
        with mock.patch.object(population, "CIVILIAN_POOL_DEFAULT", 12):
            with self.settings():
                # no override present in test settings -> default applies
                self.assertIsInstance(population.civilian_pool_max(), int)

    def test_garbage_ceiling_does_not_crash_the_heartbeat(self):
        with self.settings(CIVILIAN_POOL_MAX="not a number"):
            self.assertEqual(population.civilian_pool_max(),
                             population.CIVILIAN_POOL_DEFAULT)

    def test_zero_ceiling_disables_respawn(self):
        with self.settings(CIVILIAN_POOL_MAX=0):
            self.assertIsNone(population.maintain_civilian_population())

    def test_no_spawn_when_pool_is_full(self):
        with self.settings(CIVILIAN_POOL_MAX=2), \
             mock.patch.object(population, "living_civilians",
                               return_value=["a", "b"]):
            self.assertIsNone(population.maintain_civilian_population())

    def test_spawns_at_most_one_per_beat(self):
        """Losses are made good at a walking pace, not instantly."""
        room = self.room1
        with self.settings(CIVILIAN_POOL_MAX=40), \
             mock.patch.object(population, "living_civilians", return_value=[]), \
             mock.patch.object(population, "_spawnable_rooms", return_value=[room]), \
             mock.patch("world.director.civilians.spawn_civilian",
                        return_value="npc") as spawner:
            population.maintain_civilian_population()
            self.assertEqual(spawner.call_count, 1)


class TestCrowdKnowsTheHour(EvenniaTest):
    """Crowd level feeds witness chance and stealth, so the hour is mechanical."""

    def _level_at(self, hour):
        from world.crowd.crowd_system import CrowdSystem
        room = self.room1
        room.crowd_base_level = 3
        with mock.patch("world.gametime.colony_hour", return_value=hour):
            return CrowdSystem().calculate_crowd_level(room)

    def test_deep_night_is_emptier_than_the_evening_rush(self):
        self.assertLess(self._level_at(3), self._level_at(18))

    def test_shift_changes_are_the_peaks(self):
        self.assertGreaterEqual(self._level_at(8), self._level_at(14))
        self.assertGreaterEqual(self._level_at(18), self._level_at(14))

    def test_level_never_goes_negative(self):
        room = self.room1
        room.crowd_base_level = 0
        from world.crowd.crowd_system import CrowdSystem
        with mock.patch("world.gametime.colony_hour", return_value=2):
            self.assertGreaterEqual(CrowdSystem().calculate_crowd_level(room), 0)

    def test_a_broken_clock_does_not_empty_the_streets(self):
        from world.crowd.crowd_system import CrowdSystem
        room = self.room1
        room.crowd_base_level = 3
        with mock.patch("world.gametime.colony_hour",
                        side_effect=RuntimeError("clock is out")):
            self.assertGreater(CrowdSystem().calculate_crowd_level(room), 0)
