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
        # Issue #234: preserved gender / name snapshot.
        corpse.db.original_gender = "male"
        corpse.db.original_character_name = "Jdoe"
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
        app.db.original_gender = None
        app.db.original_character_name = None
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
        # Condition prefix is no longer prepended (overbearing
        # redundant signal — decay-tier prose already conveys
        # freshness).  Just confirm desc contains location prose.
        self.assertNotIn("specimen", app.db.desc)

    def test_damaged_right_thigh_populates_desc(self):
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="right_thigh", condition="damaged",
            corpse=self._fake_corpse(stage="moderate"),
        )
        self.assertTrue(app.db.desc)
        self.assertIn("right thigh", app.db.desc.lower())
        self.assertNotIn("specimen", app.db.desc)

    def test_putrid_head_populates_desc(self):
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="head", condition="putrid",
            corpse=self._fake_corpse(stage="advanced"),
        )
        self.assertTrue(app.db.desc)
        self.assertIn("head", app.db.desc.lower())
        self.assertNotIn("specimen", app.db.desc)

    def test_unknown_location_leaves_desc_untouched(self):
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="tentacle", condition="pristine",
            corpse=self._fake_corpse(),
        )
        # No registered prose for an unknown location + condition
        # prefix is no longer surfaced → desc stays empty.
        self.assertNotIn("specimen", app.db.desc or "")

    def test_key_still_assigned_alongside_desc(self):
        # Regression guard for the species-aware key path.
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="left_arm", condition="pristine",
            corpse=self._fake_corpse(),
        )
        # Fresh corpse → "human left arm" via species helper.
        self.assertEqual(app.key, "human left arm")

    def test_gender_and_name_snapshotted_from_corpse(self):
        # Issue #234: configure_from_sever must carry the preserved
        # gender + name so return_appearance can resolve pronoun tokens.
        app = self._fake_appendage()
        app.configure_from_sever(
            location_name="left_arm", condition="pristine",
            corpse=self._fake_corpse(),
        )
        self.assertEqual(app.db.original_gender, "male")
        self.assertEqual(app.db.original_character_name, "Jdoe")


class TestAppendageDecay(TestCase):
    """Severed limbs decay after they leave the body — the decay clock
    now lives on the ``Appendage`` base (lifted from ``SeveredHead``), so
    flesh limbs advance through the tiers instead of staying frozen at
    their sever-moment name.  Cyber limbs stay frozen: chrome doesn't
    rot, and its degradation rides the future preservation model.
    """

    def _fake_limb(self, *, location_name="left_arm", chain=None,
                   creation_time=None, species="human"):
        import time
        from typeclasses.items import Appendage

        class _DB:
            pass

        limb = type("FakeLimb", (), {})()
        limb.db = _DB()
        limb.db.location_name = location_name
        limb.db.chain = chain or [location_name]
        limb.db.source_species = species
        limb.db.creation_time = (
            creation_time if creation_time is not None else time.time()
        )
        limb.key = ""
        limb._DECAY_STAGES = Appendage._DECAY_STAGES
        for name in ("get_decay_stage", "_current_decay_key",
                     "_refresh_decay_key_if_changed"):
            setattr(limb, name, getattr(Appendage, name).__get__(limb))
        return limb

    def test_stage_advances_with_age(self):
        import time
        limb = self._fake_limb(creation_time=time.time())
        self.assertEqual(limb.get_decay_stage(), "fresh")
        # Backdate the clock past the advanced threshold → terminal skeletal.
        limb.db.creation_time = time.time() - 700000
        self.assertEqual(limb.get_decay_stage(), "skeletal")

    def test_refresh_advances_key_to_current_tier(self):
        import time
        limb = self._fake_limb(creation_time=time.time())
        limb._refresh_decay_key_if_changed()
        fresh_key = limb.key
        self.assertIn("left arm", fresh_key.lower())
        # Age to skeletal and refresh — the key advances, location words stay.
        limb.db.creation_time = time.time() - 700000
        limb._refresh_decay_key_if_changed()
        self.assertNotEqual(limb.key, fresh_key)
        self.assertIn("left arm", limb.key.lower())
        self.assertIn("skeletal", limb.key.lower())

    def test_compound_chain_decays_as_one_name(self):
        import time
        limb = self._fake_limb(
            location_name="left_thigh",
            chain=["left_thigh", "left_shin", "left_foot"],
            creation_time=time.time() - 700000,
        )
        limb._refresh_decay_key_if_changed()
        # Compound leg name, not the bare thigh.
        self.assertIn("left leg", limb.key.lower())

    def test_cyber_limb_does_not_decay(self):
        import time
        from unittest.mock import patch
        limb = self._fake_limb(creation_time=time.time() - 700000)
        limb.key = "cybernetic left arm"
        with patch(
            "world.medical.procedures.is_cybernetic_limb", return_value=True,
        ):
            limb._refresh_decay_key_if_changed()
        # Chrome doesn't rot — frozen name preserved.
        self.assertEqual(limb.key, "cybernetic left arm")
