"""Tests for the species-keyed pair table (issue #350 / PR-A).

Pre-PR, ``PAIR_MERGE_KEYS`` was a flat global constant. PR-A moved the
canonical source of truth into the species registry so non-humans can
declare their own pair anatomy (cyclops → no eye pair; insectoid →
no pair, single compound eye; spider → ``("anterior_eyes",
"posterior_eyes")``; hydra → multi-pair).

Tests cover:

* The human species declares the historical pair table.
* ``get_species_pair_keys`` returns the right table per species, falls
  back to human on unknown, returns a fresh dict (no aliasing).
* The legacy global ``PAIR_MERGE_KEYS`` is now derived from the human
  table — same contents, single source of truth.
* The pure ``substitute_pronoun_tokens`` helper threads species
  through so a species with no eye pair (e.g., a hypothetical cyclops)
  doesn't apply the side-aware singular flex.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy.species import (
    SPECIES_DEFINITIONS,
    get_species_pair_keys,
)
from world.anatomy import substitute_pronoun_tokens
from world.combat.constants import PAIR_MERGE_KEYS


class HumanPairTableShape(TestCase):

    def test_human_declares_canonical_pair_set(self):
        pairs = get_species_pair_keys("human")
        self.assertEqual(
            set(pairs.keys()),
            {"eyes", "ears", "arms", "hands", "thighs", "shins", "feet"},
        )

    def test_each_pair_is_left_right_tuple(self):
        for pair_key, (left, right) in get_species_pair_keys("human").items():
            with self.subTest(pair_key=pair_key):
                self.assertTrue(left.startswith("left_"))
                self.assertTrue(right.startswith("right_"))
                # Right stem must mirror left stem (left_eye/right_eye,
                # left_foot/right_foot).
                self.assertEqual(
                    left.split("_", 1)[1],
                    right.split("_", 1)[1],
                )


class GetSpeciesPairKeysHelper(TestCase):

    def test_unknown_species_falls_back_to_human(self):
        # Unknown species — registry guarantee per spec: fall back to
        # human rather than raising.
        unknown = get_species_pair_keys("alien_xenoform_qrz")
        human = get_species_pair_keys("human")
        self.assertEqual(unknown, human)

    def test_none_species_falls_back_to_human(self):
        self.assertEqual(get_species_pair_keys(None),
                         get_species_pair_keys("human"))

    def test_returns_fresh_dict_no_aliasing(self):
        # Callers may mutate the returned dict (defensive callers, or
        # ones that want to temporarily augment the set) — that must
        # not corrupt the registry.
        pairs = get_species_pair_keys("human")
        pairs["test_pair"] = ("left_test", "right_test")
        pairs2 = get_species_pair_keys("human")
        self.assertNotIn("test_pair", pairs2)


class LegacyGlobalConstantDerivedFromHuman(TestCase):

    def test_pair_merge_keys_matches_human_table(self):
        # Single source of truth: the legacy global constant is now
        # derived from SPECIES_DEFINITIONS["human"]["pair_keys"].
        self.assertEqual(
            dict(PAIR_MERGE_KEYS),
            dict(SPECIES_DEFINITIONS["human"]["pair_keys"]),
        )


class SubstitutePronounTokensThreadsSpecies(TestCase):
    """The pure token helper accepts an optional species parameter so
    the body-noun flex pass consults the right pair table."""

    def test_human_singular_eye_with_side_prefixes(self):
        # Baseline: human, singular eye with side="left" → "left eye"
        # (side-aware singular flex from #341 still applies).
        out = substitute_pronoun_tokens(
            "{Their} {eyes} are bright.",
            gender="male", number="singular", side="left",
            species="human",
        )
        self.assertEqual(out, "His left eye are bright.")

    def test_default_species_is_human(self):
        # No species → falls back to human (existing callers don't
        # need to change).
        out = substitute_pronoun_tokens(
            "{Their} {eyes} are bright.",
            gender="male", number="singular", side="left",
        )
        self.assertEqual(out, "His left eye are bright.")

    def test_species_with_no_eye_pair_keeps_bare_noun(self):
        # Simulate a cyclops-style species by registering one ad-hoc.
        # The body-noun flex pass shouldn't apply side prefix because
        # "eye" isn't in this species's pair table.
        SPECIES_DEFINITIONS["_test_cyclops"] = {
            "display_name": "test cyclops",
            "pair_keys": {},  # no pairs
            "location_display": {},
            "decay_part_prefixes": {},
            "decay_organ_prefixes": {},
            "decay_corpse_names": {},
            "decay_corpse_descriptions": {},
        }
        try:
            out = substitute_pronoun_tokens(
                "{Their} {eye} is bright.",
                gender="male", number="singular", side="left",
                species="_test_cyclops",
            )
            # No side prefix — bare "eye" since the species has no
            # eye pair. Pronoun still resolves.
            # NB: "eye" is also in LONGDESC_FLEX_NOUNS so it still
            # gets noun-flexed (kept singular here), just without
            # the side prefix.
            self.assertIn("His", out)
            self.assertIn("eye", out)
            self.assertNotIn("left eye", out)
        finally:
            del SPECIES_DEFINITIONS["_test_cyclops"]
