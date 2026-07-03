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
            self.assertTrue(spec.get("wardrobe") or spec.get("outfits"), role)
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

    def test_weapon_pools_reference_real_prototypes(self):
        from world import prototypes as protos
        for role, spec in CIVILIAN_ROLES.items():
            for key in spec.get("weapon_pool", []):
                self.assertTrue(hasattr(protos, key), f"{role}: {key}")
            if spec.get("armed"):
                self.assertTrue(spec.get("weapon_pool"), f"{role} armed, no pool")

    def test_colonist_archetype_registered(self):
        from world.llm.prompt import ARCHETYPES
        self.assertIn("colonist", ARCHETYPES)
        self.assertEqual(ARCHETYPES["colonist"]["tools"], ["release", "style"])

    def _all_garments(self, spec):
        out = []
        for entry in spec.get("wardrobe", []):
            out.extend(entry if isinstance(entry, list) else [entry])
        outfits = spec.get("outfits") or []
        if isinstance(outfits, dict):
            outfits = [o for pool in outfits.values() for o in pool]
        for outfit in outfits:
            out.extend(outfit)
        return out

    def test_no_disguise_items_in_wardrobes(self):
        # Essential disguise items would scramble civilian apparent_uids
        # (witness/BOLO identity must stay stable).
        for role, spec in CIVILIAN_ROLES.items():
            for proto in self._all_garments(spec):
                self.assertNotIn("MASK", proto, role)
                self.assertNotIn("HOOD_UP", proto, role)
                self.assertNotIn("WIG", proto, role)

    def test_all_garments_reference_real_prototypes(self):
        from world import prototypes as protos
        for role, spec in CIVILIAN_ROLES.items():
            for key in self._all_garments(spec):
                self.assertTrue(hasattr(protos, key), f"{role}: {key}")

    def test_companion_outfits_are_sex_keyed_and_shod(self):
        outfits = CIVILIAN_ROLES["synth_companion"]["outfits"]
        self.assertIn("female", outfits)
        self.assertIn("male", outfits)
        footwear = {"HEELED_BOOTS", "COMBAT_BOOTS", "HIGH_TOPS"}
        for sex, pool in outfits.items():
            self.assertGreaterEqual(len(pool), 3, sex)
            for outfit in pool:
                self.assertTrue(footwear & set(outfit), f"{sex}: {outfit}")
        # dresses/skirts stay out of the male pool
        male_garments = {g for o in outfits["male"] for g in o}
        self.assertFalse({"SYNTHWEAVE_SHEATH", "SLIT_SKIRT"} & male_garments)

    def test_synth_longdescs_survive_spawn_order(self):
        # Live bug: the species longdesc re-seed ran AFTER the flavor pass
        # and wiped all authored prose. Pin the order in the source.
        import inspect
        from world.director import civilians as _c
        source = inspect.getsource(_c.spawn_civilian)
        self.assertLess(source.index("get_species_default_longdesc_locations"),
                        source.index("apply_random_flavor(npc)"))

    def test_register_merged_from_serverconfig(self):
        from unittest.mock import patch as _patch
        import world.director.civilians as _c
        with _patch("evennia.server.models.ServerConfig") as mock_sc, \
             _patch("evennia.create_object") as mock_create, \
             _patch("evennia.prototypes.spawner.spawn") as mock_spawn, \
             _patch("world.mob_flavor.apply_random_flavor"), \
             _patch("world.anatomy.get_species_default_longdesc_locations",
                    return_value={}), \
             _patch("world.medical.core.MedicalState"), \
             _patch("world.spatial.rooms_within", return_value=[]), \
             _patch("world.spatial.is_reachable", return_value=True):
            mock_sc.objects.conf.return_value = {
                "synth_companion": "EXPLICIT-DIRECTIVE-SENTINEL"}
            garment = MagicMock(); garment.key = "dress"
            garment.layer = 2                  # sortable for inner-to-outer
            mock_spawn.return_value = [garment]
            npc = MagicMock(); npc.db = SimpleNamespace()
            mock_create.return_value = npc
            _c.spawn_civilian("synth_companion", _Room("alley"))
            self.assertEqual(npc.db.llm_persona["register"],
                             "EXPLICIT-DIRECTIVE-SENTINEL")
            # roles WITHOUT a configured register stay clean
            npc2 = MagicMock(); npc2.db = SimpleNamespace()
            mock_create.return_value = npc2
            _c.spawn_civilian("miner", _Room("street"))
            self.assertNotIn("register", npc2.db.llm_persona)

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
        garment.layer = 1                      # sortable for inner-to-outer
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

    def _victim(self, reaction, weapon=None):
        return SimpleNamespace(
            db=SimpleNamespace(reaction=reaction, role="x",
                               carried_weapon=weapon),
            execute_cmd=MagicMock())

    @patch("evennia.utils.delay")
    def test_resist_draws_carried_weapon(self, mock_delay):
        from world.director.civilians import react_to_attack
        v = self._victim("resist", weapon="tire iron")
        react_to_attack(v, MagicMock())
        cmds = [c.args for c in mock_delay.call_args_list]
        self.assertTrue(any("wield tire iron" in str(a) for a in cmds))

    @patch("evennia.utils.delay")
    def test_resist_unarmed_just_fights(self, mock_delay):
        from world.director.civilians import react_to_attack
        v = self._victim("resist", weapon=None)
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


class TestClothingStyles(TestCase):
    """Spawn-time style randomization + the LLM `style` tool."""

    def _item(self, closure=None, adjustable=None):
        configs, props = {}, {}
        if closure:
            configs["closure"] = {}; props["closure"] = closure
        if adjustable:
            configs["adjustable"] = {}; props["adjustable"] = adjustable
        item = SimpleNamespace(key="work coveralls",
                               db=SimpleNamespace(style_configs=configs,
                                                  style_properties=props))
        return item

    @patch("random.random", return_value=0.1)   # always under threshold
    def test_randomize_toggles_via_real_commands(self, _r):
        from world.director.civilians import _randomize_styles
        npc = SimpleNamespace(execute_cmd=MagicMock())
        _randomize_styles(npc, self._item(closure="zipped", adjustable="normal"))
        cmds = [c.args[0] for c in npc.execute_cmd.call_args_list]
        self.assertIn("unzip work coveralls", cmds)
        self.assertIn("rollup work coveralls", cmds)

    @patch("random.random", return_value=0.99)  # never under threshold
    def test_randomize_can_leave_defaults(self, _r):
        from world.director.civilians import _randomize_styles
        npc = SimpleNamespace(execute_cmd=MagicMock())
        _randomize_styles(npc, self._item(closure="zipped"))
        npc.execute_cmd.assert_not_called()

    def test_plain_garment_no_styling(self):
        from world.director.civilians import _randomize_styles
        npc = SimpleNamespace(execute_cmd=MagicMock())
        item = SimpleNamespace(key="boots",
                               db=SimpleNamespace(style_configs=None,
                                                  style_properties=None))
        _randomize_styles(npc, item)
        npc.execute_cmd.assert_not_called()

    def test_style_tool_registered(self):
        from world.llm.prompt import ARCHETYPES, TOOLS
        self.assertIn("style", TOOLS)
        self.assertIn("style", ARCHETYPES["colonist"]["tools"])
        self.assertIn("style", ARCHETYPES["companion"]["tools"])

    def test_style_handler_routes_real_verbs_only(self):
        from typeclasses.llm_npc import LLMNpcMixin
        npc = SimpleNamespace(execute_cmd=MagicMock(),
                              ndb=SimpleNamespace(), location=MagicMock())
        LLMNpcMixin._handle_action_tool(npc, "style", "unzip jacket", None)
        npc.execute_cmd.assert_called_once_with("unzip jacket")
        npc.execute_cmd.reset_mock()
        LLMNpcMixin._handle_action_tool(npc, "style", "detonate jacket", None)
        npc.execute_cmd.assert_not_called()   # junk verbs never execute
        LLMNpcMixin._handle_action_tool(npc, "style", "unzip", None)
        npc.execute_cmd.assert_not_called()   # verb without garment


class TestSynthFlavor(TestCase):
    """Full synth flavor tables: passes for human, but if you know you know."""

    def test_registered_in_all_axes(self):
        from world.mob_flavor import (_LONGDESCS_BY_SPECIES,
                                      _LOOK_PLACES_BY_SPECIES,
                                      _SHORT_DESCS_BY_SPECIES)
        for table in (_LONGDESCS_BY_SPECIES, _LOOK_PLACES_BY_SPECIES,
                      _SHORT_DESCS_BY_SPECIES):
            self.assertIn("synthetic_humanoid", table)

    def test_full_humanoid_slot_coverage(self):
        from world.mob_flavor.longdescs import LONGDESCS
        from world.mob_flavor.longdescs_synth import LONGDESCS_SYNTH
        self.assertEqual(set(LONGDESCS_SYNTH), set(LONGDESCS))
        for slot, options in LONGDESCS_SYNTH.items():
            if isinstance(options, dict):
                for sex, pool in options.items():
                    self.assertGreaterEqual(len(pool), 2, f"{slot}.{sex}")
            else:
                self.assertGreaterEqual(len(options), 3, slot)

    def test_chest_groin_are_sex_keyed(self):
        from world.mob_flavor.longdescs_synth import LONGDESCS_SYNTH
        for slot in ("chest", "groin"):
            entry = LONGDESCS_SYNTH[slot]
            self.assertIsInstance(entry, dict, slot)
            for sex in ("male", "female", "any"):
                self.assertIn(sex, entry, slot)
        # anatomically correct: female chest names breasts; male stays flat
        female_chest = str(LONGDESCS_SYNTH["chest"]["female"]).lower()
        male_chest = str(LONGDESCS_SYNTH["chest"]["male"]).lower()
        self.assertIn("breast", female_chest)
        self.assertNotIn("breast", male_chest)

    def test_random_longdesc_resolves_sex_pools(self):
        from world.mob_flavor import random_longdesc
        from world.mob_flavor.longdescs_synth import LONGDESCS_SYNTH
        line = random_longdesc("chest", "synthetic_humanoid", sex="female")
        self.assertIn(line, LONGDESCS_SYNTH["chest"]["female"])
        line = random_longdesc("chest", "synthetic_humanoid", sex="male")
        self.assertIn(line, LONGDESCS_SYNTH["chest"]["male"])
        # unknown sex falls to the any pool
        line = random_longdesc("chest", "synthetic_humanoid", sex="ambiguous")
        self.assertIn(line, LONGDESCS_SYNTH["chest"]["any"])

    def test_pair_slots_use_braced_nouns(self):
        from world.mob_flavor.longdescs_synth import LONGDESCS_SYNTH
        for slot in ("eyes", "ears", "arms", "hands", "thighs", "shins",
                     "feet"):
            for line in LONGDESCS_SYNTH[slot]:
                self.assertIn("{" + slot + "}", line, slot)

    def test_register_is_uncanny_not_mechanical(self):
        # Synths PASS — no robot vocabulary leaks into the prose.
        from world.mob_flavor.longdescs_synth import LONGDESCS_SYNTH
        from world.mob_flavor.short_descs_synth import SHORT_DESCS_SYNTH
        joined = (str(LONGDESCS_SYNTH) + str(SHORT_DESCS_SYNTH)).lower()
        for tell in ("symmetr", "poreless", "engineered"):
            self.assertIn(tell, joined)
        for robot_word in ("servo", "actuator", "chassis", "optics",
                           "vocalizer"):
            self.assertNotIn(robot_word, joined)


class TestWardrobeLayering(TestCase):
    """The barefoot-companion bug class: same-layer collisions and
    outer-before-inner wear orders silently strip garments."""

    def _proto_attr(self, key, attr):
        from world import prototypes as protos
        proto = getattr(protos, key)
        return dict(a[:2] for a in proto["attrs"]).get(attr)

    def test_footwear_sits_on_the_footwear_layer(self):
        # COMBAT_BOOTS convention: layer 3, "doesn't conflict with pants".
        for key in ("HEELED_BOOTS", "PIT_BOOTS", "HIGH_TOPS"):
            self.assertGreaterEqual(self._proto_attr(key, "layer"), 3, key)

    def test_no_same_layer_same_slot_collisions_in_any_look(self):
        # Simulate every role's possible look; no two garments may claim
        # the same location on the same layer.
        from itertools import product
        from world import prototypes as protos

        def garment(key):
            attrs = dict(a[:2] for a in getattr(protos, key)["attrs"])
            return attrs.get("layer", 2), attrs.get("coverage", [])

        for role, spec in CIVILIAN_ROLES.items():
            looks = []
            outfits = spec.get("outfits") or []
            if isinstance(outfits, dict):
                for pool in outfits.values():
                    looks.extend([list(o) for o in pool])
            else:
                looks.extend([list(o) for o in outfits])
            wardrobe = spec.get("wardrobe") or []
            if wardrobe:
                slots = [e if isinstance(e, list) else [e] for e in wardrobe]
                looks.extend([list(c) for c in product(*slots)])
            for look in looks:
                seen = {}
                for key in look:
                    layer, coverage = garment(key)
                    for loc in coverage:
                        self.assertNotIn(
                            (loc, layer), seen,
                            f"{role}: {key} vs {seen.get((loc, layer))} "
                            f"at {loc} layer {layer}")
                        seen[(loc, layer)] = key

    def test_spawn_wears_inner_to_outer(self):
        import inspect
        from world.director import civilians as _c
        source = inspect.getsource(_c.spawn_civilian)
        self.assertIn('sorted(items, key=lambda i: getattr(i, "layer", 2))',
                      source)
