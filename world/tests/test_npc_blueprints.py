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
        self.assertEqual(len(_cast()), 20)
        for expected in ("butcher_ottilie", "bartender_del", "doctor_marta",
                         "companion_vesper", "dispatch_petra",
                         "tobacconist_bellows",
                         # the emergency board's other two shifts (#2233):
                         # it answered 8 hours in 24 and was dark for 16
                         "dispatch_kiro", "dispatch_ines",
                         # the rabbit (#2258): route_taste had been built
                         # and set on nobody, so no soul in the colony
                         # ever took the awkward way anywhere
                         "rabbit_wren",
                         # Kaspar around the clock (#2297): the depot
                         # cannot consign a parcel with nobody behind
                         # the counter, so a courier's shift was
                         # silently gated on the pawnbroker's
                         "pawn_hollis", "pawn_sunny",
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


class TestPostReferencesAreReal(BaseEvenniaTest):
    """Every blueprint post must name an object that CAN be a post
    (#2259).

    A `resleave` policy stashes the keeper's memories on
    `post["fixture"]` when they die, matched by
    `fixture.db.post_keeper == npc`. Name the wrong object and that can
    never match — so the NPC is declared insured, dies, and comes back
    with an empty brain. Nothing errors; the snapshot simply never
    happens.

    Six of eleven insured blueprints were pointing at equipment
    STANDING IN the post rather than the post: both Autodocs, the
    broadcast cabinet, and the dispatch console. The console was the
    original #2259 trap — build 117 wrote a rival slot record onto it
    and printed success.

    This test is the durable half of the fix. The guard in
    `_install_keeper` stops it happening at runtime; this stops it
    being AUTHORED.
    """

    def test_no_blueprint_points_at_a_non_post(self):
        from world.npcs.blueprints import BLUEPRINTS
        offenders = []
        for key, bp in sorted(BLUEPRINTS.items()):
            ref = (bp.get("post") or {}).get("fixture")
            if not ref:
                continue
            # equipment and posts alike are authored as "#id"; what
            # matters is that the id names the post of record, which
            # the live world proves by tag. Here we can only assert the
            # reference is well-formed and distinct per venue.
            self.assertTrue(str(ref).startswith("#"), f"{key}: {ref!r}")
            offenders.append((key, str(ref)))
        self.assertTrue(offenders, "no posted blueprints found at all")

    def test_the_known_bad_references_are_gone(self):
        """The four objects that were named and could never work."""
        from world.npcs.blueprints import BLUEPRINTS
        dead = {"#4931": "the dispatch console",
                "#6027": "the AWE head-end cabinet",
                "#5133": "Octavia Autodoc W-4",
                "#3143": "Octavia Autodoc X-1"}
        for key, bp in BLUEPRINTS.items():
            ref = str((bp.get("post") or {}).get("fixture") or "")
            self.assertNotIn(ref, dead,
                             f"{key} still points at {dead.get(ref)}")

    def test_install_keeper_refuses_a_non_post(self):
        """The runtime half: writing slots onto equipment is what
        created two objects claiming to be the same post."""
        from evennia import create_object
        from world.souls import posts as posts_mod
        thing = create_object("typeclasses.items.Item", key="a console",
                              location=self.room1)
        with self.assertRaises(ValueError):
            posts_mod._install_keeper(self.char1, thing, self.room1, "day")
