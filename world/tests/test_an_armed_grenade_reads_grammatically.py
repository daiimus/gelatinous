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
        self.assertTrue(arming_line("tactical grenade", 5).startswith("|rA tactical grenade beeps"))
        self.assertTrue(arming_line("flashbang", 3).startswith("|rA flashbang beeps"))
        self.assertTrue(arming_line("smoke grenade", 4).startswith("|rA smoke grenade beeps"))

    def test_an_initialism_that_sounds_like_a_vowel_takes_an(self):
        self.assertTrue(arming_line("HDG M67 fragmentation grenade", 4).startswith("|rAn HDG M67 fragmentation grenade beeps"))
        self.assertTrue(arming_line("SPDR M9 grenade", 4).startswith("|rAn SPDR M9 grenade beeps"))

    def test_the_fuse_and_the_rest_of_the_line_are_unchanged(self):
        self.assertEqual(arming_line("flashbang", 7),
                         "|rA flashbang beeps and its light begins flashing!|n |y[7 seconds]|n")

    def test_no_broadcast_hardcodes_the_article_any_more(self):
        self.assertNotIn('"|rAn {', inspect.getsource(CmdExplosives))
