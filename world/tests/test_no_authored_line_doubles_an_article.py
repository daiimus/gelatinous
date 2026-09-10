"""No authored line says "a the" (#2724).

Three dispatcher blueprints carried:

    'temp_place': 'sitting on a the dispatch chair.'

which renders in the room to every observer. Purely cosmetic and cheap,
but the kind of thing that survives indefinitely because nobody owns
proofreading a 3,000-line data file.

A guard over the whole file rather than three edits, because the three
were not a coincidence -- they are copies of one another, and the next
dispatcher blueprint will be a copy too.

The live half of #2724 is already gone: a sweep of every `temp_place`,
`post_work_place`, `look_place`, `override_place`, `desc` and `sdesc` in
the database found ZERO doubled articles. The shift system has since
rewritten those rows (`_take_the_post` writes a generated line over the
authored one), so only the source strings remained. No repair build.

Scoped to the article pairs that are always wrong in English -- "a the",
"the a", "an the" and so on. Deliberately not a general grammar checker:
this catches a specific copy-paste shape, and a test that tries to be
clever about prose will fail on dialogue the moment somebody writes a
character who talks like that.
"""
import pathlib
import re

from evennia.utils.test_resources import EvenniaTest

#: Two articles in a row is never right outside quoted speech.
DOUBLED = re.compile(r"\b(a|an|the)\s+(a|an|the)\b", re.I)

FILES = (
    "world/npcs/blueprints.py",
    "world/prototypes.py",
    "world/emote_templates.py",
)


class TestAuthoredProse(EvenniaTest):

    def _root(self):
        return pathlib.Path(__file__).resolve().parents[2]

    def test_the_scan_reads_real_files(self):
        """Control: a typo in FILES would make every assertion below
        pass while reading nothing."""
        root = self._root()
        for rel in FILES:
            self.assertTrue((root / rel).is_file(), rel)

    def test_the_pattern_catches_the_shape_it_is_for(self):
        """Control: and that the regex actually fires."""
        self.assertTrue(DOUBLED.search("sitting on a the dispatch chair."))
        self.assertFalse(DOUBLED.search("sitting on the dispatch chair."))

    def test_no_doubled_article_in_authored_data(self):
        root = self._root()
        offenders = []
        for rel in FILES:
            for num, line in enumerate(
                    (root / rel).read_text(errors="ignore").splitlines(), 1):
                if DOUBLED.search(line):
                    offenders.append(f"{rel}:{num}: {line.strip()[:70]}")
        self.assertEqual(offenders, [], "doubled article in authored prose")
