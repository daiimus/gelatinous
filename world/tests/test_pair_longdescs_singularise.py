"""Every pair-slot longdesc survives losing a limb (#2780, #2803, #2813).

`world/mob_flavor/longdescs.py` documents the convention in its own
header: one entry is applied to BOTH sides, so the renderer's
paired-collapse path engages, and a line must use the brace token --
`{hands}` / `{thighs}` / `{shins}` / `{feet}` -- **so the renderer can
singularize**.

Lines that write the pair noun bare cannot be singularised. The
renderer can turn `{shins}` into "right shin"; it can do nothing with
"the shins". So an amputee read *"Small faded marks band the shins"*
with one shin, and *"The skin of their thighs are smooth"* with two.

**The reason three separate issues exist is one test gap.** The
renderability sweep in `test_mob_flavor` imports `LONGDESCS` -- the
human table alone -- while `world.mob_flavor` registers four:
`_LONGDESCS_BY_SPECIES` maps human / rat / robot / synthetic_humanoid.
Human drift was caught; rat, robot and synth drift was not. #2813 named
this explicitly: *"the reason they got in is that the renderability test
sweeps only the human table -- which is also why #2780 and #2803
exist."*

So this sweep walks the REGISTRY, not one table. A fifth species added
tomorrow is covered the day its table lands.

Measured before the fix: **33 offending lines** -- 26 human, 7
synthetic_humanoid, 0 robot, 0 rat -- against the 14 the original issue
counted.
"""
import re

from evennia.utils.test_resources import EvenniaTest

from world.anatomy import get_species_pair_keys
from world.anatomy.longdesc_tokens import substitute_pronoun_tokens
from world.mob_flavor import _LONGDESCS_BY_SPECIES


def _text(entry):
    """Entries are either a bare string or a ``(build_tag, line)`` pair
    -- the human table carries 104 of the latter."""
    return entry[1] if isinstance(entry, tuple) else entry


def _pair_lines():
    """Every (species, slot, line) in a slot that can lose one side."""
    for species, table in _LONGDESCS_BY_SPECIES.items():
        pairs = get_species_pair_keys(species) or {}
        for slot, entries in (table or {}).items():
            if slot not in pairs:
                continue
            if isinstance(entries, dict):
                entries = [e for pool in entries.values() for e in pool]
            for entry in entries or ():
                yield species, slot, _text(entry)


class TestTheSweepCoversEverySpecies(EvenniaTest):
    """Guards the guard. If the registry grows and this sweep does not,
    the whole file goes quiet without failing."""

    def test_every_registered_species_is_walked(self):
        walked = {sp for sp, _slot, _line in _pair_lines()}
        self.assertEqual(walked, set(_LONGDESCS_BY_SPECIES))

    def test_more_than_the_human_table(self):
        self.assertGreater(len(_LONGDESCS_BY_SPECIES), 1)

    def test_there_are_lines_to_check(self):
        self.assertGreater(len(list(_pair_lines())), 200)


class TestNoPairLineNamesItsOwnSlotBare(EvenniaTest):
    """The mechanical failure: the slot's own plural noun written as
    literal text instead of the brace token."""

    def test_no_bare_slot_noun(self):
        offenders = []
        for species, slot, line in _pair_lines():
            braced = "{" + slot + "}"
            if braced in line:
                continue
            if re.search(rf"(?<!\{{)\b{re.escape(slot)}\b", line):
                offenders.append(f"[{species}/{slot}] {line[:70]}")
        self.assertEqual(offenders, [], "\n".join(offenders))


class TestEveryPairLineRendersInBothNumbers(EvenniaTest):
    """A line must survive the amputation, not merely contain a token."""

    def _render(self, line, species, number, side=None):
        return substitute_pronoun_tokens(
            line, gender="male", number=number, side=side, species=species)

    def test_no_token_survives_rendering(self):
        """An unresolved `{token}` reaches the player as literal braces."""
        offenders = []
        for species, slot, line in _pair_lines():
            for number, side in (("plural", None), ("singular", "right")):
                out = self._render(line, species, number, side)
                if "{" in out or "}" in out:
                    offenders.append(f"[{species}/{slot}] {number}: {out[:70]}")
        self.assertEqual(offenders[:12], [], "\n".join(offenders[:12]))

    def test_singular_render_never_shows_the_plural_noun(self):
        offenders = []
        for species, slot, line in _pair_lines():
            out = self._render(line, species, "singular", "right")
            if re.search(rf"\b{re.escape(slot)}\b", out):
                offenders.append(f"[{species}/{slot}] {out[:70]}")
        self.assertEqual(offenders[:12], [], "\n".join(offenders[:12]))

    def test_no_singular_render_has_a_plural_predicate(self):
        """#2803's failure, which the token rule alone does not catch:
        the predicate is a NOUN PHRASE, so flexing the verb is not
        enough. "{Their} {hands} {are} three-fingered manipulators"
        singularised to "his right hand IS three-fingered
        manipulatorS". The noun has to flex too -- braced as
        `{a manipulator}`, with any adjective outside the braces,
        since the resolver ignores a token containing a space."""
        offenders = []
        for species, slot, line in _pair_lines():
            out = self._render(line, species, "singular", "right")
            m = re.search(r"\b(?:is|was)\s+((?:\w+[- ]){0,3}\w+?s)\b(?=[.,;]|\s+(?:and|or)\b|$)",
                          out)
            # A preposition or comparative inside the span means the
            # -s word belongs to a prepositional phrase, not to the
            # predicate head: "is ragged at the tips", "is longer than
            # the forelegs". Both are correct English and neither is a
            # plural predicate. Without this the check reports them,
            # which is the same crude-proxy trap that left 5 of #2803's
            # 11 flagged lines needing a human eye.
            PREP = (" at ", " than ", " of ", " in ", " on ", " with ",
                    " from ", " for ", " to ", " by ", " against ",
                    " under ", " over ", " into ")
            if m and any(x in f" {m.group(1)} " for x in PREP):
                m = None
            if m and not m.group(1).endswith(("ss", "ous")):
                offenders.append(f"[{species}/{slot}] {out[:74]}")
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_plural_render_is_still_plural(self):
        """The fix must not invert the bug -- a two-limbed body still
        reads plural."""
        checked = 0
        for species, slot, line in _pair_lines():
            if "{" + slot + "}" not in line:
                continue
            out = self._render(line, species, "plural")
            self.assertIn(slot, out, f"[{species}/{slot}] {out[:70]}")
            checked += 1
        self.assertGreater(checked, 50, "sweep matched almost nothing")
