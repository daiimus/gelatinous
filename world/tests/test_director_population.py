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


class TestEnsureCommsFitted(TestCase):
    """The reload-time upkeep sweep: fit the comms module into pre-#1009
    units, never touch a unit that already has one (even destroyed)."""

    def _unit(self, organs):
        bot = MagicMock(name="bot")
        bot.db = SimpleNamespace(role="security")
        bot.medical_state = SimpleNamespace(organs=organs)
        return bot

    @patch("world.director.population.factory_fit_comms")
    @patch("evennia.objects.models.ObjectDB")
    def test_fits_only_units_missing_the_module(self, mock_db, mock_fit):
        from world.director.population import ensure_comms_fitted
        bare = self._unit({})                              # pre-#1009: fit
        fitted = self._unit({"comms_module": MagicMock()})  # has one: skip
        destroyed = self._unit({"comms_module": MagicMock()})  # EMP'd: skip
        civilian = MagicMock(); civilian.db = SimpleNamespace(role="miner")
        mock_db.objects.filter.return_value.distinct.return_value = [
            bare, fitted, destroyed, civilian]
        self.assertEqual(ensure_comms_fitted(), 1)
        mock_fit.assert_called_once_with(bare)

    @patch("world.director.population.factory_fit_comms")
    @patch("evennia.objects.models.ObjectDB")
    def test_sweep_heals_missing_voices(self, mock_db, _fit):
        from world.director.population import ensure_comms_fitted
        mute = self._unit({"comms_module": MagicMock()})
        mute.db.voice_description = None
        mock_db.objects.filter.return_value.distinct.return_value = [mute]
        ensure_comms_fitted()
        self.assertIn(mute.db.voice_description, ("clipped", "flinty", "icy"))
        self.assertIn(mute.db.voice_ending, ("monotone", "hum"))

    @patch("world.director.population.factory_fit_comms",
           side_effect=RuntimeError("bad unit"))
    @patch("evennia.objects.models.ObjectDB")
    def test_one_bad_unit_never_stops_the_sweep(self, mock_db, _fit):
        from world.director.population import ensure_comms_fitted
        units = [self._unit({}), self._unit({})]
        mock_db.objects.filter.return_value.distinct.return_value = units
        self.assertEqual(ensure_comms_fitted(), 0)   # both failed, no raise


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


class TestBaseStation(TestCase):
    """The base's dispatch console: installed by upkeep, idempotent, and
    only a live powered console counts as dispatch's voice."""

    def _station(self, on=True):
        s = MagicMock()
        s.db = SimpleNamespace(is_base_station=True, is_radio=True,
                               radio_on=on, frequency="911MHz")
        return s

    @patch("world.director.population.get_security_base", return_value=None)
    def test_no_base_no_station(self, _base):
        from world.director.population import ensure_base_station
        self.assertIsNone(ensure_base_station())

    @patch("world.director.population.get_security_base")
    def test_existing_console_is_kept(self, mock_base):
        from world.director.population import ensure_base_station
        station = self._station()
        base = MagicMock(); base.contents = [station]
        mock_base.return_value = base
        with patch("evennia.prototypes.spawner.spawn") as sp:
            self.assertIs(ensure_base_station(), station)
        sp.assert_not_called()                    # idempotent

    @patch("world.director.population.get_security_base")
    def test_missing_console_is_installed(self, mock_base):
        from world.director.population import ensure_base_station
        base = MagicMock(); base.contents = []
        mock_base.return_value = base
        newborn = MagicMock()
        with patch("evennia.prototypes.spawner.spawn",
                   return_value=[newborn]):
            self.assertIs(ensure_base_station(), newborn)
        self.assertIs(newborn.location, base)

    @patch("world.director.population.get_security_base")
    def test_powered_console_is_the_voice_off_is_silence(self, mock_base):
        from world.director.population import get_base_station
        live, dead = self._station(on=True), self._station(on=False)
        base = MagicMock()
        mock_base.return_value = base
        base.contents = [live]
        self.assertIs(get_base_station(), live)
        base.contents = [dead]                    # switched off: no voice
        self.assertIsNone(get_base_station())


class TestDispatchOperator(TestCase):
    """The human at the desk: live lookup (dead/absent -> automation) and
    idempotent upkeep."""

    def _op(self, dead=False, unconscious=False):
        op = MagicMock()
        op.db = SimpleNamespace(dispatch_operator=True)
        op.is_dead.return_value = dead
        op.is_unconscious.return_value = unconscious
        return op

    @patch("world.director.population.get_security_base")
    def test_live_operator_found(self, mock_base):
        from world.director.population import get_dispatch_operator
        vess = self._op()
        base = MagicMock(); base.contents = [vess]
        mock_base.return_value = base
        self.assertIs(get_dispatch_operator(), vess)

    @patch("world.director.population.get_security_base")
    def test_dead_or_unconscious_operator_is_no_operator(self, mock_base):
        from world.director.population import get_dispatch_operator
        base = MagicMock()
        mock_base.return_value = base
        base.contents = [self._op(dead=True)]
        self.assertIsNone(get_dispatch_operator())      # automation answers
        base.contents = [self._op(unconscious=True)]
        self.assertIsNone(get_dispatch_operator())

    @patch("world.director.population.get_security_base")
    def test_upkeep_is_idempotent(self, mock_base):
        from world.director.population import ensure_dispatch_operator
        vess = self._op()
        base = MagicMock(); base.contents = [vess]
        mock_base.return_value = base
        with patch("world.director.population.spawn_dispatch_operator") as sp:
            self.assertIs(ensure_dispatch_operator(), vess)
        sp.assert_not_called()
