"""A fall breaks legs, not hearts (#3579).

``apply_fall_damage`` fills the body from the ground up rather than
dumping the whole number on the chest the way a generic hit does. The
defects it guards, each of which the old per-verb fall code shipped at
some point:

* **Falls used to hit the chest.** A body that lands feet-first and
  loses a lung reads as a bug to every player who has ever jumped off
  anything. Tier 1 is the LEGS, ordered ground-up, and the chest is not
  reachable until both tiers are exhausted.
* **"Leg" cannot be a hardcoded list.** ``_is_leg_bone`` asks the live
  organ what it feeds, so a chrome leg counts and a rat's hind paws
  count. The two organs that feed ``moving`` but are NOT legs are the
  pelvis (no ``can_be_destroyed`` flag at all) and the
  thoracolumbar_spine (``cannot_be_destroyed``) -- a fall that snapped
  your spine on the way down every time would be a different game.
* **Destroyed organs must be skipped, not filled.** A body that has
  already lost both feet takes the next fall in the shins. The live
  filter is what makes a second fall land somewhere new.
* **A killing chunk ends the fill.** Damage past death is damage to a
  corpse, and each chunk is a separate ``take_damage`` call that runs
  the whole death pipeline.
"""

from __future__ import annotations

from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.gravity import apply_fall_damage, fall_targets


def _names(organs):
    return [o.name for o in organs]


def _hp(char, organ_name):
    return char.medical_state.organs[organ_name].current_hp


class TestTheOrderTheBodyFillsIn(EvenniaTest):
    """tier1 is the legs, ground up; tier2 the other severable limbs."""

    def test_the_feet_come_first_then_shins_then_thighs(self):
        tier1, _tier2, _covered = fall_targets(self.char1)
        self.assertEqual(
            _names(tier1),
            ["right_metatarsals", "left_metatarsals",
             "right_tibia", "left_tibia",
             "right_femur", "left_femur"],
        )

    def test_the_pelvis_is_never_a_leg(self):
        """It feeds ``moving`` and carries neither destroy flag."""
        tier1, tier2, _ = fall_targets(self.char1)
        self.assertIn("pelvis", self.char1.medical_state.organs,
                      "premise: the human table has a pelvis")
        self.assertNotIn("pelvis", _names(tier1))
        self.assertNotIn("pelvis", _names(tier2))

    def test_the_spine_is_never_a_leg(self):
        tier1, tier2, _ = fall_targets(self.char1)
        self.assertIn("thoracolumbar_spine", self.char1.medical_state.organs)
        self.assertNotIn("thoracolumbar_spine", _names(tier1))
        self.assertNotIn("thoracolumbar_spine", _names(tier2))

    def test_tier_two_is_arms_and_hands_and_never_the_head(self):
        _tier1, tier2, _ = fall_targets(self.char1)
        containers = {o.container for o in tier2}
        self.assertTrue(containers, "tier2 was empty -- the pin is vacuous")
        self.assertNotIn("head", containers)
        self.assertLessEqual(containers,
                             {"left_arm", "right_arm",
                              "left_hand", "right_hand"})

    def test_the_covered_set_names_both_tiers(self):
        tier1, tier2, covered = fall_targets(self.char1)
        for organ in tier1 + tier2:
            self.assertIn(organ.container, covered)
        self.assertNotIn("chest", covered)

    def test_a_dead_organ_is_not_a_target(self):
        self.char1.medical_state.organs["right_metatarsals"].current_hp = 0
        self.char1.medical_state.organs["left_metatarsals"].current_hp = 0
        self.char1.save_medical_state()
        tier1, _, _ = fall_targets(self.char1)
        self.assertEqual(_names(tier1)[0], "right_tibia")
        self.assertNotIn("right_metatarsals", _names(tier1))


class TestWhereTwoStoreysLand(EvenniaTest):
    """FALL_DAMAGE_PER_STORY x 2 = 10, and a metatarsal has 20 hp, so a
    two-storey fall is exactly one foot's worth."""

    AMOUNT = 10

    def test_the_first_foot_takes_it(self):
        before = _hp(self.char1, "right_metatarsals")
        dealt, died = apply_fall_damage(self.char1, self.AMOUNT)
        self.assertFalse(died)
        self.assertGreater(dealt, 0)
        self.assertLess(_hp(self.char1, "right_metatarsals"), before)

    def test_nothing_reaches_the_chest(self):
        chest = [o for o in self.char1.medical_state.organs.values()
                 if o.container == "chest"]
        self.assertTrue(chest, "premise: the chest holds organs")
        before = {o.name: o.current_hp for o in chest}
        apply_fall_damage(self.char1, self.AMOUNT)
        for name, hp in before.items():
            self.assertEqual(_hp(self.char1, name), hp,
                             f"{name} took fall damage")

    def test_nothing_reaches_the_head(self):
        before = {o.name: o.current_hp
                  for o in self.char1.medical_state.organs.values()
                  if o.container == "head"}
        apply_fall_damage(self.char1, self.AMOUNT)
        for name, hp in before.items():
            self.assertEqual(_hp(self.char1, name), hp)

    def test_the_second_foot_is_still_whole(self):
        before = _hp(self.char1, "left_metatarsals")
        apply_fall_damage(self.char1, self.AMOUNT)
        self.assertEqual(_hp(self.char1, "left_metatarsals"), before)

    def test_zero_damage_touches_nothing(self):
        before = _hp(self.char1, "right_metatarsals")
        dealt, died = apply_fall_damage(self.char1, 0)
        self.assertEqual((dealt, died), (0, False))
        self.assertEqual(_hp(self.char1, "right_metatarsals"), before)


class TestWhenTheFeetRunOut(EvenniaTest):
    """Both metatarsals are 20 hp; 45 exhausts them and spills up."""

    def test_the_fill_spills_into_a_shin(self):
        apply_fall_damage(self.char1, 45)
        self.assertEqual(_hp(self.char1, "right_metatarsals"), 0)
        self.assertEqual(_hp(self.char1, "left_metatarsals"), 0)
        self.assertLess(_hp(self.char1, "right_tibia"), 25)

    def test_it_stops_at_the_first_shin(self):
        apply_fall_damage(self.char1, 45)
        self.assertEqual(_hp(self.char1, "left_tibia"), 25)
        self.assertEqual(_hp(self.char1, "right_femur"), 30)

    def test_and_still_leaves_the_chest_alone(self):
        before = {o.name: o.current_hp
                  for o in self.char1.medical_state.organs.values()
                  if o.container == "chest"}
        apply_fall_damage(self.char1, 45)
        for name, hp in before.items():
            self.assertEqual(_hp(self.char1, name), hp)

    def test_a_body_with_no_feet_starts_at_the_shins(self):
        for name in ("right_metatarsals", "left_metatarsals"):
            self.char1.medical_state.organs[name].current_hp = 0
        self.char1.save_medical_state()
        apply_fall_damage(self.char1, 10)
        self.assertLess(_hp(self.char1, "right_tibia"), 25)


class TestARatFallsOnItsHindPaws(EvenniaTest):
    """The species table is the authority, not a hardcoded leg list. A
    rat has no femur; it has hindleg bones and hindpaw bones, and the
    ground-up order is read off the rat's own display order."""

    def _rat(self):
        rat = create_object("typeclasses.characters.Character",
                            key="a grey rat", location=self.room1)
        rat.db.species = "rat"
        rat.db.medical_state = None
        rat.medical_state = None
        return rat

    def test_the_rat_table_is_what_loaded(self):
        rat = self._rat()
        self.assertIn("left_hindpaw_bones", rat.medical_state.organs)
        self.assertNotIn("left_femur", rat.medical_state.organs)

    def test_hind_paws_come_before_hind_legs(self):
        tier1, _, _ = fall_targets(self._rat())
        self.assertEqual(
            _names(tier1),
            ["right_hindpaw_bones", "left_hindpaw_bones",
             "right_hindleg_bone", "left_hindleg_bone"],
        )

    def test_the_forelegs_are_not_legs(self):
        """They feed ``manipulation`` -- they are the rat's arms."""
        tier1, _, _ = fall_targets(self._rat())
        self.assertNotIn("left_foreleg_bone", _names(tier1))
        self.assertNotIn("left_forepaw_bones", _names(tier1))

    def test_the_tail_is_not_a_leg(self):
        """``tail_vertebrae`` is destroyable and LAST in the display
        order, so an order-only rule would have put it first."""
        tier1, _, _ = fall_targets(self._rat())
        self.assertNotIn("tail_vertebrae", _names(tier1))

    def test_a_rats_fall_lands_in_a_hind_paw(self):
        rat = self._rat()
        before = rat.medical_state.organs["right_hindpaw_bones"].current_hp
        apply_fall_damage(rat, 5)
        self.assertLess(
            rat.medical_state.organs["right_hindpaw_bones"].current_hp,
            before)


class TestTheFillStopsWhenItKills(EvenniaTest):
    """Each chunk is a full ``take_damage``, which runs the death
    pipeline. Filling a corpse's remaining organs afterwards would fire
    at_death's neighbours again and again."""

    def test_no_chunk_lands_after_the_killing_one(self):
        calls = []

        def killer(amount, location=None, injury_type=None, target_organ=None):
            calls.append(target_organ)
            return (True, amount)      # (died, actual damage)

        with mock.patch.object(type(self.char1), "take_damage",
                               side_effect=killer):
            dealt, died = apply_fall_damage(self.char1, 500)
        self.assertTrue(died)
        self.assertEqual(len(calls), 1, f"kept filling a corpse: {calls}")
        self.assertEqual(calls[0], "right_metatarsals")

    def test_a_survivable_fill_walks_the_whole_tier(self):
        """Control: with nothing dying, 500 damage walks well past one
        organ -- so the pin above is measuring the stop, not the loop."""
        calls = []

        def survivor(amount, location=None, injury_type=None,
                     target_organ=None):
            calls.append(target_organ)
            self.char1.medical_state.organs[target_organ].current_hp = 0
            return (False, amount)

        with mock.patch.object(type(self.char1), "take_damage",
                               side_effect=survivor):
            apply_fall_damage(self.char1, 500)
        self.assertGreater(len(calls), 6)
        self.assertEqual(calls[:2], ["right_metatarsals", "left_metatarsals"])


class TestWhatIsNotABody(EvenniaTest):
    def test_an_item_takes_no_fall_damage(self):
        item = create_object("typeclasses.items.Item", key="a shiv",
                             location=self.room1)
        self.assertEqual(apply_fall_damage(item, 50), (0, False))

    def test_a_room_takes_no_fall_damage(self):
        self.assertEqual(apply_fall_damage(self.room1, 50), (0, False))

    def test_none_takes_no_fall_damage(self):
        self.assertEqual(apply_fall_damage(None, 50), (0, False))
