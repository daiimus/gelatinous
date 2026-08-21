"""Personality as a cost structure (NPC_TRAITS_SPEC).

The load-bearing claim is the conscience rule: a plan a soul abhors is
reachable only under duress, so the gap between soft and critical IS
the personality. These pin that, the dials that reprice the planner,
and the wound that acting against yourself leaves behind.
"""
import time as _time
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.souls import needs as needs_mod
from world.souls import traits as traits_mod


class _TraitBase(BaseEvenniaTest):
    def _soul(self, *trait_keys, hunger=0.0, lawless=True):
        char = create_object("typeclasses.characters.Character",
                             key="Trait Subject", location=self.room1)
        char.tags.add("soul", category="npc_role")
        char.db.soul_traits = list(trait_keys)
        char.db.soul_lawless = lawless
        char.db.soul_needs = {"hunger": hunger, "_at": _time.time()}
        char.tokens = 0
        return char


class TestDials(_TraitBase):
    def test_rate_dials_compound_on_the_need(self):
        greedy = self._soul("ration_burner")
        plain = self._soul()
        # same elapsed time, hungrier sooner
        self.assertGreater(needs_mod.pressure(greedy, "hunger"),
                           needs_mod.pressure(plain, "hunger") - 1)
        self.assertAlmostEqual(
            traits_mod.dial(greedy, "rate:hunger", 1.0), 1.3, places=3)

    def test_threshold_dials_move_per_soul(self):
        craven = self._soul("flinch_coded")
        steady = self._soul("plate_nerved")
        self.assertLess(needs_mod.critical_for(craven, "safety"),
                        needs_mod.critical_for(steady, "safety"))

    def test_unset_dial_falls_back(self):
        plain = self._soul()
        self.assertEqual(traits_mod.dial(plain, "violence_gate", 0.25), 0.25)

    def test_dry_circuit_silences_the_misery_pull(self):
        sober = self._soul("dry_circuit")
        with patch("world.souls.thoughts.mood", return_value=-0.9):
            self.assertEqual(needs_mod.craving_pressure(sober), 0.0)

    def test_rustgut_reaches_sooner(self):
        drinker = self._soul("rustgut")
        with patch("world.souls.thoughts.mood", return_value=-0.9):
            self.assertAlmostEqual(needs_mod.craving_pressure(drinker),
                                   0.45, places=2)


class TestConscience(_TraitBase):
    """The duress rule — the whole point of the system."""

    def _hungry_mugger(self, *traits, hunger):
        soul = self._soul(*traits, hunger=hunger)
        mark = create_object("typeclasses.characters.Character",
                             key="A Mark", location=self.room1)
        mark.db.is_npc = True
        mark.tokens = 50
        return soul, mark

    def test_gentle_soul_will_not_rob_while_merely_hungry(self):
        from world.souls import actions

        soul, _mark = self._hungry_mugger("soft_handed", hunger=0.60)
        with patch("world.souls.thoughts.mood", return_value=-0.9), \
             patch.object(actions, "_advertisers", return_value=[]):
            self.assertIsNone(actions.plan_for(soul, "hunger"))

    def test_the_same_soul_robs_when_starving(self):
        from world.souls import actions

        soul, mark = self._hungry_mugger("soft_handed", hunger=0.99)
        with patch("world.souls.thoughts.mood", return_value=-0.9), \
             patch.object(actions, "_advertisers", return_value=[]), \
             patch.object(actions, "_find_mark", return_value=mark):
            plan = actions.plan_for(soul, "hunger")
        self.assertIsNotNone(plan)
        self.assertIn("violence", plan["ethos"])

    def test_a_soul_without_the_scruple_robs_at_soft(self):
        from world.souls import actions

        soul, mark = self._hungry_mugger(hunger=0.60)
        with patch("world.souls.thoughts.mood", return_value=-0.9), \
             patch.object(actions, "_advertisers", return_value=[]), \
             patch.object(actions, "_find_mark", return_value=mark):
            self.assertIsNotNone(actions.plan_for(soul, "hunger"))

    def test_hot_solder_opens_the_knife_at_a_brighter_mood(self):
        from world.souls import actions

        soul, mark = self._hungry_mugger("hot_solder", hunger=0.99)
        with patch("world.souls.thoughts.mood", return_value=0.35), \
             patch.object(actions, "_advertisers", return_value=[]), \
             patch.object(actions, "_find_mark", return_value=mark):
            self.assertIsNotNone(actions.plan_for(soul, "hunger"))
        plain, mark2 = self._hungry_mugger(hunger=0.99)
        with patch("world.souls.thoughts.mood", return_value=0.35), \
             patch.object(actions, "_advertisers", return_value=[]), \
             patch.object(actions, "_find_mark", return_value=mark2):
            self.assertIsNone(actions.plan_for(plain, "hunger"))


class TestTheWound(_TraitBase):
    def test_acting_against_nature_leaves_a_wound(self):
        from world.souls import jobs, thoughts

        soul = self._soul("soft_handed")
        jobs._conscience(soul, {"ethos": ("violence", "theft")})
        keys = [t[1] for t in (soul.db.soul_thoughts or [])]
        self.assertIn("against_my_nature", keys)
        self.assertLess(thoughts.mood(soul), -0.2)

    def test_living_up_to_it_warms_instead(self):
        from world.souls import jobs, thoughts

        soul = self._soul("greenhaus_handed")
        jobs._conscience(soul, {"ethos": ("care",)})
        keys = [t[1] for t in (soul.db.soul_thoughts or [])]
        self.assertIn("felt_like_myself", keys)
        self.assertGreater(thoughts.mood(soul), 0)

    def test_a_wound_outlasts_an_ordinary_thought(self):
        from world.souls import thoughts

        soul = self._soul("soft_handed")
        long_ago = _time.time() - 12 * 3600
        soul.db.soul_thoughts = [
            (long_ago, "against_my_nature", -0.35, "what I did"),
            (long_ago, "went_hungry", -0.35, "no food"),
        ]
        felt = {t[1]: abs(t[0]) for t in thoughts.decayed(soul)}
        self.assertGreater(felt["against_my_nature"], felt["went_hungry"])

    def test_charged_once_per_deed(self):
        from world.souls import jobs

        soul = self._soul("soft_handed")
        job = {"ethos": ("violence",)}
        jobs._conscience(soul, job)
        jobs._conscience(soul, job)
        wounds = [t for t in (soul.db.soul_thoughts or [])
                  if t[1] == "against_my_nature"]
        self.assertEqual(len(wounds), 1)


class TestRolling(BaseEvenniaTest):
    def test_rolls_are_exclusion_safe(self):
        for _ in range(60):
            picked = traits_mod.roll()
            self.assertIn(len(picked), (2, 3))
            for key in picked:
                blocked = traits_mod.TRAITS[key].get("excludes") or set()
                self.assertFalse(set(picked) & set(blocked))

    def test_curated_singletons_are_never_rolled(self):
        for _ in range(60):
            self.assertNotIn("wire_loved", traits_mod.roll())

    def test_the_rook_may_still_carry_hers(self):
        char = create_object("typeclasses.characters.Character",
                             key="the Rook", location=self.room1)
        char.db.soul_traits = ["wire_loved"]
        self.assertEqual(traits_mod.labels(char), ["Wire-Loved"])


class TestDefects(BaseEvenniaTest):
    """A machine has no personality; it has wear (#2136)."""

    def _bot(self, *keys):
        bot = create_object("typeclasses.characters.Character",
                            key="A Secbot", location=self.room1)
        bot.tags.add("soul", category="npc_role")
        bot.db.soul_profile = "robot"
        bot.db.soul_traits = list(keys)
        return bot

    def test_a_machine_reads_from_the_defect_book(self):
        bot = self._bot("ghost_contact")
        self.assertIs(traits_mod.registry_for(bot), traits_mod.DEFECTS)
        self.assertEqual(traits_mod.labels(bot), ["Ghost Contact"])

    def test_a_person_reads_from_the_trait_book(self):
        char = create_object("typeclasses.characters.Character",
                             key="A Person", location=self.room1)
        char.db.soul_traits = ["rustgut"]
        self.assertIs(traits_mod.registry_for(char), traits_mod.TRAITS)

    def test_human_traits_do_not_apply_to_a_machine(self):
        """The secbot that rolled Dry Circuit was noise: a machine
        carrying a human trait key simply carries nothing."""
        bot = self._bot("dry_circuit", "faraday_souled")
        self.assertEqual(traits_mod.labels(bot), [])

    def test_defects_reprice_the_machine(self):
        jumpy = self._bot("ghost_contact")
        self.assertLess(needs_mod.critical_for(jumpy, "safety"),
                        needs_mod.CRITICAL)

    def test_neglect_earns_one_and_service_removes_it(self):
        bot = self._bot()
        got = traits_mod.acquire_defect(bot)
        self.assertIn(got, traits_mod.DEFECTS)
        self.assertEqual(list(bot.db.soul_traits), [got])
        self.assertEqual(traits_mod.clear_defect(bot), got)
        self.assertEqual(list(bot.db.soul_traits), [])

    def test_a_unit_can_only_get_so_broken(self):
        bot = self._bot()
        for _ in range(10):
            traits_mod.acquire_defect(bot)
        self.assertLessEqual(len(bot.db.soul_traits),
                             traits_mod.DEFECT_CAP)

    def test_contradictory_faults_are_never_stacked(self):
        bot = self._bot("sticky_directive")
        for _ in range(10):
            traits_mod.acquire_defect(bot)
        self.assertNotIn("slack_directive", bot.db.soul_traits)
