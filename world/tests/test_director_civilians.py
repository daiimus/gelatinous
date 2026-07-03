"""Tests for the civilian layer: roles, spawn wiring, cadence drift,
stagger, ambience, and tag-scoped purge safety."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import civilians as cmod
from world.director import routines as rmod
from world.director.civilians import (
    CIVILIAN_ROLES,
    TOKEN_RANGE,
    ambient_beat,
    purge_civilians,
    spawn_civilian,
)


class _Room:
    def __init__(self, name, sky=False):
        self.name = name
        self.db = SimpleNamespace(is_sky_room=sky)


class TestRoles(TestCase):
    def test_every_role_is_complete(self):
        for role, spec in CIVILIAN_ROLES.items():
            self.assertTrue(spec["wardrobe"], role)
            self.assertGreaterEqual(len(spec["ambient"]), 3, role)
            self.assertIn(spec["reaction"], ("comply", "flee", "resist"), role)
            self.assertIn("armed", spec, role)
            self.assertIn("reports", spec, role)
            persona = spec["persona"]
            self.assertIn(persona["archetype"], ("colonist", "companion"), role)
            for key in ("name", "description", "personality", "manner",
                        "wants", "boundaries"):
                self.assertTrue(persona.get(key), f"{role}.{key}")

    def test_colony_roster_shape(self):
        self.assertEqual(
            sorted(CIVILIAN_ROLES),
            ["addict", "ganger", "hawker", "miner", "salaryman", "scavver",
             "synth_companion", "synth_company_man"])
        # teeth: at least two resist roles, and armed ones carry blades
        resisters = [r for r, s in CIVILIAN_ROLES.items()
                     if s["reaction"] == "resist"]
        self.assertGreaterEqual(len(resisters), 2)
        self.assertEqual(CIVILIAN_ROLES["ganger"]["reports"], "never")
        self.assertEqual(CIVILIAN_ROLES["hawker"]["stock"][0],
                         "CIGARETTE_PACK_NOIR")
        for role in ("synth_companion", "synth_company_man"):
            self.assertEqual(CIVILIAN_ROLES[role]["species"],
                             "synthetic_humanoid")

    def test_colonist_archetype_registered(self):
        from world.llm.prompt import ARCHETYPES
        self.assertIn("colonist", ARCHETYPES)
        self.assertEqual(ARCHETYPES["colonist"]["tools"], ["release"])

    def test_no_disguise_items_in_wardrobes(self):
        # Essential disguise items would scramble civilian apparent_uids
        # (witness/BOLO identity must stay stable).
        for role, spec in CIVILIAN_ROLES.items():
            for proto in spec["wardrobe"]:
                self.assertNotIn("MASK", proto, role)
                self.assertNotIn("HOOD_UP", proto, role)
                self.assertNotIn("WIG", proto, role)

    def test_ambient_beat_by_role(self):
        npc = SimpleNamespace(db=SimpleNamespace(role="miner"))
        self.assertIn(ambient_beat(npc), CIVILIAN_ROLES["miner"]["ambient"])
        self.assertIsNone(ambient_beat(
            SimpleNamespace(db=SimpleNamespace(role="security"))))


class TestSpawn(TestCase):
    @patch("world.spatial.is_reachable", return_value=True)
    @patch("world.spatial.rooms_within")
    @patch("world.mob_flavor.apply_random_flavor")
    @patch("evennia.prototypes.spawner.spawn")
    @patch("evennia.create_object")
    def test_spawn_full_wiring(self, mock_create, mock_spawn, _flavor,
                               mock_within, _reach):
        anchor = _Room("Maxwell Street")
        haunts = [_Room("a"), _Room("b"), _Room("c"), _Room("d"),
                  _Room("e"), _Room("f")]
        sky = _Room("In the Air", sky=True)
        mock_within.return_value = haunts + [sky]
        garment = MagicMock()
        garment.key = "cotton t-shirt"
        mock_spawn.return_value = [garment]
        npc = MagicMock()
        npc.db = SimpleNamespace()
        mock_create.return_value = npc

        out = spawn_civilian("hawker", anchor)
        self.assertIs(out, npc)
        self.assertEqual(npc.db.role, "hawker")
        self.assertEqual(npc.db.reaction, "comply")
        self.assertEqual(npc.db.reports, "fast")
        self.assertTrue(npc.db.is_npc)   # canonical marker (absence = PC)
        self.assertTrue(TOKEN_RANGE[0] <= npc.db.tokens <= TOKEN_RANGE[1])
        self.assertTrue(npc.db.llm_driven)
        self.assertEqual(npc.db.llm_persona["archetype"], "colonist")
        npc.tags.add.assert_called_once_with("civilian", category="director")
        # dressed via the REAL command
        worn = [c.args[0] for c in npc.execute_cmd.call_args_list
                if c.args[0].startswith("wear ")]
        self.assertEqual(len(worn), len(CIVILIAN_ROLES["hawker"]["wardrobe"]))
        # haunts sampled from nearby; slow cadence
        self.assertTrue(2 <= len(npc.db.patrol_beat) <= 4)
        self.assertTrue(all(h in haunts for h in npc.db.patrol_beat))
        self.assertNotIn(sky, npc.db.patrol_beat)   # no air haunts
        # presentation completeness (live report: genders/skintones/voices)
        from world.director.civilians import HUMAN_SKINTONES
        self.assertIn(npc.db.skintone, HUMAN_SKINTONES)
        self.assertTrue(npc.db.voice_description)
        self.assertTrue(npc.db.voice_ending)
        self.assertTrue(3 <= npc.db.patrol_cadence <= 6)
        self.assertIs(npc.db.post, anchor)

    def test_bad_role_or_anchor(self):
        self.assertIsNone(spawn_civilian("astronaut", _Room("x")))
        self.assertIsNone(spawn_civilian("hawker", None))


class TestPurgeSafety(TestCase):
    @patch("world.director.civilians.all_civilians")
    def test_purge_is_tag_scoped_and_role_filterable(self, mock_all):
        a = MagicMock(); a.db = SimpleNamespace(role="hawker"); a.contents = []
        b = MagicMock(); b.db = SimpleNamespace(role="addict"); b.contents = []
        mock_all.return_value = [a, b]
        self.assertEqual(purge_civilians("hawker"), 1)
        a.delete.assert_called_once()
        b.delete.assert_not_called()

    @patch("world.director.civilians.all_civilians")
    def test_purge_all_takes_clothes_along(self, mock_all):
        shirt = MagicMock()
        a = MagicMock(); a.db = SimpleNamespace(role="miner")
        a.contents = [shirt]
        mock_all.return_value = [a]
        self.assertEqual(purge_civilians(), 1)
        shirt.delete.assert_called_once()


@patch("world.director.routines._in_combat", return_value=False)
@patch("world.director.routines.is_travelling", return_value=False)
@patch("world.director.routines.is_assigned", return_value=False)
class TestCadenceAndStagger(TestCase):
    def _npc(self, location, post, beat, cadence=None):
        return SimpleNamespace(
            location=location, ndb=SimpleNamespace(),
            db=SimpleNamespace(role="addict", post=post, patrol_beat=beat,
                              patrol_cadence=cadence),
            execute_cmd=MagicMock())

    def test_cadence_waits_then_acts(self, *_m):
        base, a = _Room("base"), _Room("a")
        npc = self._npc(base, base, [a], cadence=3)
        npc.ndb.patrol_idx = 0
        self.assertEqual(rmod.tick_npc(npc), "wait")
        self.assertEqual(rmod.tick_npc(npc), "wait")
        with patch("world.director.routines.at_waypoint"):
            self.assertEqual(rmod.tick_npc(npc), "waypoint")
        # counter reset — waits again
        self.assertEqual(rmod.tick_npc(npc), "wait")

    @patch("world.director.routines.travel_to")
    def test_fresh_npc_staggers_to_random_index(self, mock_travel, *_m):
        base = _Room("base")
        beat = [_Room(f"r{i}") for i in range(6)]
        seen = set()
        for _ in range(24):
            npc = self._npc(base, None, list(beat))
            rmod.tick_npc(npc)   # cadence 1 (None) → acts immediately
            seen.add(getattr(npc.ndb, "patrol_idx", None))
        self.assertGreater(len(seen), 2)   # spread, not lockstep at 0

class TestConversationHold(TestCase):
    """The LLM engagement hold: an engaged NPC defers its drift until the
    model releases it (or the inactivity window lapses)."""

    def _npc(self, engaged_until=None):
        return SimpleNamespace(
            location=_Room("street"), ndb=SimpleNamespace(
                llm_engaged_until=engaged_until),
            db=SimpleNamespace(role="hawker", post=None, patrol_beat=None,
                               patrol_cadence=None),
            execute_cmd=MagicMock())

    @patch("world.director.routines._in_combat", return_value=False)
    @patch("world.director.routines.is_travelling", return_value=False)
    @patch("world.director.routines.is_assigned", return_value=False)
    def test_engaged_npc_is_not_idle(self, *_m):
        from time import monotonic
        held = self._npc(engaged_until=monotonic() + 100)
        self.assertFalse(rmod.is_patrol_idle(held))

    @patch("world.director.routines._in_combat", return_value=False)
    @patch("world.director.routines.is_travelling", return_value=False)
    @patch("world.director.routines.is_assigned", return_value=False)
    def test_lapsed_or_released_hold_frees_the_npc(self, *_m):
        from time import monotonic
        lapsed = self._npc(engaged_until=monotonic() - 5)
        self.assertTrue(rmod.is_patrol_idle(lapsed))
        released = self._npc(engaged_until=None)
        self.assertTrue(rmod.is_patrol_idle(released))

    def test_release_tool_registered_for_mobile_archetypes(self):
        from world.llm.prompt import ARCHETYPES, TOOLS
        self.assertIn("release", TOOLS)
        self.assertEqual(TOOLS["release"]["kind"], "action")
        self.assertIn("release", ARCHETYPES["colonist"]["tools"])
        self.assertIn("release", ARCHETYPES["security"]["tools"])

    def test_release_handler_clears_the_hold(self):
        from typeclasses.llm_npc import LLMNpcMixin
        npc = SimpleNamespace(ndb=SimpleNamespace(llm_engaged_until=999.0),
                              location=MagicMock())
        LLMNpcMixin._handle_action_tool(npc, "release", "", MagicMock())
        self.assertIsNone(npc.ndb.llm_engaged_until)


class TestReactToAttack(TestCase):
    """§5.2 victim reactions: resist draws, comply yields, flee runs."""

    def _victim(self, reaction, blade=False):
        v = SimpleNamespace(
            db=SimpleNamespace(reaction=reaction, role="x"),
            contents=([SimpleNamespace(key="a dagger")] if blade else []),
            execute_cmd=MagicMock())
        return v

    @patch("evennia.utils.delay")
    def test_resist_draws_carried_blade(self, mock_delay):
        from world.director.civilians import react_to_attack
        v = self._victim("resist", blade=True)
        react_to_attack(v, MagicMock())
        cmds = [c.args for c in mock_delay.call_args_list]
        self.assertTrue(any("wield dagger" in str(a) for a in cmds))

    @patch("evennia.utils.delay")
    def test_resist_unarmed_just_fights(self, mock_delay):
        from world.director.civilians import react_to_attack
        v = self._victim("resist", blade=False)
        react_to_attack(v, MagicMock())
        mock_delay.assert_not_called()   # handler default = fists

    @patch("evennia.utils.delay")
    def test_comply_yields(self, mock_delay):
        from world.director.civilians import react_to_attack
        v = self._victim("comply")
        react_to_attack(v, MagicMock())
        cmds = str([c.args for c in mock_delay.call_args_list])
        self.assertIn("stop attacking", cmds)

    @patch("evennia.utils.delay")
    def test_flee_runs(self, mock_delay):
        from world.director.civilians import react_to_attack
        v = self._victim("flee")
        react_to_attack(v, MagicMock())
        cmds = str([c.args for c in mock_delay.call_args_list])
        self.assertIn("flee", cmds)

    @patch("evennia.utils.delay")
    def test_reactionless_target_is_ignored(self, mock_delay):
        from world.director.civilians import react_to_attack
        pc = SimpleNamespace(db=SimpleNamespace(reaction=None))
        react_to_attack(pc, MagicMock())
        mock_delay.assert_not_called()
