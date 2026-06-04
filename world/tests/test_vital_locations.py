"""Tests for ``_get_vital_locations`` (vital body-location derivation, #251).

``_get_vital_locations`` previously iterated ``ORGANS`` looking for keys that
do not exist in the schema (``critical`` / ``location``), so it always fell
through to a hardcoded fallback. It now derives the vital set from the
capacities that actually kill or incapacitate the character
(``LETHAL_CAPACITY_NAMES``) by mapping each capacity's organs to their
``container``.

Covers:

* the stock anatomy resolves to ``{head, chest, neck, abdomen}``;
* ``neck`` is present *by data* (cervical spine -> neck), not by the fallback;
* the result is genuinely data-driven (a new lethal-capacity organ's container
  shows up), and never returns the empty set.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from world.medical.constants import (
    BODY_CAPACITIES,
    LETHAL_CAPACITY_NAMES,
    ORGANS,
)
from world.medical.utils import _get_vital_locations


class TestVitalLocations(TestCase):
    def test_stock_anatomy_vital_set(self):
        self.assertEqual(
            _get_vital_locations(None),
            {"head", "chest", "neck", "abdomen"},
        )

    def test_neck_is_vital_by_data(self):
        # cervical_spine lives in the neck and belongs to neck_integrity, a
        # lethal capacity -> neck must be vital regardless of the fallback.
        self.assertIn("neck", _get_vital_locations(None))

    def test_lethal_capacity_organs_map_to_their_containers(self):
        # Every lethal capacity's organs should contribute their container.
        expected = set()
        for capacity_name in LETHAL_CAPACITY_NAMES:
            for organ_name in BODY_CAPACITIES.get(capacity_name, {}).get(
                "organs", []
            ):
                container = ORGANS.get(organ_name, {}).get("container")
                if container:
                    expected.add(container)
        self.assertEqual(_get_vital_locations(None), expected)

    def test_is_data_driven_not_hardcoded(self):
        # Patching a lethal capacity to reference an organ in a novel container
        # must surface that container in the result, proving the derivation is
        # dynamic rather than a constant literal.
        #
        # Issue #356 follow-up: ``_get_vital_locations`` now reads
        # organ specs and capacity wiring through the species registry
        # (``get_organ_spec`` / ``get_species_body_capacities``). The
        # patch surface is therefore the human species entry rather
        # than the legacy module globals.
        from world.anatomy.species import SPECIES_DEFINITIONS

        human = SPECIES_DEFINITIONS["human"]
        patched_organs = dict(human["organs"])
        patched_organs["test_vital_organ"] = {"container": "tail"}
        patched_caps = {
            name: dict(data) for name, data in human["body_capacities"].items()
        }
        patched_caps["blood_pumping"] = {"organs": ["test_vital_organ"]}
        patched_human = dict(human)
        patched_human["organs"] = patched_organs
        patched_human["body_capacities"] = patched_caps
        patched_registry = dict(SPECIES_DEFINITIONS)
        patched_registry["human"] = patched_human

        with patch.dict(
            "world.anatomy.species.SPECIES_DEFINITIONS",
            patched_registry,
            clear=True,
        ):
            result = _get_vital_locations(None)
        self.assertIn("tail", result)

    def test_never_empty(self):
        self.assertTrue(_get_vital_locations(None))
