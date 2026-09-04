"""The slowboat manifest (#2138).

Pins the chart's reserved corners (Command and Commander are never
rolled), the rank banding, the owner's check-value formula, and that
the score sheet actually prints a designation.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world import manifest as manifest_mod


class TestTheChart(EvenniaCommandTest):
    def test_command_is_never_rolled(self):
        for _ in range(200):
            self.assertNotEqual(
                manifest_mod.roll_designation()["dept"], "command")

    def test_commander_is_never_rolled(self):
        for _ in range(200):
            self.assertNotEqual(
                manifest_mod.roll_designation()["rank"], "commander")

    def test_command_still_exists_on_the_chart(self):
        """Reserved, not deleted — its story arrives as artifacts."""
        self.assertIn("command", manifest_mod.DEPARTMENTS)
        self.assertIn("command", manifest_mod.DEPARTMENT_SKILLS)

    def test_every_vessel_has_a_name(self):
        for registry, name in manifest_mod.VESSELS.items():
            self.assertTrue(registry.startswith("SBL-"))
            self.assertTrue(name)

    def test_every_department_rates_real_skills(self):
        for dept, skills in manifest_mod.DEPARTMENT_SKILLS.items():
            self.assertIn(dept, manifest_mod.DEPARTMENTS)
            for skill in skills:
                self.assertIn(skill, manifest_mod.SKILLS)


class TestSeeding(EvenniaCommandTest):
    def test_a_crewman_is_rated_for_their_department(self):
        des = {"vessel": "SBL-0117", "dept": "medical", "rank": "crewman"}
        skills = manifest_mod.seed_skills(des)
        self.assertIn("medicine", skills)
        self.assertIn("chemistry", skills)

    def test_rank_bands_the_core_ratings(self):
        crew = manifest_mod.seed_skills(
            {"dept": "security", "rank": "crewman"})
        officer = manifest_mod.seed_skills(
            {"dept": "security", "rank": "officer"})
        self.assertLess(max(crew["firearms"], crew["unarmed"]),
                        min(officer["firearms"], officer["unarmed"]))

    def test_nobody_is_only_their_job(self):
        des = {"dept": "medical", "rank": "crewman"}
        skills = manifest_mod.seed_skills(des)
        core = set(manifest_mod.DEPARTMENT_SKILLS["medical"])
        self.assertTrue(set(skills) - core)


class TestValues(EvenniaCommandTest):
    def test_letters_span_the_scale(self):
        self.assertEqual(manifest_mod.letter_for(0), "Z")
        self.assertEqual(manifest_mod.letter_for(3), "Y")
        self.assertEqual(manifest_mod.letter_for(150), "A")

    def test_check_value_averages_the_governing_stats(self):
        self.char1.db.skills = {"medicine": 70}
        self.char1.intellect = 40
        self.char1.motorics = 20
        # 70 + (40 + 20) / 2
        self.assertAlmostEqual(
            manifest_mod.check_value(self.char1, "medicine"), 100.0)

    def test_a_cant_weights_the_stat_that_should_dominate(self):
        self.char1.db.skills = {"unarmed": 50}
        self.char1.grit = 60
        self.char1.motorics = 30
        # 50 + (2*60 + 30) / 3
        self.assertAlmostEqual(
            manifest_mod.check_value(self.char1, "unarmed"), 100.0)

    def test_unrated_is_none_not_zero(self):
        self.char1.db.skills = {}
        self.assertIsNone(manifest_mod.check_value(self.char1, "piloting"))

    def test_only_held_ratings_are_listed(self):
        self.char1.db.skills = {"medicine": 70, "piloting": 40}
        labels = [row[0] for row in manifest_mod.rated_skills(self.char1)]
        self.assertEqual(labels, ["Medicine", "Piloting"])   # best first


class TestTheSheet(EvenniaCommandTest):
    def test_score_prints_the_designation(self):
        self.char1.db.designation = {"vessel": "SBL-0117",
                                     "dept": "life_systems",
                                     "rank": "chief"}
        self.char1.db.skills = {"agrotech": 95}
        out = self.call(
            __import__("commands.CmdCharacter", fromlist=["x"]).CmdStats(),
            "")
        self.assertIn("Chief, Life Systems", out)
        self.assertIn("Halcyon Days", out)
        self.assertIn("Agrotech", out)

    def test_a_character_with_no_record_says_so(self):
        self.char1.db.designation = None
        self.char1.db.skills = {}
        out = self.call(
            __import__("commands.CmdCharacter", fromlist=["x"]).CmdStats(),
            "")
        self.assertIn("NONE ON FILE", out)


class TestTheReservationIsGuarded(EvenniaCommandTest):
    """`roll_designation`'s docstring says "Never Command, and never
    Commander -- both are reserved, and Command is meant to stay empty".
    The reservation was enforced by the POOLS, which both parameters
    bypassed verbatim, so the function could return exactly the thing it
    says never happens (#2800)."""

    def test_a_reserved_department_is_refused(self):
        from world.manifest import ROLLABLE, roll_designation
        for _ in range(20):
            d = roll_designation(dept="command")
            self.assertIn(d["dept"], ROLLABLE)

    def test_a_reserved_rank_is_refused(self):
        from world.manifest import ROLLABLE_RANKS, roll_designation
        for _ in range(20):
            d = roll_designation(rank="commander")
            self.assertIn(d["rank"], ROLLABLE_RANKS)

    def test_a_legitimate_override_still_works(self):
        """The pin: the parameters exist to author somebody
        deliberately, and must keep doing that."""
        from world.manifest import roll_designation
        d = roll_designation(dept="medical", rank="chief")
        self.assertEqual(d["dept"], "medical")
        self.assertEqual(d["rank"], "chief")

    def test_junk_falls_back_to_a_roll(self):
        from world.manifest import ROLLABLE, roll_designation
        d = roll_designation(dept="banana")
        self.assertIn(d["dept"], ROLLABLE)
