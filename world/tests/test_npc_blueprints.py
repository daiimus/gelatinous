"""Named-NPC blueprints (NPC_POSTS_AND_REINCARNATION_SPEC §P1): registry
integrity, and a full build-from-nothing → verify round trip for every
blueprint in a test db."""

from unittest import TestCase

from django.test import override_settings
from evennia.utils.test_resources import BaseEvenniaTest

from world.npcs.blueprints import BLUEPRINTS, build_npc, verify_blueprint


def _cast():
    """The real cast — blueprints flagged `fixture` are machinery for
    drills and pilots, and carry no persona or post by design."""
    return {k: bp for k, bp in BLUEPRINTS.items() if not bp.get("fixture")}


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
        for key, bp in _cast().items():
            arch = (bp.get("persona") or {}).get("archetype")
            self.assertIn(arch, ARCHETYPES, key)

    def test_wardrobe_specs_are_wearable(self):
        for key, bp in BLUEPRINTS.items():
            for g in bp.get("wardrobe", ()):
                self.assertTrue(g.get("worn_desc"), f"{key}: {g['key']}")
                self.assertTrue(g.get("coverage"), f"{key}: {g['key']}")

    def test_post_policies_valid(self):
        for key, bp in _cast().items():
            self.assertIn((bp.get("post") or {}).get("policy"),
                          (None, "resleave", "successor"), key)

    def test_roster_complete(self):
        # the cast, excluding machinery fixtures like the drill dummy
        self.assertEqual(len(_cast()), 17)
        for expected in ("butcher_ottilie", "bartender_del", "doctor_marta",
                         "companion_vesper", "dispatch_petra",
                         "tobacconist_bellows",
                         # the emergency board's other two shifts (#2233):
                         # it answered 8 hours in 24 and was dark for 16
                         "dispatch_kiro", "dispatch_ines",
                         # the bench (#2261): maintenance advertises only
                         # where somebody is standing, so these three ARE
                         # the repair system
                         "mech_marisol", "mech_tuck", "mech_halina"):
            self.assertIn(expected, BLUEPRINTS)

    def test_every_dispatcher_carries_the_desk_register(self):
        """All three keepers sit the same chair, so all three inherit the
        channel discipline — units announce themselves, and nobody
        promises to leave the desk. Petra's seed said `colonist` after
        the register moved, so a resleeve would have rebuilt her as a
        civilian with no radio tool at all."""
        for key in ("dispatch_petra", "dispatch_kiro", "dispatch_ines"):
            self.assertEqual(
                BLUEPRINTS[key]["persona"]["archetype"], "dispatcher", key)


@override_settings(PROTOTYPE_MODULES=["world.prototypes"])
class TestBuildRoundTrip(BaseEvenniaTest):
    """Build every named NPC from nothing in the test db, then verify the
    result against its own blueprint — the §P1 fidelity check.

    BaseEvenniaTest overrides PROTOTYPE_MODULES to Evennia's empty template
    (discovered here the hard way: every spawn-by-key returns 0 matches
    inside it); restore the game's prototype module for real spawns."""

    def test_build_and_verify_all(self):
        for key in _cast():
            npc = build_npc(key, self.room1)
            diffs = verify_blueprint(key, npc)
            self.assertEqual(diffs, [], f"{key}: {diffs}")
            self.assertTrue(npc.db.llm_driven, key)
            want_kw = BLUEPRINTS[key].get("identity", {}).get("sdesc_keyword")
            if want_kw:
                # the category-bug regression: the PROPERTY must see it
                self.assertEqual(npc.sdesc_keyword, want_kw, key)
                self.assertIn(want_kw, npc.get_sdesc(), key)
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
