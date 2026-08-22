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

    def test_the_tag_vocabulary_is_the_games_vocabulary(self):
        """Spawners roll `world.identity.BUILDS`. If the two lists ever
        drift, every tagged line silently becomes unreachable — the
        failure is invisible, because selection just falls back to the
        untagged pool and still returns prose."""
        from world.identity import BUILDS
        self.assertEqual(set(mob_flavor.BUILD_TAGS), set(BUILDS))
        for build in BUILDS:
            self.assertIn(build, mob_flavor.BUILD_NEIGHBOURS)

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

    #: Garments a longdesc must not claim the body is currently inside.
    #: A covered location renders the CLOTHING's description instead of
    #: the longdesc (appearance_mixin), so a line reading "bandaged under
    #: the trousers" appears exactly when there are no trousers.
    WORN_NOW = re.compile(
        r"\b(under|through|over|above|beneath|behind)\s+(the\s+|their\s+|"
        r"\{their\}\s+|loose\s+)?(trousers|pants|shirt|jacket|coat|"
        r"waistband|clothing|clothes|sleeve|collar|boot|sock|glove)\b",
        re.I)

    def test_no_line_claims_a_garment_that_is_not_there(self):
        offenders = [f"{slot}: {line}" for slot, line in self._lines()
                     if self.WORN_NOW.search(line)]
        self.assertEqual(
            offenders, [],
            "a longdesc renders only when the location is UNCOVERED:\n"
            + "\n".join(offenders))

    def test_lines_are_unique_within_a_slot(self):
        for slot, entries in longdescs.LONGDESCS.items():
            lines = [e[1] if isinstance(e, tuple) else e for e in entries]
            self.assertEqual(len(lines), len(set(lines)),
                             f"{slot} repeats a line verbatim")


class TestNothingIsAParaphrase(EvenniaCommandTest):
    """Verbatim uniqueness is not enough.

    Expanding a slot by rewording a line already in it looks like new
    content and reads like a stutter. Caught 18 of exactly that in the
    synth catalogue after a hand-written pass; the verbatim check
    passed every one of them.
    """

    #: Jaccard overlap on content words. 0.5 flags a reworded twin
    #: while leaving lines that merely share a subject alone.
    THRESHOLD = 0.5

    STOP = set(
        "a an the of in on at to and or but with without that this it its "
        "is are was were be been has have had no not never any all as for "
        "from by into over under their them they there here which who "
        "somebody someone something".split())

    def _content_words(self, line):
        stripped = re.sub(r"\{[^{}]*\}", " ", line.lower())
        return {w for w in re.findall(r"[a-z]+", stripped)
                if w not in self.STOP and len(w) > 2}

    def _tables(self):
        from world.mob_flavor import longdescs_rat, longdescs_robot
        from world.mob_flavor import longdescs_synth
        return {
            "human": longdescs.LONGDESCS,
            "synth": longdescs_synth.LONGDESCS_SYNTH,
            "robot": longdescs_robot.LONGDESCS_ROBOT,
            "rat": longdescs_rat.LONGDESCS_RAT,
        }

    def test_no_slot_contains_a_reworded_twin(self):
        import itertools

        offenders = []
        for species, table in self._tables().items():
            for slot, entries in table.items():
                if isinstance(entries, dict):
                    entries = [ln for v in entries.values() for ln in v]
                lines = [e[1] if isinstance(e, tuple) else e
                         for e in entries]
                words = [self._content_words(ln) for ln in lines]
                for (i, a), (j, b) in itertools.combinations(
                        enumerate(words), 2):
                    if not a or not b:
                        continue
                    overlap = len(a & b) / len(a | b)
                    if overlap >= self.THRESHOLD:
                        offenders.append(
                            f"{species}/{slot} ({overlap:.2f}):\n"
                            f"     {lines[i]}\n     {lines[j]}")
        self.assertEqual(
            offenders, [],
            "these read as rewordings of each other:\n"
            + "\n".join(offenders))
