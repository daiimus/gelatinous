"""Tests for corpse longdesc token rendering (issue #319).

The corpse renderer has its own per-location longdesc pipeline
(``Corpse._get_preserved_longdesc_descriptions``) that is independent
from the living-character ``AppearanceMixin``. Pre-#319, three gaps
were visible:

1. ``_build_decay_desc_paragraph`` slotted the death-time short
   description (``physical_description``) into the species template
   without running pronoun substitution, so ``{They}``/``{themselves}``
   tokens leaked.
2. ``_process_corpse_description_variables`` only resolved pronouns;
   body-noun and verb tokens like ``{eyes}`` / ``{move}`` were left
   literal.
3. No symmetric-pair collapse pass — ``left_eye`` and ``right_eye``
   each rendered their own line, even when both sides carried the
   same template.

These tests exercise the corpse fixes using a lightweight stub that
mirrors the corpse storage surface, sidestepping the full Evennia
object dance.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from typeclasses.corpse import Corpse


class _CorpseStub:
    """Minimal stub re-using the unbound corpse methods we exercise."""

    # Bind the corpse methods we want to test as instance methods on this stub.
    _process_corpse_description_variables = (
        Corpse._process_corpse_description_variables
    )
    _get_preserved_longdesc_descriptions = (
        Corpse._get_preserved_longdesc_descriptions
    )
    _build_corpse_clothing_coverage_map = (
        Corpse._build_corpse_clothing_coverage_map
    )
    _apply_decay_to_description = Corpse._apply_decay_to_description
    get_preserved_wound_descriptions = Corpse.get_preserved_wound_descriptions
    get_decay_stage = Corpse.get_decay_stage
    get_time_since_death = Corpse.get_time_since_death

    def __init__(self, *, gender="male", name="Anthony",
                 longdesc_data=None, contents=None):
        import time
        self.db = SimpleNamespace(
            original_character_name=name,
            original_gender=gender,
            original_skintone=None,
            longdesc_data=longdesc_data or {},
            wounds_at_death=[],
            death_time=None,
            time_of_death=None,
            creation_time=time.time(),  # Drives decay stage.
            # Generous thresholds so test corpse always reads as "fresh".
            decay_stages={
                "fresh": 1e9, "early": 2e9, "moderate": 3e9, "advanced": 4e9,
            },
        )
        self.ndb = SimpleNamespace()
        self.contents = contents or []


class TokenSubstitutionTests(TestCase):
    """``_process_corpse_description_variables`` should now flex
    pair-nouns and verbs per the requested ``number``."""

    def test_pronoun_token_resolves(self):
        c = _CorpseStub(gender="male")
        out = c._process_corpse_description_variables(
            "{Their} hand twitches."
        )
        self.assertEqual(out, "His hand twitches.")

    def test_capitalised_themselves_resolves(self):
        # Regression: pre-#319 the capitalised form leaked.
        c = _CorpseStub(gender="female")
        out = c._process_corpse_description_variables(
            "{They} hold {themselves} still."
        )
        self.assertEqual(out, "She hold herself still.")

    def test_pair_noun_plural_flex(self):
        c = _CorpseStub(gender="male")
        out = c._process_corpse_description_variables(
            "{Their} {eyes} hold steady.", number="plural"
        )
        self.assertEqual(out, "His eyes hold steady.")

    def test_pair_noun_singular_flex(self):
        # Only braced words flex — bare prose stays as authored.  The
        # "hold" verb here is plain prose so it doesn't subject-agree
        # with the singularised "eye"; authors who need that should
        # brace the verb (see ``test_braced_verb_flexes_singular``).
        c = _CorpseStub(gender="male")
        out = c._process_corpse_description_variables(
            "{Their} {eyes} hold steady.", number="singular"
        )
        self.assertEqual(out, "His eye hold steady.")

    def test_braced_verb_flexes_singular(self):
        c = _CorpseStub(gender="male")
        out = c._process_corpse_description_variables(
            "{Their} {eyes} {hold} steady.", number="singular"
        )
        self.assertEqual(out, "His eye holds steady.")


class PairCollapseTests(TestCase):
    """``_get_preserved_longdesc_descriptions`` should collapse matched
    left/right pairs into a single plural line."""

    EYES_TEMPLATE = (
        "{Their} {eyes} hold steady on whatever they look at."
    )
    HAIR_TEXT = "It is cropped close."

    def test_matching_eyes_collapse_to_one_line(self):
        c = _CorpseStub(
            gender="male",
            longdesc_data={
                "left_eye": self.EYES_TEMPLATE,
                "right_eye": self.EYES_TEMPLATE,
            },
        )
        descriptions = c._get_preserved_longdesc_descriptions()
        # Exactly one entry, anchored at the left side, rendered plural.
        eye_entries = [(loc, txt) for loc, txt in descriptions
                       if loc in ("left_eye", "right_eye")]
        self.assertEqual(len(eye_entries), 1)
        location, text = eye_entries[0]
        self.assertEqual(location, "left_eye")
        self.assertEqual(text, "His eyes hold steady on whatever they look at.")

    def test_singular_location_renders_singular(self):
        c = _CorpseStub(
            gender="female",
            longdesc_data={"hair": self.HAIR_TEXT},
        )
        descriptions = c._get_preserved_longdesc_descriptions()
        hair_entries = [(loc, txt) for loc, txt in descriptions if loc == "hair"]
        self.assertEqual(len(hair_entries), 1)
        self.assertEqual(hair_entries[0][1], self.HAIR_TEXT)

    def test_diverged_sides_render_individually(self):
        c = _CorpseStub(
            gender="male",
            longdesc_data={
                "left_eye": "{Their} left {eye} is brown.",
                "right_eye": "{Their} right {eye} is green.",
            },
        )
        descriptions = c._get_preserved_longdesc_descriptions()
        eye_entries = [(loc, txt) for loc, txt in descriptions
                       if loc in ("left_eye", "right_eye")]
        # Sides diverge → no collapse, both render individually.
        self.assertEqual(len(eye_entries), 2)
        for _loc, txt in eye_entries:
            # Singular flex was applied; no leaked braces.
            self.assertNotIn("{eye}", txt)
            self.assertNotIn("{Their}", txt)

    def test_single_side_only_renders_once(self):
        # Severed-on-one-side anatomy: only left_eye carries a longdesc.
        # Right side has no entry → no collapse, left renders alone.
        c = _CorpseStub(
            gender="male",
            longdesc_data={"left_eye": self.EYES_TEMPLATE},
        )
        descriptions = c._get_preserved_longdesc_descriptions()
        eye_entries = [(loc, txt) for loc, txt in descriptions
                       if loc in ("left_eye", "right_eye")]
        self.assertEqual(len(eye_entries), 1)
        self.assertEqual(eye_entries[0][0], "left_eye")
        # The braced {eyes} flexes to singular "eye"; surrounding plain
        # prose (the bare verb "hold") stays as authored.
        self.assertIn("His eye hold steady", eye_entries[0][1])

    def test_no_leaked_braces_anywhere(self):
        # End-to-end: load all the pair-key templates and confirm output
        # has zero leaked braces.
        from world.combat.constants import PAIR_MERGE_KEYS

        longdesc_data = {}
        for pair_key, (left, right) in PAIR_MERGE_KEYS.items():
            # Use the singular form of the pair key in the template.
            singular = left.split("_", 1)[1]
            template = f"{{Their}} {{{singular}s}} are present."
            longdesc_data[left] = template
            longdesc_data[right] = template

        c = _CorpseStub(gender="male", longdesc_data=longdesc_data)
        descriptions = c._get_preserved_longdesc_descriptions()
        for _loc, text in descriptions:
            self.assertNotIn("{", text, f"Leaked brace in: {text}")
            self.assertNotIn("}", text, f"Leaked brace in: {text}")
