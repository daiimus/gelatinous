"""Tests for organ display metadata (PR #202 / PR-G).

Covers :data:`world.anatomy.organs.ORGAN_DISPLAY` and the two
lookup helpers (``get_organ_display_name``,
``get_organ_default_description``).  Schema + coverage checks plus a
spot-check on the Organ typeclass key formatting at harvest time.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    ORGAN_DISPLAY,
    get_organ_default_description,
    get_organ_display_name,
)
from world.medical.constants import ORGANS


class TestOrganDisplayCoverage(TestCase):
    """Every harvestable organ must have display metadata registered."""

    def test_every_harvestable_organ_has_display_entry(self):
        missing = []
        for organ_name, data in ORGANS.items():
            if data.get("can_be_harvested"):
                if organ_name not in ORGAN_DISPLAY:
                    missing.append(organ_name)
        self.assertEqual(
            missing, [],
            f"Harvestable organs missing ORGAN_DISPLAY entries: {missing}",
        )

    def test_every_display_entry_has_required_keys(self):
        for organ_name, entry in ORGAN_DISPLAY.items():
            self.assertIn(
                "display_name", entry,
                f"{organ_name} missing display_name",
            )
            self.assertIn(
                "default_descriptions", entry,
                f"{organ_name} missing default_descriptions",
            )

    def test_every_display_entry_covers_three_conditions(self):
        required_conditions = {"pristine", "damaged", "putrid"}
        for organ_name, entry in ORGAN_DISPLAY.items():
            descs = entry.get("default_descriptions", {})
            missing = required_conditions - set(descs.keys())
            self.assertEqual(
                missing, set(),
                f"{organ_name} missing conditions: {missing}",
            )

    def test_descriptions_are_non_empty_strings(self):
        for organ_name, entry in ORGAN_DISPLAY.items():
            for condition, prose in entry["default_descriptions"].items():
                self.assertIsInstance(
                    prose, str,
                    f"{organ_name}/{condition} prose is not a string",
                )
                self.assertGreater(
                    len(prose.strip()), 0,
                    f"{organ_name}/{condition} prose is empty",
                )


class TestOrganDisplayHelpers(TestCase):
    def test_get_display_name_known_organ(self):
        self.assertEqual(get_organ_display_name("heart"), "heart")
        self.assertEqual(
            get_organ_display_name("left_kidney"), "left kidney"
        )

    def test_get_display_name_unknown_organ_falls_back(self):
        # Unregistered organs fall back to underscore-stripped key.
        self.assertEqual(
            get_organ_display_name("flux_capacitor"), "flux capacitor"
        )

    def test_get_default_description_returns_prose(self):
        prose = get_organ_default_description("heart", "pristine")
        self.assertTrue(prose)
        self.assertIn("heart", prose.lower())

    def test_get_default_description_unknown_organ_returns_empty(self):
        self.assertEqual(
            get_organ_default_description("flux_capacitor", "pristine"),
            "",
        )

    def test_get_default_description_unknown_condition_returns_empty(self):
        # ``refuse`` (skeletal-stage harvest) is intentionally absent —
        # the harvest command refuses skeletal corpses upstream.
        self.assertEqual(
            get_organ_default_description("heart", "refuse"), ""
        )


class TestOrganConfigureFromHarvestPopulatesDesc(TestCase):
    """PR #204: ``configure_from_harvest`` must seed ``db.desc``.

    Verifies the Evennia-standard contract: the engine's normal
    ``return_appearance`` renderer picks up ``db.desc`` and slots it
    into the look output.  No custom ``return_appearance`` override
    is required (or wanted).
    """

    def _fake_corpse(self, species="human"):
        """Minimal duck-typed corpse for ``configure_from_harvest``."""

        class _DB:
            pass

        corpse = type("FakeCorpse", (), {})()
        corpse.db = _DB()
        corpse.db.signature_at_death = ("uid", "tall", "lean", "hooded", ())
        corpse.db.apparent_uid_at_death = "hash-abc"
        corpse.db.species = species
        corpse.dbref = "#42"
        return corpse

    def _fake_organ(self):
        """Stub with a ``db`` namespace; binds the unbound configure method."""
        from typeclasses.items import Organ

        class _DB:
            pass

        organ = type("FakeOrgan", (), {})()
        organ.db = _DB()
        organ.db.organ_name = ""
        organ.db.condition = "pristine"
        organ.db.source_signature = None
        organ.db.source_apparent_uid = None
        organ.db.source_corpse_dbref = None
        organ.db.source_species = "human"
        organ.db.desc = None
        # Track key assignment.
        organ.key = ""
        organ.configure_from_harvest = (
            Organ.configure_from_harvest.__get__(organ)
        )
        return organ

    def test_registered_organ_populates_desc(self):
        organ = self._fake_organ()
        organ.configure_from_harvest(
            organ_name="heart", condition="pristine",
            corpse=self._fake_corpse(),
        )
        self.assertTrue(organ.db.desc)
        self.assertIn("heart", organ.db.desc.lower())
        # Issue #221 / #223: plain condition sentence prepended above
        # the prose, single newline (no blank-line gap).
        self.assertTrue(
            organ.db.desc.startswith("It is a pristine specimen.\n")
        )

    def test_damaged_condition_uses_damaged_prose(self):
        organ = self._fake_organ()
        organ.configure_from_harvest(
            organ_name="liver", condition="damaged",
            corpse=self._fake_corpse(),
        )
        self.assertTrue(organ.db.desc)
        # Damaged prose typically signals decay-onset vocabulary.
        self.assertIn("liver", organ.db.desc.lower())
        self.assertTrue(
            organ.db.desc.startswith("It is a damaged specimen.\n")
        )

    def test_putrid_condition_uses_putrid_prose(self):
        organ = self._fake_organ()
        organ.configure_from_harvest(
            organ_name="brain", condition="putrid",
            corpse=self._fake_corpse(),
        )
        self.assertTrue(organ.db.desc)
        self.assertIn("brain", organ.db.desc.lower())
        self.assertTrue(
            organ.db.desc.startswith("It is a putrid specimen.\n")
        )

    def test_unknown_organ_leaves_desc_untouched(self):
        organ = self._fake_organ()
        organ.configure_from_harvest(
            organ_name="flux_capacitor", condition="pristine",
            corpse=self._fake_corpse(),
        )
        # Issue #221: even when no prose is registered, the condition
        # sentence alone surfaces so the player gets *some* freshness
        # signal in the look output.
        self.assertEqual(organ.db.desc, "It is a pristine specimen.")

    def test_refuse_condition_leaves_desc_untouched(self):
        organ = self._fake_organ()
        organ.configure_from_harvest(
            organ_name="heart", condition="refuse",
            corpse=self._fake_corpse(),
        )
        # ``refuse`` has no registered prose AND no sentence (issue #221:
        # defensive empty for gameplay-internal conditions); preserve
        # engine default.
        self.assertIsNone(organ.db.desc)

    def test_key_still_assigned_alongside_desc(self):
        # Regression guard: the desc plumbing must not skip the
        # display-key assignment that the rest of the system reads.
        # Issue #212: key is now species-qualified, decay-modulated
        # via ``get_species_organ_name`` — fake corpse lacks
        # ``get_decay_stage`` so the configure helper falls back to
        # the ``fresh`` template (``{species} {organ}``).
        organ = self._fake_organ()
        organ.configure_from_harvest(
            organ_name="heart", condition="pristine",
            corpse=self._fake_corpse(),
        )
        self.assertEqual(organ.key, "human heart")

    def test_key_omits_species_at_moderate_decay(self):
        # Issue #212: moderate/advanced decay drops the species token
        # ("rotting heart").  Stub a corpse with ``get_decay_stage``.
        organ = self._fake_organ()
        corpse = self._fake_corpse()
        corpse.get_decay_stage = lambda: "moderate"
        organ.configure_from_harvest(
            organ_name="heart", condition="damaged", corpse=corpse,
        )
        self.assertEqual(organ.key, "rotting heart")

    def test_key_uses_desiccated_at_skeletal_decay(self):
        # Issue #212: organs use ``desiccated`` (not ``skeletal``) at
        # the skeletal decay tier — soft tissue dries out.
        organ = self._fake_organ()
        corpse = self._fake_corpse()
        corpse.get_decay_stage = lambda: "skeletal"
        organ.configure_from_harvest(
            organ_name="heart", condition="refuse", corpse=corpse,
        )
        self.assertEqual(organ.key, "desiccated heart")

    def test_key_falls_back_for_unknown_species(self):
        # Issue #215: unknown species drop the species token entirely
        # at fresh decay — accidentally-alien organs render as bare
        # ``liver`` rather than misclaiming as human.
        organ = self._fake_organ()
        corpse = self._fake_corpse(species="unobtanium_alien")
        organ.configure_from_harvest(
            organ_name="liver", condition="pristine", corpse=corpse,
        )
        self.assertEqual(organ.key, "liver")


class TestOrganHasNoReturnAppearanceOverride(TestCase):
    """PR #204: the PR-G return_appearance override is gone.

    Asserts the override no longer exists on ``Organ`` so the engine's
    default renderer handles look output (consuming ``db.desc``
    naturally).  Guards against accidental re-introduction.
    """

    def test_organ_does_not_define_return_appearance(self):
        from typeclasses.items import Organ

        # ``return_appearance`` should be inherited, not defined on
        # Organ itself.  ``__dict__`` check skips inherited members.
        self.assertNotIn(
            "return_appearance", Organ.__dict__,
            "Organ must not override return_appearance; populate db.desc "
            "in configure_from_harvest instead.",
        )
