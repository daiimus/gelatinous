"""A blueprinted NPC ships wearing all of `OUTFIT_SLOTS` (#2705).

The invariant — a torso piece, a leg piece, footwear — was declared in
`world/souls/population.py` and consulted by the generated-arrival
dresser ALONE. Blueprints never read it, so the rule governed
procedural residents and not the named cast:

    souls with an uncovered outfit slot:      20 of 78
      ... of which robots (legitimately bare):  8
      ... NON-robot, human:                    12

Every one of the twelve was missing exactly `feet` — Bianca Morgan,
Marisol, Tuck, Halina, Wren, Hollis, Sunny, Pia, Tobias, Marek,
Sunniva, Cameron Brito. They were not failing to put shoes on; they had
none in inventory.

METHOD, because it decides whether a re-run means anything: worn state
lives in the `worn_items` AttributeProperty on the CHARACTER, keyed by
body location. There is no per-item `db.worn` flag — zero such rows
exist — and a probe that read one reported all 78 souls as naked.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.souls.population import OUTFIT_SLOTS, missing_outfit_slots


class _Body(EvenniaTest):
    def npc(self, key="Testcast"):
        return create_object("typeclasses.characters.Character",
                             key=key, location=self.room1)


class TestTheInvariantCanSeeABareBody(_Body):

    def test_a_naked_body_is_short_every_slot(self):
        """Control: if the check could not see a bare body, everything
        below would pass on a body wearing nothing."""
        self.assertEqual(
            [slot for slot, _proof in missing_outfit_slots(self.npc())],
            [slot for slot, _proof in OUTFIT_SLOTS])

    def test_it_reads_worn_items_and_not_a_per_item_flag(self):
        """The trap that cost the original probe its first answer."""
        who = self.npc()
        self.assertFalse(
            any(g.attributes.has("worn") for g in who.contents),
            "a per-item `worn` flag has appeared; this check reads "
            "`worn_items` on the character and would need revisiting")


class TestABlueprintedNpcIsDressed(_Body):
    """The two build paths carry the same wardrobe loop copied twice, so
    both are driven here — a fix applied to one of them would be the
    same defect a second time."""

    def dress(self, who):
        from world.npcs.blueprints import _dress_to_the_invariant
        _dress_to_the_invariant(who)
        return [slot for slot, _proof in missing_outfit_slots(who)]

    def test_a_bare_body_ends_up_covered(self):
        left = self.dress(self.npc())
        self.assertEqual(left, [],
                         "a blueprinted NPC still ships short a slot")

    def test_the_feet_slot_in_particular(self):
        """What all twelve were missing."""
        who = self.npc()
        self.dress(who)
        self.assertIn("left_foot", who.worn_items or {})

    def test_it_does_not_overwrite_an_authored_wardrobe(self):
        """Fills only what is EMPTY — the blueprint's pieces win."""
        who = self.npc()
        self.dress(who)
        before = dict(who.worn_items or {})
        self.dress(who)
        self.assertEqual(dict(who.worn_items or {}), before,
                         "a second pass re-dressed an already-dressed body")


class TestARobotIsLeftAlone(_Body):
    """Eight of the twenty uncovered souls are robots, and they are bare
    on purpose."""

    def test_a_robot_is_never_short_a_slot(self):
        from unittest.mock import patch
        who = self.npc("unit")
        with patch("world.souls.needs.profile_name", return_value="robot"):
            self.assertEqual(missing_outfit_slots(who), [])

    def test_and_a_human_still_is(self):
        """Control for the line above."""
        from unittest.mock import patch
        who = self.npc()
        with patch("world.souls.needs.profile_name", return_value="human"):
            self.assertTrue(missing_outfit_slots(who))


class TestARefusedGarmentIsNotLeftBehind(_Body):
    """`wear_item` returns `(ok, message)` and refuses a garment going
    on UNDER an already-worn outer layer. A caller that discards the
    result leaves it sitting in inventory — and something doing that on
    a repeating schedule is how #6106 Sam Fukuda ended up carrying 628
    unworn pairs of trousers, spanning object ids 9811 to 16654."""

    def test_a_body_that_cannot_be_dressed_does_not_accumulate(self):
        from unittest.mock import patch
        from world.souls.population import ensure_outfit_complete
        who = self.npc()
        before = len(who.contents)
        with patch.object(type(who), "wear_item",
                          return_value=(False, "something is over it")):
            ensure_outfit_complete(who)
        self.assertEqual(
            len(who.contents), before,
            "a refused garment was left in inventory")

    def test_and_a_body_that_can_be_dressed_keeps_the_clothes(self):
        """Control: the deletion must not be eating garments that WERE
        successfully worn."""
        from world.souls.population import ensure_outfit_complete
        who = self.npc()
        ensure_outfit_complete(who)
        self.assertTrue(who.contents)
        self.assertTrue(who.worn_items)


class TestTheFloorIsNotMistakenForDrift(_Body):
    """`verify_blueprint` compares what a body WEARS against what its
    blueprint AUTHORED. A garment the invariant added is neither, so
    without a mark every invariant-dressed NPC reports as diverging
    from its own blueprint — which is how this change first broke
    `TestBuildRoundTrip`.

    The mark is written where the garment is worn rather than inferred
    from the blueprint's silence, because a blueprint that authors no
    wardrobe and one whose piece failed to spawn look identical from
    inside the verifier.
    """

    def test_what_the_invariant_adds_is_marked(self):
        from world.souls.population import ensure_outfit_complete
        who = self.npc()
        ensure_outfit_complete(who)
        added = [g for g in who.contents]
        self.assertTrue(added, "nothing was added to mark")
        for garment in added:
            self.assertTrue(garment.attributes.get("outfit_invariant"),
                            f"{garment.key} went on unmarked")

    def test_the_verifier_ignores_it(self):
        from world.npcs.blueprints import verify_blueprint
        from world.souls.population import ensure_outfit_complete
        who = self.npc()
        ensure_outfit_complete(who)
        fields = [d[0] for d in verify_blueprint("pawn_hollis", who)]
        self.assertNotIn("wardrobe", fields)

    def test_but_it_still_sees_an_unmarked_garment(self):
        """Control: the verifier has not simply stopped checking the
        wardrobe. Strip the mark off one of the same garments and it
        reports again — so what silences it is the MARK, not the fact
        that the pieces came from the rail."""
        from world.npcs.blueprints import verify_blueprint
        from world.souls.population import ensure_outfit_complete
        who = self.npc()
        ensure_outfit_complete(who)
        who.contents[0].attributes.remove("outfit_invariant")
        fields = [d[0] for d in verify_blueprint("pawn_hollis", who)]
        self.assertIn("wardrobe", fields)
