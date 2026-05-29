"""Tests for severed-part default descriptions (PR #204).

Covers :data:`world.anatomy.severed_parts.SEVERED_PART_DESCRIPTIONS`
and the lookup helper, plus the
:meth:`typeclasses.items.Appendage.configure_from_sever` contract that
``self.db.desc`` is populated at sever-time so the standard Evennia
renderer slots the prose into the look output naturally.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    SEVERED_PART_DESCRIPTIONS,
    get_severed_part_description,
)
from world.combat.constants import SEVERABLE_CONTAINERS


class TestSeveredPartCoverage(TestCase):
    """Every severable location must have prose for all 3 conditions."""

    def test_human_table_registered(self):
        self.assertIn("human", SEVERED_PART_DESCRIPTIONS)

    def test_every_severable_location_has_human_entry(self):
        human = SEVERED_PART_DESCRIPTIONS["human"]
        missing = sorted(SEVERABLE_CONTAINERS - set(human.keys()))
        self.assertEqual(
            missing, [],
            f"Severable locations missing from human prose table: {missing}",
        )

    def test_every_human_entry_covers_three_conditions(self):
        required_conditions = {"pristine", "damaged", "putrid"}
        for location, entry in SEVERED_PART_DESCRIPTIONS["human"].items():
            missing = required_conditions - set(entry.keys())
            self.assertEqual(
                missing, set(),
                f"{location} missing conditions: {missing}",
            )

    def test_descriptions_are_non_empty_strings(self):
        for location, entry in SEVERED_PART_DESCRIPTIONS["human"].items():
            for condition, prose in entry.items():
                self.assertIsInstance(
                    prose, str,
                    f"{location}/{condition} prose is not a string",
                )
                self.assertGreater(
                    len(prose.strip()), 0,
                    f"{location}/{condition} prose is empty",
                )


class TestSeveredPartHelper(TestCase):
    def test_returns_prose_for_known_tuple(self):
        prose = get_severed_part_description("human", "left_arm", "pristine")
        self.assertTrue(prose)
        self.assertIn("left arm", prose.lower())

    def test_returns_empty_for_unknown_location(self):
        self.assertEqual(
            get_severed_part_description("human", "tentacle", "pristine"),
            "",
        )

    def test_returns_empty_for_unknown_condition(self):
        # ``refuse`` is the harvest-only condition; severance never
        # produces it, but a defensive caller might pass it anyway.
        self.assertEqual(
            get_severed_part_description("human", "left_arm", "refuse"),
            "",
        )

    def test_unknown_species_falls_back_to_human(self):
        prose = get_severed_part_description("synth", "head", "pristine")
        # Falls back to the human entry, which is registered.
        self.assertTrue(prose)

    def test_none_species_falls_back_to_human(self):
        prose = get_severed_part_description(None, "head", "pristine")
        self.assertTrue(prose)


class TestAppendageConfigureFromSeverPopulatesDesc(TestCase):
    """PR #204: ``configure_from_sever`` must seed ``db.desc``.

    Same Evennia-standard contract as Organ: the engine renderer
    handles ``db.desc``; ``Appendage.return_appearance`` composes
    additional dynamic prose (wound + longdesc carry-forward) on top
    of the engine-rendered base.
    """

    def _fake_corpse(self, species="human", stage="fresh"):
        class _DB:
            pass

        corpse = type("FakeCorpse", (), {})()
        corpse.db = _DB()
        corpse.db.signature_at_death = ("uid", "tall", "lean", "hooded", ())
        corpse.db.apparent_uid_at_death = "hash-abc"
        corpse.db.species = species
        corpse.dbref = "#42"
        # Per-location longdesc / wounds tables consumed by the
        # carry-forward overlay; empty is fine for desc-only tests.
        corpse.db.longdesc = {}
        corpse.db.longdesc_data = {}
        corpse.db.wounds = []
        corpse.db.wounds_at_death = []
        corpse.db.severed_locations = []
        corpse._stage = stage

        def get_decay_stage():
            return corpse._stage

        corpse.get_decay_stage = get_decay_stage
        return corpse

    def _fake_appendage(self):
        from typeclasses.items import Appendage

        class _DB:
            pass

        app = type("FakeAppendage", (), {})()
        app.db = _DB()
        app.db.location_name = ""
        app.db.condition = "pristine"
        app.db.source_signature = None
        app.db.source_apparent_uid = None
        app.db.source_corpse_dbref = None
        app.db.source_species = "human"
        app.db.wounds_at_death = []
        app.db.longdesc_data = {}
        app.db.desc = None
        app.key = ""
        app.configure_from_sever = (
            Appendage.configure_from_sever.__get__(app)
        )
        return app

    def test_pristine_left_arm_populates_desc(self):
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="left_arm", condition="pristine",
            corpse=self._fake_corpse(),
        )
        self.assertTrue(app.db.desc)
        self.assertIn("left arm", app.db.desc.lower())
        # Issue #221 / #223 / #225: plain sentence joined to prose with
        # a single space (one continuous paragraph).
        self.assertTrue(
            app.db.desc.startswith("It is a pristine specimen. ")
        )

    def test_damaged_right_thigh_populates_desc(self):
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="right_thigh", condition="damaged",
            corpse=self._fake_corpse(stage="moderate"),
        )
        self.assertTrue(app.db.desc)
        self.assertIn("right thigh", app.db.desc.lower())
        self.assertTrue(
            app.db.desc.startswith("It is a damaged specimen. ")
        )

    def test_putrid_head_populates_desc(self):
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="head", condition="putrid",
            corpse=self._fake_corpse(stage="advanced"),
        )
        self.assertTrue(app.db.desc)
        self.assertIn("head", app.db.desc.lower())
        self.assertTrue(
            app.db.desc.startswith("It is a putrid specimen. ")
        )

    def test_unknown_location_leaves_desc_untouched(self):
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="tentacle", condition="pristine",
            corpse=self._fake_corpse(),
        )
        # Issue #221: even without registered prose, the condition
        # sentence alone surfaces — a meaningful freshness signal.
        self.assertEqual(app.db.desc, "It is a pristine specimen.")

    def test_key_still_assigned_alongside_desc(self):
        # Regression guard for the species-aware key path.
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="left_arm", condition="pristine",
            corpse=self._fake_corpse(),
        )
        # Fresh corpse → "human left arm" via species helper.
        self.assertEqual(app.key, "human left arm")
