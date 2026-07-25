"""Named-NPC blueprints (NPC_POSTS_AND_REINCARNATION_SPEC §P1): registry
integrity, and a full build-from-nothing → verify round trip for every
blueprint in a test db."""

from unittest import TestCase

from django.test import override_settings
from evennia.utils.test_resources import BaseEvenniaTest

from world.npcs.blueprints import BLUEPRINTS, build_npc, verify_blueprint


class TestRegistryIntegrity(TestCase):
    """Every blueprint is internally valid BEFORE any build is attempted."""

    def test_identity_vocab_validates(self):
        from world.identity import HEIGHTS, BUILDS
        from world.combat.constants import VALID_SKINTONES
        for key, bp in BLUEPRINTS.items():
            ident = bp.get("identity", {})
            if ident.get("height"):
                self.assertIn(ident["height"], HEIGHTS, key)
            if ident.get("build"):
                self.assertIn(ident["build"], BUILDS, key)
            if ident.get("skintone"):
                self.assertIn(ident["skintone"], VALID_SKINTONES, key)

    def test_personas_have_real_archetypes(self):
        from world.llm.prompt import ARCHETYPES
        for key, bp in BLUEPRINTS.items():
            arch = (bp.get("persona") or {}).get("archetype")
            self.assertIn(arch, ARCHETYPES, key)

    def test_wardrobe_specs_are_wearable(self):
        for key, bp in BLUEPRINTS.items():
            for g in bp.get("wardrobe", ()):
                self.assertTrue(g.get("worn_desc"), f"{key}: {g['key']}")
                self.assertTrue(g.get("coverage"), f"{key}: {g['key']}")

    def test_post_policies_valid(self):
        for key, bp in BLUEPRINTS.items():
            self.assertIn(bp["post"]["policy"],
                          (None, "resleave", "successor"), key)

    def test_roster_complete(self):
        self.assertEqual(len(BLUEPRINTS), 10)
        for expected in ("butcher_ottilie", "bartender_del", "doctor_marta",
                         "companion_vesper", "dispatch_petra",
                         "tobacconist_bellows"):
            self.assertIn(expected, BLUEPRINTS)


@override_settings(PROTOTYPE_MODULES=["world.prototypes"])
class TestBuildRoundTrip(BaseEvenniaTest):
    """Build every named NPC from nothing in the test db, then verify the
    result against its own blueprint — the §P1 fidelity check.

    BaseEvenniaTest overrides PROTOTYPE_MODULES to Evennia's empty template
    (discovered here the hard way: every spawn-by-key returns 0 matches
    inside it); restore the game's prototype module for real spawns."""

    def test_build_and_verify_all(self):
        for key in BLUEPRINTS:
            npc = build_npc(key, self.room1)
            diffs = verify_blueprint(key, npc)
            self.assertEqual(diffs, [], f"{key}: {diffs}")
            self.assertTrue(npc.db.llm_driven, key)
            npc.delete()

    def test_invalid_identity_refused_before_write(self):
        import copy
        from world.npcs import blueprints as bmod
        broken = copy.deepcopy(BLUEPRINTS["butcher_ottilie"])
        broken["identity"]["build"] = "sturdy"   # the historical server-killer
        bmod.BLUEPRINTS["_test_broken"] = broken
        try:
            with self.assertRaises(ValueError):
                build_npc("_test_broken", self.room1)
        finally:
            del bmod.BLUEPRINTS["_test_broken"]
