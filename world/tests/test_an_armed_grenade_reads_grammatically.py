"""An armed grenade's broadcast carries the right article (#3429).

Four arming broadcasts hardcoded "An", so "An tactical grenade beeps and
its light begins flashing!" for half the catalogue. The house helper is
phoneme-aware and skips names that already carry an article.
"""
import inspect
from unittest import TestCase

from commands import CmdExplosives
from commands.CmdExplosives import arming_line


class AnArmedGrenadeReadsGrammaticallyTest(TestCase):

    def test_a_consonant_name_takes_a(self):
        self.assertTrue(arming_line("tactical grenade").startswith("|rA tactical grenade beeps"))
        self.assertTrue(arming_line("flashbang").startswith("|rA flashbang beeps"))
        self.assertTrue(arming_line("smoke grenade").startswith("|rA smoke grenade beeps"))

    def test_an_initialism_that_sounds_like_a_vowel_takes_an(self):
        self.assertTrue(arming_line("HDG M67 fragmentation grenade").startswith("|rAn HDG M67 fragmentation grenade beeps"))
        self.assertTrue(arming_line("SPDR M9 grenade").startswith("|rAn SPDR M9 grenade beeps"))

    def test_the_rest_of_the_line_is_unchanged_and_carries_no_countdown(self):
        # The bracketed countdown left the line for good (#3350, owner):
        # `fuse_tag` appends it per viewer, builders only.
        self.assertEqual(arming_line("flashbang"),
                         "|rA flashbang beeps and its light begins flashing!|n")

    def test_the_countdown_is_for_builders_only(self):
        from types import SimpleNamespace
        from commands.CmdExplosives import fuse_tag
        # Through the perm() lock function: a rank on the ACCOUNT counts,
        # and quelling drops it; check_permstring on the character sees
        # neither (Iver, a developer, saw no countdown until this).
        builder = SimpleNamespace(locks=SimpleNamespace(check_lockstring=lambda who, ls: "perm(Builder)" in ls))
        player = SimpleNamespace(locks=SimpleNamespace(check_lockstring=lambda who, ls: False))
        thing_without_locks = SimpleNamespace()
        self.assertEqual(fuse_tag(builder, 7), " |y[7 seconds]|n")
        self.assertEqual(fuse_tag(player, 7), "")
        self.assertEqual(fuse_tag(thing_without_locks, 7), "")

    def test_no_broadcast_hardcodes_the_article_any_more(self):
        self.assertNotIn('"|rAn {', inspect.getsource(CmdExplosives))
