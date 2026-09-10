"""Wardrobe is arbitrated at band 2, where the ruling puts it (#2699).

The band-2 arm's own comment cites the decision:

    you get dressed before you go to work, but not before you stop
    bleeding: wardrobe sits under the survival band and over the
    schedule (owner ruling 2026-08-20)

and the arm could never be reached. `wardrobe` is in `profile_of` for 34
of 40 ensouled bodies, so it was a band-1 candidate purely by being in
the profile — inheriting the generic `CRITICAL` of 0.85 that nothing set
for it specifically. Any pressure high enough for the band-2 arm (>= 1.0)
had already passed 0.85 several lines earlier, so band 1 returned first
and getting dressed was arbitrated alongside starving and exhaustion.

Inside band 1 the tie-break is profile ORDER, so depending on where
wardrobe sat in a given profile, a soul could elect to get dressed while
a critical body need was outstanding.

Latent when filed and still latent: every sampled soul shows wardrobe
pressure 0.0 today. The inversion was in the arbitration.
"""
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from world.souls import engine as engine_mod
from world.souls import needs as needs_mod


class _Arbitration(EvenniaTest):
    """Drives `_desired_goal` with the real thresholds and a controlled
    set of derived pressures."""

    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.soul.db.soul_schedule = "day"
        self.soul.db.soul_post = None
        self.soul.db.soul_home = None
        self.soul.db.patrol_beat = None

    def band_for(self, derived, profile=("hunger", "wardrobe", "rest")):
        with patch.object(needs_mod, "profile_of", return_value=profile), \
             patch.object(needs_mod, "pressures", return_value=dict(derived)):
            return engine_mod._desired_goal(self.soul, hour=10.0)


class TestGettingDressedIsNotSurvival(_Arbitration):

    def test_a_starving_soul_still_elects_band_one(self):
        """Control: band 1 still works. If it did not, the wardrobe
        assertions below would pass for the wrong reason."""
        band, goal = self.band_for({"hunger": 1.0, "wardrobe": 0.0,
                                    "rest": 0.0})
        self.assertEqual((band, goal), (1, "hunger"))

    def test_being_undressed_is_not_band_one(self):
        band, goal = self.band_for({"hunger": 0.0, "wardrobe": 1.0,
                                    "rest": 0.0})
        self.assertEqual(goal, "wardrobe")
        self.assertEqual(band, 2, "getting dressed is arbitrated as "
                                  "survival-critical")

    def test_hunger_beats_wardrobe_when_both_are_high(self):
        """The consequence of the inversion: inside band 1 the tie-break
        is profile ORDER, so a soul could dress while starving depending
        on where wardrobe sat in its profile."""
        band, goal = self.band_for({"hunger": 1.0, "wardrobe": 1.0,
                                    "rest": 0.0},
                                   profile=("wardrobe", "hunger"))
        self.assertEqual((band, goal), (1, "hunger"))

    def test_an_upgrade_is_still_elected_at_band_three(self):
        """`PROVISIONAL_PRESSURE` is 0.60 against a soft threshold of
        0.55 — a soul covered only by the paper decant issue must still
        go and find real clothes. Excluding wardrobe from band 1 must
        not have taken that with it."""
        band, goal = self.band_for(
            {"hunger": 0.0, "rest": 0.0,
             "wardrobe": needs_mod.PROVISIONAL_PRESSURE})
        self.assertEqual((band, goal), (3, "wardrobe"))

    def test_the_band_two_arm_is_reachable_at_all(self):
        """It was dead code: nothing could satisfy >= 1.0 without
        having passed 0.85 five lines earlier."""
        band, _goal = self.band_for({"hunger": 0.0, "wardrobe": 1.0,
                                     "rest": 0.0})
        self.assertEqual(band, 2)

    def test_safety_still_outranks_it(self):
        """"...but not before you stop bleeding." Band 0 is untouched."""
        band, goal = self.band_for({"safety": 1.0, "wardrobe": 1.0,
                                    "hunger": 0.0, "rest": 0.0})
        self.assertEqual((band, goal), (0, "safety"))
