"""`world/voice.py` says what it is (#2645).

Three stale contracts, filed as one issue because the fix is one pass.

1. `is_voice_modulated`'s docstring said *"No augment sets this yet; the
   flag is honoured now so the modulator is pure content later."* One
   did, and it had shipped. Fixed since, and more thoroughly than the
   issue asked — see the test below.

2. The module header described itself as *"the data + composition layer
   (slice 2a)"* and said recognition and the resolution chain were
   *"later slices (2b/2c)"*. Both shipped INSIDE this file, and inline
   comments a few lines down already referred to 2c in the present
   tense.

3. `get_assigned_voice_name` and `has_voice_signature` have zero callers
   outside this module and its tests, while
   `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC` lists the first as shipped
   character-facing API. Not acted on: an unused function is not a dead
   function until the governing spec has been read, and here the spec
   says the opposite.

A docstring is not decoration in this repo — the one in (1) invited
deletion of code that honours a shipped augment.
"""
import inspect

from evennia.utils.test_resources import EvenniaTest

from world import voice as voice_mod


class TestTheHeaderNamesEverySlice(EvenniaTest):

    def test_the_slices_that_shipped_are_named(self):
        header = (voice_mod.__doc__ or "")
        for slice_name in ("2a", "2b", "2c"):
            self.assertIn(slice_name, header)

    def test_it_no_longer_calls_them_later(self):
        header = (voice_mod.__doc__ or "").lower()
        self.assertNotIn("are later slices", header)

    def test_because_they_are_in_this_file(self):
        """The control for the claim above: the header is only wrong if
        the functions really are here."""
        for name in ("get_apparent_voice_uid", "remember_voice",
                     "attempt_voice_discern"):
            self.assertTrue(hasattr(voice_mod, name), name)


class TestTheModulatorIsRealAndSaysSo(EvenniaTest):

    def test_the_docstring_no_longer_denies_it(self):
        doc = inspect.getdoc(voice_mod.is_voice_modulated) or ""
        self.assertNotIn("No augment sets this yet", doc)

    def test_it_reads_the_organ_not_a_flag(self):
        """The fix that landed goes further than the issue asked: a
        `character.db` flag has to be cleared by everything that can
        take the module away, and a module destroyed in place clears
        nothing — which welded the disguise on permanently (#2484). A
        destroyed organ simply stops matching."""
        source = inspect.getsource(voice_mod.is_voice_modulated)
        self.assertIn("has_deployed_ability", source)
        self.assertNotIn("voice_modulator_active", source)

    def test_nothing_sets_the_old_flag_any_more(self):
        """If something started writing it again, the organ read and the
        flag would disagree silently."""
        import subprocess
        found = subprocess.run(
            ["grep", "-rl", "voice_modulator_active",
             "world", "commands", "typeclasses"],
            capture_output=True, text=True).stdout.split()
        live = [p for p in found if "/tests/" not in p]
        self.assertEqual(live, [])
