"""Species wound-prose packs (SPECIES_AUTHORING §wounds).

A robot tears and weeps amber hydraulic fluid; a synth bleeds cobalt and
scars to pearlescent seams. A species with a registered pack NEVER falls
through to human flesh prose, at any stage; humans and pack-less species
are byte-identical to before.
"""

from types import SimpleNamespace
from unittest import TestCase

from world.medical.wounds import messages
from world.medical.wounds.wound_descriptions import get_wound_description

#: Human-flesh vocabulary that must never appear on a robot chassis.
FLESH_WORDS = ("blood", "bleed", "flesh", "tissue", "skin", "bruis",
               "stitch", "sutur", "scab")

STAGES = ("fresh", "treated", "healing", "scarred", "destroyed")


def _char(species=None, skintone=None):
    return SimpleNamespace(
        species=species,
        db=SimpleNamespace(species=species, skintone=skintone),
    )


class TestPackRegistry(TestCase):
    def test_robot_and_synth_registered(self):
        self.assertIs(messages.species_pack(_char("robot")), messages.robot)
        self.assertIs(messages.species_pack(_char("synthetic_humanoid")),
                      messages.synth)

    def test_human_and_packless_get_none(self):
        self.assertIsNone(messages.species_pack(_char(None)))
        self.assertIsNone(messages.species_pack(_char("human")))
        self.assertIsNone(messages.species_pack(_char("rat")))
        self.assertIsNone(messages.species_pack(None))

    def test_packs_complete_across_all_stages(self):
        # The no-leak guarantee rests on completeness — every stage authored.
        for pack in messages.SPECIES_PACKS.values():
            for stage in STAGES:
                self.assertTrue(pack.WOUND_DESCRIPTIONS.get(stage),
                                f"{pack.__name__} missing stage {stage!r}")


class TestRobotProse(TestCase):
    def test_no_flesh_vocabulary_at_any_stage(self):
        bot = _char("robot")
        for stage in STAGES:
            for injury in ("cut", "bullet", "blunt", "stab"):
                for _ in range(12):   # cover the random template choices
                    desc = get_wound_description(
                        injury, "chest", "Severe", stage, character=bot)
                    low = desc.lower()
                    for word in FLESH_WORDS:
                        self.assertNotIn(
                            word, low,
                            f"flesh word {word!r} on a robot ({stage}): {desc}")

    def test_fresh_damage_reads_mechanical(self):
        bot = _char("robot")
        seen = " ".join(
            get_wound_description("cut", "chest", "Severe", "fresh",
                                  character=bot)
            for _ in range(20)).lower()
        self.assertTrue(any(w in seen for w in
                            ("plating", "servo", "hydraulic", "chassis",
                             "panel", "scorch")), seen[:200])

    def test_destroyed_eye_is_an_optic(self):
        bot = _char("robot")
        desc = get_wound_description("blunt", "left_eye", "Critical",
                                     "destroyed", character=bot).lower()
        self.assertIn("optic", desc)


class TestSynthProse(TestCase):
    def test_fresh_blood_is_cobalt_never_crimson(self):
        synth = _char("synthetic_humanoid")
        for _ in range(20):
            desc = get_wound_description("cut", "chest", "Moderate", "fresh",
                                         character=synth)
            self.assertNotIn("|R", desc)     # human crimson code
        seen = " ".join(
            get_wound_description("cut", "chest", "Moderate", "fresh",
                                  character=synth)
            for _ in range(20)).lower()
        self.assertTrue("cobalt" in seen or "slate" in seen, seen[:200])

    def test_scars_read_engineered(self):
        synth = _char("synthetic_humanoid")
        seen = " ".join(
            get_wound_description("cut", "chest", "Light", "scarred",
                                  character=synth)
            for _ in range(20)).lower()
        self.assertTrue(any(w in seen for w in
                            ("pearlescent", "opaline", "lacquer")), seen[:200])


class TestHumanUnchanged(TestCase):
    def test_human_fresh_cut_comes_from_the_cut_module(self):
        human = _char(None)
        for _ in range(10):
            desc = get_wound_description("cut", "chest", "Severe", "fresh",
                                         character=human)
            self.assertIn("|R", desc)        # human crimson prose intact

    def test_packless_species_uses_shared_modules(self):
        rat = _char("rat")
        desc = get_wound_description("cut", "chest", "Severe", "fresh",
                                     character=rat)
        self.assertIn("|R", desc)            # falls to the shared tables


class TestCompoundRouting(TestCase):
    def test_robot_compound_is_mechanical(self):
        from world.medical.wounds.longdesc_hooks import (
            _resolve_compound_template,
        )
        bot = _char("robot")
        for stage in ("fresh", "treated", "healing", "scarred"):
            template = _resolve_compound_template("cut", stage, bot)
            self.assertIsNotNone(template, stage)
            for word in FLESH_WORDS:
                self.assertNotIn(word, template.lower(), template)

    def test_human_compound_unchanged(self):
        from world.medical.wounds.longdesc_hooks import (
            _resolve_compound_template,
        )
        template = _resolve_compound_template("cut", "fresh", _char(None))
        self.assertIsNotNone(template)


class PacksAnswerByInjuryType(TestCase):
    """#3512: a blow, a bullet and a blade no longer share one cobalt cut."""
    INJURIES = ("blunt", "bullet", "stab", "laceration", "burn", "cut")
    HEAL_STAGES = ("fresh", "treated", "healing", "scarred")

    def test_every_pack_authors_every_injury_type(self):
        for name, pack in messages.SPECIES_PACKS.items():
            by = getattr(pack, "BY_INJURY", None) or {}
            for inj in self.INJURIES:
                for stage in self.HEAL_STAGES:
                    self.assertTrue((by.get(inj) or {}).get(stage), f"{name}: {inj}/{stage} unauthored")
            comp = getattr(pack, "COMPOUND_BY_INJURY", None) or {}
            for inj in self.INJURIES:
                self.assertTrue((comp.get(inj) or {}).get("fresh"), f"{name}: compound {inj} unauthored")

    def test_a_synth_blunt_wound_is_not_a_cut(self):
        synth = _char("synthetic_humanoid")
        seen = [get_wound_description("blunt", "left_arm", "Severe", "fresh", character=synth) for _ in range(30)]
        for desc in seen:
            low = desc.lower()
            for word in ("cut ", "gash", "puncture", "rent ", "slice"):
                self.assertNotIn(word, low, f"blunt read as a cut on a synth: {desc}")
        self.assertTrue(any(w in " ".join(seen).lower() for w in ("bloom", "pool", "dent", "crush", "impact", "blow", "subdermal", "swell", "bruise")), seen[:3])

    def test_a_robot_blunt_wound_dents_and_never_bleeds(self):
        bot = _char("robot")
        seen = [get_wound_description("blunt", "chest", "Severe", "fresh", character=bot) for _ in range(30)]
        joined = " ".join(seen).lower()
        for word in FLESH_WORDS:
            self.assertNotIn(word, joined)
        self.assertTrue(any(w in joined for w in ("dent", "crumpl", "caved", "buckl", "sprung", "seam")), seen[:3])

    def test_injury_types_are_distinguishable_on_a_synth(self):
        synth = _char("synthetic_humanoid")
        pools = {inj: set(get_wound_description(inj, "chest", "Severe", "fresh", character=synth) for _ in range(40)) for inj in self.INJURIES}
        for a in self.INJURIES:
            for b in self.INJURIES:
                if a < b:
                    self.assertFalse(pools[a] & pools[b], f"{a} and {b} share fresh lines on a synth")

    def test_every_authored_template_renders(self):
        sample = dict(severity="serious", location="left arm", skintone="", suture_color="|K", bandage_color="|W",
                      medical_tape_color="", medical_staple_color="", ice_pack_color="", compression_wrap_color="",
                      antiseptic_color="", iodine_color="", organ="", injury_type="")
        for name, pack in messages.SPECIES_PACKS.items():
            for table, extra in ((getattr(pack, "BY_INJURY", {}) or {}, {}),
                                 (getattr(pack, "COMPOUND_BY_INJURY", {}) or {}, {"others_phrase": "another wound"})):
                for inj, stages in table.items():
                    for stage, lines in stages.items():
                        for line in lines:
                            try:
                                line.format(**sample, **extra)
                            except (KeyError, IndexError, ValueError) as exc:
                                self.fail(f"{name} {inj}/{stage}: {exc}: {line}")

    def test_an_unknown_type_on_a_synth_is_never_a_cut(self):
        """#3514: a damage type added without a bank reads plainly, not as cobalt cut prose."""
        synth = _char("synthetic_humanoid")
        for _ in range(10):
            desc = get_wound_description("plasma", "left_arm", "Severe", "fresh", character=synth)
            self.assertEqual(desc, "a severe plasma wound on the left arm")

