"""The catalogue keeps its own house rules (#2166).

Guards the two things that are cheap to break by hand-editing prose
and expensive to notice in play: a line that contradicts the body it
is attached to, and a line whose grammar only works for one pronoun.
"""
import re

from evennia.utils.test_resources import EvenniaCommandTest

from world import mob_flavor
from world.mob_flavor import longdescs


class TestBuildTagsAreHonoured(EvenniaCommandTest):
    LIMBS = ("arms", "hands", "thighs", "shins", "feet")

    def test_every_tag_is_a_real_build(self):
        for slot, entries in longdescs.LONGDESCS.items():
            for entry in entries:
                if isinstance(entry, tuple):
                    self.assertIn(entry[0], mob_flavor.BUILD_TAGS,
                                  f"{slot}: unknown build tag {entry[0]!r}")

    def test_a_heavy_body_never_draws_a_thin_line(self):
        """The contradiction this whole change exists to stop.

        Checked against the tagged set, not against the word "slight" —
        "a slight tremor at rest" is universal prose, not a build claim.
        """
        for slot in self.LIMBS:
            entries = longdescs.LONGDESCS[slot]
            thin = {e[1] for e in entries
                    if isinstance(e, tuple) and e[0] in ("slight", "lean")}
            self.assertTrue(thin, f"{slot} has no thin-tagged lines")
            pool = set(mob_flavor._eligible(entries, "heavyset"))
            self.assertEqual(pool & thin, set(),
                             f"{slot}: a heavyset body can draw thin prose")

    def test_every_build_gets_a_usable_pool(self):
        for slot in longdescs.LONGDESCS:
            for build in mob_flavor.BUILD_TAGS:
                pool = mob_flavor._eligible(
                    longdescs.LONGDESCS[slot], build)
                self.assertGreaterEqual(
                    len(pool), 5,
                    f"{slot}/{build} has only {len(pool)} lines to choose "
                    f"from — too thin to avoid repetition")

    def test_selection_respects_the_tag(self):
        """Drawn 200 times, a heavyset body never lands a slight line."""
        slight = {e[1] for e in longdescs.LONGDESCS["thighs"]
                  if isinstance(e, tuple) and e[0] == "slight"}
        self.assertTrue(slight)
        for _ in range(200):
            line = mob_flavor.random_longdesc(
                "thighs", "human", build="heavyset")
            self.assertNotIn(line, slight)


class TestTheProseStaysRenderable(EvenniaCommandTest):
    SAFE_AFTER_THEY = {
        "could", "would", "should", "might", "must", "can", "will",
        "fell", "slept", "had", "was", "were", "did", "went", "stopped",
        "left", "kept", "spent", "lost", "found", "made", "took", "saw",
    }

    def _lines(self):
        for slot, entries in longdescs.LONGDESCS.items():
            for entry in entries:
                yield slot, (entry[1] if isinstance(entry, tuple) else entry)

    def test_no_bare_person_subject_present_tense(self):
        bad = []
        pattern = re.compile(r"\{[Tt]hey\}\s+([A-Za-z']+)")
        for slot, line in self._lines():
            for word in pattern.findall(line):
                if word.lower() not in self.SAFE_AFTER_THEY:
                    bad.append(f"{slot}: {{they}} {word}")
        self.assertEqual(bad, [], "use {they <verb>}:\n" + "\n".join(bad))

    def test_braces_are_balanced(self):
        for slot, line in self._lines():
            self.assertEqual(line.count("{"), line.count("}"),
                             f"{slot}: unbalanced braces in {line!r}")

    def test_no_empty_lines(self):
        for slot, line in self._lines():
            self.assertTrue(line.strip(), f"{slot}: empty entry")

    def test_lines_are_unique_within_a_slot(self):
        for slot, entries in longdescs.LONGDESCS.items():
            lines = [e[1] if isinstance(e, tuple) else e for e in entries]
            self.assertEqual(len(lines), len(set(lines)),
                             f"{slot} repeats a line verbatim")
