"""Unit tests for the mob_flavor data layer and apply_random_flavor.

Verifies:

* The three data axes (short_descs, look_places, longdescs) are populated.
* ``apply_random_flavor`` selects from each axis and writes the chosen
  values onto the mob's storage surface.
* Paired locations receive the *same* template on both sides (so the
  symmetric-collapse render path engages).
* Locations without seed data are left untouched.
* The pair-key data structure carries the expected slots.
"""

from __future__ import annotations

from unittest import TestCase

from world.combat.constants import (
    DEFAULT_LONGDESC_LOCATIONS,
    PAIR_MERGE_KEYS,
)
from world.mob_flavor import (
    LONGDESCS,
    LOOK_PLACES,
    SHORT_DESCS,
    apply_random_flavor,
    random_longdesc,
    random_look_place,
    random_short_desc,
)


class FakeMob:
    """Minimal mob stub mirroring the storage surface used by
    ``apply_random_flavor``."""

    def __init__(self, locations=None):
        self._longdesc = dict(locations or DEFAULT_LONGDESC_LOCATIONS)
        self.db = type("DB", (), {})()
        self.db.desc = ""
        self.look_place = ""

    def get_available_locations(self):
        return list(self._longdesc.keys())

    def set_longdesc(self, location, value):
        if location not in self._longdesc:
            return False
        self._longdesc[location] = value
        return True

    def get_longdesc(self, location):
        return self._longdesc.get(location)


# =====================================================================
# Data presence
# =====================================================================


class DataLayerTests(TestCase):

    def test_short_descs_populated(self):
        self.assertTrue(len(SHORT_DESCS) >= 20)

    def test_short_descs_render_grammatically_for_he_she(self):
        """Smoke-test that braced verbs in short_descs flex correctly for
        gendered sleeves. A specific entry the user surfaced as broken
        ("{They} hold {themselves}...") must now produce
        ``"He holds himself"`` / ``"She holds herself"``.

        The neutral case ("They hold themselves") requires the *caller*
        to pass ``number="plural"`` since the renderer can't infer the
        verb's subject from the pronoun bucket. The corpse-side fix for
        that lives in ``Corpse._build_decay_desc_paragraph``; see
        ``test_corpse_token_render.py``.
        """
        from world.anatomy import substitute_pronoun_tokens

        entry = next(
            e for e in SHORT_DESCS
            if e.startswith("{They} {hold} {themselves}")
        )

        male = substitute_pronoun_tokens(entry, gender="male")
        self.assertIn("He holds himself", male)

        female = substitute_pronoun_tokens(entry, gender="female")
        self.assertIn("She holds herself", female)

        # Caller-driven plural picks the right verb form for neutral.
        neutral = substitute_pronoun_tokens(
            entry, gender="neutral", number="plural"
        )
        self.assertIn("They hold themselves", neutral)

    def test_short_descs_brace_verbs_after_pronoun_subject(self):
        """Verbs that follow ``{They}`` / ``{they}`` as their subject must
        be braced so ``flex_verb`` conjugates them for the apparent number
        (issue #321). Without bracing, a male / female sleeve renders
        ``"He hold himself"`` instead of ``"He holds himself"``.
        """
        import re

        # A small set of verbs that, if seen unbraced directly after a
        # capitalised ``{They}`` subject, would silently leak through
        # pronoun substitution.
        bare_verb_re = re.compile(
            r"\{They\}\s+(hold|carry|move|stand|look|have|are|sit|"
            r"think|remember|come|go|walk|run|wait|watch|seem|appear)"
            r"(?=\b|\W)"
        )
        offenders = []
        for entry in SHORT_DESCS:
            if bare_verb_re.search(entry):
                offenders.append(entry)
        self.assertEqual(
            offenders, [],
            f"Unbraced verbs after {{They}} subject: {offenders}",
        )

    def test_look_places_populated(self):
        self.assertTrue(len(LOOK_PLACES) >= 20)

    def test_longdescs_cover_all_default_singletons(self):
        # Every default-anatomy singular location should have entries.
        paired_sides = {side for pair in PAIR_MERGE_KEYS.values() for side in pair}
        singletons = set(DEFAULT_LONGDESC_LOCATIONS) - paired_sides
        for loc in singletons:
            with self.subTest(location=loc):
                self.assertIn(loc, LONGDESCS, f"Missing entries for {loc}")
                self.assertTrue(
                    len(LONGDESCS[loc]) >= 20,
                    f"Too few entries for {loc}",
                )

    def test_longdescs_cover_all_pair_keys(self):
        for pair_key in PAIR_MERGE_KEYS:
            with self.subTest(pair_key=pair_key):
                self.assertIn(pair_key, LONGDESCS, f"Missing entries for {pair_key}")
                self.assertTrue(
                    len(LONGDESCS[pair_key]) >= 20,
                    f"Too few entries for {pair_key}",
                )


# =====================================================================
# Getters
# =====================================================================


class GetterTests(TestCase):

    def test_random_short_desc_returns_string(self):
        result = random_short_desc()
        self.assertIsInstance(result, str)
        self.assertIn(result, SHORT_DESCS)

    def test_random_look_place_returns_string(self):
        result = random_look_place()
        self.assertIsInstance(result, str)
        self.assertIn(result, LOOK_PLACES)

    def test_random_longdesc_returns_seeded_entry(self):
        result = random_longdesc("hair")
        self.assertIsInstance(result, str)
        self.assertIn(result, LONGDESCS["hair"])

    def test_random_longdesc_returns_none_for_unseeded(self):
        # An extended-anatomy slot we don't seed.
        self.assertIsNone(random_longdesc("nonexistent_slot_xyz"))


# =====================================================================
# apply_random_flavor
# =====================================================================


class ApplyRandomFlavorTests(TestCase):

    def test_sets_db_desc(self):
        mob = FakeMob()
        apply_random_flavor(mob)
        self.assertIn(mob.db.desc, SHORT_DESCS)

    def test_sets_look_place(self):
        mob = FakeMob()
        apply_random_flavor(mob)
        self.assertIn(mob.look_place, LOOK_PLACES)

    def test_fills_all_seeded_singletons(self):
        mob = FakeMob()
        apply_random_flavor(mob)
        paired_sides = {side for pair in PAIR_MERGE_KEYS.values() for side in pair}
        singletons = set(DEFAULT_LONGDESC_LOCATIONS) - paired_sides
        for loc in singletons:
            with self.subTest(location=loc):
                self.assertIn(mob.get_longdesc(loc), LONGDESCS[loc])

    def test_paired_locations_share_template(self):
        # The same random selection must be applied to both sides so the
        # symmetric-collapse renderer engages.
        mob = FakeMob()
        apply_random_flavor(mob)
        for pair_key, (left, right) in PAIR_MERGE_KEYS.items():
            with self.subTest(pair_key=pair_key):
                self.assertEqual(
                    mob.get_longdesc(left),
                    mob.get_longdesc(right),
                    f"Sides of {pair_key} diverged — symmetric collapse will break.",
                )

    def test_skips_unseeded_locations(self):
        # Mob with a custom location that has no flavor data: it must
        # remain at whatever the storage surface defaulted to (None
        # under DEFAULT_LONGDESC_LOCATIONS).
        mob = FakeMob(locations={**DEFAULT_LONGDESC_LOCATIONS, "tail": None})
        apply_random_flavor(mob)
        self.assertIsNone(mob.get_longdesc("tail"))

    def test_single_side_pair_still_filled(self):
        # If only one side of a pair exists (post-severance, extended
        # anatomy), the pair entry should still be applied to it.
        locations = {
            loc: None for loc in DEFAULT_LONGDESC_LOCATIONS
            if loc != "left_eye"
        }
        mob = FakeMob(locations=locations)
        apply_random_flavor(mob)
        self.assertIn(mob.get_longdesc("right_eye"), LONGDESCS["eyes"])
