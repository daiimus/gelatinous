"""Tests for the population layer's first slice: the security base and
complement maintenance (the respawn loop)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import population as pmod
from world.director.population import (
    count_posted_secbots,
    maintain_security_complement,
)


def _room(complement=None, beat=None):
    room = MagicMock(name="base")
    room.db = SimpleNamespace(security_complement=complement,
                              security_beat=beat)
    return room


def _bot(post, role="security", dead=False):
    bot = MagicMock(name="bot")
    bot.db = SimpleNamespace(post=post, role=role)
    bot.is_dead.return_value = dead
    return bot


class TestComplementCount(TestCase):
    @patch("evennia.objects.models.ObjectDB")
    def test_counts_living_posted_security_only(self, mock_db):
        base = _room()
        elsewhere = _room()
        units = [
            _bot(base),                        # counts
            _bot(base, dead=True),             # dead — fell out of census
            _bot(elsewhere),                   # other post
            _bot(base, role="miner"),          # wrong role
        ]
        mock_db.objects.filter.return_value.distinct.return_value = units
        self.assertEqual(count_posted_secbots(base), 1)


class TestMaintain(TestCase):
    @patch("world.director.population.spawn_secbot")
    @patch("world.director.population.count_posted_secbots", return_value=2)
    @patch("world.director.population.get_security_base")
    def test_full_complement_spawns_nothing(self, mock_base, _count, mock_spawn):
        mock_base.return_value = _room(complement=2)
        self.assertIsNone(maintain_security_complement())
        mock_spawn.assert_not_called()

    @patch("world.director.population.spawn_secbot")
    @patch("world.director.population.count_posted_secbots", return_value=0)
    @patch("world.director.population.get_security_base")
    def test_deficit_cycles_one_replacement(self, mock_base, _count, mock_spawn):
        base = _room(complement=3)
        mock_base.return_value = base
        unit = MagicMock()
        mock_spawn.return_value = unit
        self.assertIs(maintain_security_complement(), unit)
        mock_spawn.assert_called_once_with(base)   # ONE per tick
        unit.execute_cmd.assert_called_once()      # the alcove emote

    @patch("world.director.population.spawn_secbot")
    @patch("world.director.population.get_security_base", return_value=None)
    def test_no_base_no_respawn(self, _base, mock_spawn):
        self.assertIsNone(maintain_security_complement())
        mock_spawn.assert_not_called()

    @patch("world.director.population.spawn_secbot")
    @patch("world.director.population.count_posted_secbots", return_value=0)
    @patch("world.director.population.get_security_base")
    def test_zero_complement_disables(self, mock_base, _count, mock_spawn):
        mock_base.return_value = _room(complement=0)
        self.assertIsNone(maintain_security_complement())
        mock_spawn.assert_not_called()


class TestSpawnPostsToBase(TestCase):
    @patch("world.director.population.factory_fit_armament")
    @patch("world.mob_flavor.apply_random_flavor")
    @patch("world.medical.core.MedicalState")
    @patch("world.anatomy.get_species_default_longdesc_locations",
           return_value={})
    @patch("evennia.create_object")
    def test_unit_posted_to_base_and_adopts_standing_beat(
            self, mock_create, _l, _ms, _flavor, _fit):
        from world.director.population import spawn_secbot
        street_a, street_b = MagicMock(name="a"), MagicMock(name="b")
        base = _room(beat=[street_a, street_b])
        spawn_room = MagicMock(name="alcove")
        mob = MagicMock()
        mob.db = SimpleNamespace()
        mock_create.return_value = mob
        with patch("world.director.population.get_security_base",
                   return_value=base):
            unit = spawn_secbot(spawn_room)
        self.assertIs(unit.db.post, base)
        self.assertEqual(unit.db.patrol_beat, [street_a, street_b])
        self.assertEqual(unit.db.role, "security")
        self.assertTrue(unit.db.is_npc)   # canonical marker (absence = PC)
        self.assertTrue(unit.db.llm_driven)
        self.assertIsNone(unit.height)   # chassis renders via its key

    @patch("world.director.population.factory_fit_armament")
    @patch("world.mob_flavor.apply_random_flavor")
    @patch("world.medical.core.MedicalState")
    @patch("world.anatomy.get_species_default_longdesc_locations",
           return_value={})
    @patch("evennia.create_object")
    def test_no_base_posts_to_spawn_room(self, mock_create, _l, _ms, _f, _fit):
        from world.director.population import spawn_secbot
        spawn_room = MagicMock(name="street")
        mob = MagicMock()
        mob.db = SimpleNamespace()
        mock_create.return_value = mob
        with patch("world.director.population.get_security_base",
                   return_value=None):
            unit = spawn_secbot(spawn_room)
        self.assertIs(unit.db.post, spawn_room)

    @patch("world.director.population.factory_fit_armament")
    @patch("world.mob_flavor.apply_random_flavor")
    @patch("world.medical.core.MedicalState")
    @patch("world.anatomy.get_species_default_longdesc_locations",
           return_value={})
    @patch("evennia.create_object")
    def test_secbot_is_always_a_security_robot(self, mock_create, *_m):
        # A secbot IS a security robot — never courier/loader/industrial
        # (that chassis vocabulary belongs to other robots).
        from world.director.population import spawn_secbot
        mob = MagicMock()
        mob.db = SimpleNamespace()
        mock_create.return_value = mob
        with patch("world.director.population.get_security_base",
                   return_value=None):
            for _ in range(6):
                spawn_secbot(MagicMock(name="room"))
                key = mock_create.call_args.kwargs["key"]
                self.assertIn("security robot", key)
