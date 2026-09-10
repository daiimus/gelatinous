"""Sex-specific prose reaches only the bodies it fits (#2731).

Two male NPCs had a C-section scar and a female NPC had chest hair.

The human catalogue's slots are flat LISTS and `_eligible` filters on
BUILD only, so every line was offered to every body. `sex` was threaded
through four callers into `entries.get(sex) or entries.get("any")` --
a branch that only runs for a sex-keyed dict, which no human slot is.

A RESTRICTION MAP rather than sex-keyed slots, and the reason is worth
recording because the keyed shape looks like the obvious fix:

  * `random_longdesc` resolves `get(sex) or get("any")` -- the sex pool
    REPLACES `any` rather than adding to it, and
    `test_random_longdesc_resolves_sex_pools` pins that for synth. So
    keying `chest` would leave every male body with exactly ONE chest
    line, unless ~20 neutral lines were duplicated into both pools.
  * I tried it. Sharing one neutral list across both keys avoids the
    duplication but makes every neutral line appear twice on a flatten,
    and four existing tests read these slots as lists -- one reported a
    line as a 1.00 paraphrase of ITSELF.

Two lines do not justify reshaping a data structure four tests depend
on. The keyed shape stays right for a catalogue that is sex-specific
throughout, which is what synth is.

Build 157 re-rolls the three bodies already written down, since a
catalogue fix only governs new draws.
"""
from evennia.utils.test_resources import EvenniaTest

from world.mob_flavor import LONGDESCS, random_longdesc


def _pool(slot, sex, species="human"):
    """Draw repeatedly; the pool is what shows up."""
    return {str(random_longdesc(slot, species=species, sex=sex))
            for _ in range(400)}


class TestTheKeyedSlots(EvenniaTest):

    def test_the_restricted_lines_are_still_in_the_catalogue(self):
        """Control: they are FILTERED, not deleted -- and the map keys
        must match the catalogue exactly or the filter silently matches
        nothing."""
        from world.mob_flavor import SEX_ONLY
        self.assertTrue(SEX_ONLY)
        flat = []
        for slot in ("chest", "abdomen"):
            for entry in LONGDESCS[slot]:
                flat.append(entry[1] if isinstance(entry, tuple) else entry)
        for text in SEX_ONLY:
            self.assertIn(text, flat,
                          "SEX_ONLY names a line the catalogue does not "
                          "contain — the filter matches nothing")

    def test_a_man_has_no_c_section_scar(self):
        self.assertFalse([l for l in _pool("abdomen", "male")
                          if "C-section" in l])

    def test_a_woman_has_no_chest_hair(self):
        self.assertFalse([l for l in _pool("chest", "female")
                          if "chest hair" in l])

    def test_a_woman_can_have_a_c_section_scar(self):
        """Control: the line is filtered, not deleted."""
        self.assertTrue([l for l in _pool("abdomen", "female")
                         if "C-section" in l])

    def test_a_man_can_have_chest_hair(self):
        self.assertTrue([l for l in _pool("chest", "male")
                         if "chest hair" in l])


class TestSexedPoolsAreStillFull(EvenniaTest):
    """The half that made the keying possible.

    A sex pool REPLACES `any`, so keying a slot naively would leave a
    male body with exactly one chest line -- the only male-specific one.
    The neutral prose is shared into both pools instead.
    """

    def test_a_man_still_gets_the_neutral_chest_prose(self):
        self.assertGreater(
            len(_pool("chest", "male")), 20,
            "a sexed body drew only its sex-specific line — the neutral "
            "pool is not being shared into it")

    def test_a_woman_still_gets_the_neutral_abdomen_prose(self):
        self.assertGreater(len(_pool("abdomen", "female")), 20)

    def test_an_unsexed_body_still_draws(self):
        """Never empty-handed, which the resolver's docstring promises."""
        self.assertTrue(_pool("chest", None))
