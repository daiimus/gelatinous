"""A sleeve decanted from the website is a whole character (#2449).

Four things every other creation point does that the web first-character
path did not. The shape is this session's recurring one: two doors onto
the same act, and only one of them carries the act's obligations.

**1. It leaked the player's real name.** `get_sdesc` composes a
stranger-facing description from `height` and `build`, and its fallback
when either is missing is `return self.key`. The web form never asked
for them, `at_object_creation` does not seed them, and nothing
backfills — so a website-created character was displayed to every
stranger as "Jorge Jackson" rather than "a lanky man". Permanently, and
in room contents, `look`, combat lines and every `msg_room_identity`
broadcast. The form now asks, sourced from the same `world.identity`
tuples the telnet menu enumerates.

**2. It had no Roman numeral.** Every sleeve is keyed "First Last I"
(WEB_RESPAWN_CHARACTER_CREATION_SPEC, #50) and this was the only
creation site in the tree that skipped
`build_name_from_death_count` — so a web sleeve's first death renamed
the clone straight to "First Last II" with no "I" ever having existed.

**3. Its uniqueness check couldn't see the other door.** The form
compared the un-numeraled "First Last" against `db_key`, and nothing is
ever stored under that. So it never saw the telnet sleeve "Jorge
Jackson I" and let a second player take the same lineage name, while
`charcreate.validate_name` — fixed in #2550 to compare BASE names —
blocked the reverse. It now calls that validator instead of
reimplementing it.

**4. It never got `decant_announce_pending`,** so the one player the
one-shot decant scene was written for — a brand-new website
registration — got the routine re-login line instead.

**Measured live before fixing: 0 of 57 PC sleeves were affected.** All
57 carry height and build, so this was armed and had never fired; the
14 sleeves without a Roman numeral pre-date the numbering rather than
coming from the web. No backfill is needed and none was run. That is
worth stating plainly, because the issue's framing implies live damage
and there is none — what this closes is the trap, not a wound.
"""
from django.test import TestCase as DjangoTestCase
from evennia.utils.test_resources import EvenniaTest

from world.identity import BUILDS, HEIGHTS


class TestTheFormAsksForIdentity(DjangoTestCase):
    def _form(self):
        from web.website.forms import CharacterForm
        return CharacterForm()

    def test_height_is_a_field(self):
        self.assertIn("height", self._form().fields)

    def test_build_is_a_field(self):
        self.assertIn("build", self._form().fields)

    def test_they_are_in_the_saved_field_set(self):
        from web.website.forms import CharacterForm
        for name in ("height", "build"):
            self.assertIn(name, CharacterForm.Meta.fields)

    def test_the_vocabularies_are_the_canonical_ones(self):
        """Not a second hand-maintained list — the telnet menu walks
        these same tuples."""
        fields = self._form().fields
        self.assertEqual([c[0] for c in fields["height"].choices], list(HEIGHTS))
        self.assertEqual([c[0] for c in fields["build"].choices], list(BUILDS))

    def test_a_submission_without_them_is_rejected(self):
        from web.website.forms import CharacterForm
        form = CharacterForm(data={
            "first_name": "Jorge", "last_name": "Jackson", "sex": "male",
            "desc": "", "grit": 75, "resonance": 75, "intellect": 75,
            "motorics": 75,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("height", form.errors)


class TestNoStrangerReadsTheRealName(EvenniaTest):
    """The predicate that produced the leak, driven directly: `get_sdesc`
    returns the key when either axis is missing."""

    def test_missing_both_leaks_the_key(self):
        self.char1.height = None
        self.char1.build = None
        self.assertEqual(self.char1.get_sdesc(), self.char1.key)

    def test_missing_one_leaks_it_too(self):
        """Half-seeding would not have been enough — the guard is `if
        not height or not build`."""
        self.char1.height = "tall"
        self.char1.build = None
        self.assertEqual(self.char1.get_sdesc(), self.char1.key)

    def test_both_present_describes_instead_of_naming(self):
        self.char1.height = "tall"
        self.char1.build = "lean"
        self.assertNotEqual(self.char1.get_sdesc(), self.char1.key)

    def test_every_choice_the_form_offers_produces_a_description(self):
        """Whatever a web player picks has to clear the fallback."""
        for height in HEIGHTS:
            for build in BUILDS:
                self.char1.height = height
                self.char1.build = build
                self.assertNotEqual(self.char1.get_sdesc(), self.char1.key,
                                    f"{height}/{build} still leaks the key")


class TestTheNumeralAndTheValidator(EvenniaTest):
    def test_the_web_path_imports_the_numbering_helper(self):
        """It was the only creation site in the tree that did not."""
        import inspect
        from web.website.views import characters
        source = inspect.getsource(characters)
        self.assertIn("build_name_from_death_count", source)

    def test_the_helper_numbers_a_first_sleeve(self):
        from commands.charcreate import build_name_from_death_count
        self.assertEqual(
            build_name_from_death_count("Jorge Jackson", 1), "Jorge Jackson I")

    def test_the_form_defers_to_the_muds_validator(self):
        import inspect
        from web.website import forms
        source = inspect.getsource(forms.CharacterForm.clean)
        self.assertIn("validate_name", source)
        self.assertNotIn("db_key__iexact", source)

    def test_the_validator_sees_a_numbered_sleeve(self):
        """The hole this closes: the web copy compared against a string
        nothing is ever stored under."""
        from commands.charcreate import validate_name
        self.char1.key = "Jorge Jackson I"
        self.char1.save()
        is_valid, _error = validate_name("Jorge Jackson")
        self.assertFalse(is_valid)


class TestTheDecantSceneIsArmed(EvenniaTest):
    def test_the_web_path_sets_the_flag(self):
        import inspect
        from web.website.views import characters
        self.assertIn("decant_announce_pending",
                      inspect.getsource(characters))

    def test_the_flag_is_what_at_post_puppet_reads(self):
        """Pins the two halves to each other — a flag nothing reads
        would be just as broken as one nothing writes."""
        import inspect
        from typeclasses import characters as chartypes
        self.assertIn("decant_announce_pending",
                      inspect.getsource(chartypes.Character.at_post_puppet))
