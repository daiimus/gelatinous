"""The report card's border holds, and the help names real tones
(#2522, #2523).

## #2522 — two descriptors were one character too wide

The descriptive stat rows were built with a hardcoded 12-wide field
inside a 48-wide box:

```python
grit_line = f"              Grit:       {grit_display:<12}          "
```

`14 + 12 + 12 + 10 = 48`, exactly the box width — and `:<12` **pads but
never truncates**. Two of the 104 entries in `STAT_DESCRIPTORS` are 13
characters: `"Uncomfortable"` (resonance 25-30) and `"Knowledgeable"`
(intellect 85-90). Those rows rendered 49 characters into a 48-wide box.

`_center_text` left-pads each line from its own stripped length, so it
**propagated** the overflow rather than masking it: the right border sat
a column out, and the offending row was misaligned relative to the four
around it.

Live when filed: **two characters sit in an affected band** — #4893
Wayne McClain I (resonance 29) and #2120 Martha Howard (resonance 27) —
both currently rendering `Uncomfortable`. Nobody is in intellect 85-90,
so that half was armed and unfired.

Every row now goes through `_fit_row`, which measures **visible** width
— the vitals row carries colour codes inline, and `str.ljust` counts
them. It pads short rows and clips long ones, copying colour codes
through and appending any that remain after a clip so a row can never
leave a colour unclosed.

The numeric branch used `.ljust(48)`, which was safe only because its
values are short — `ljust` does not clip either. Both branches now use
the one fitter, so there is a single answer to "how wide is a row".

## #2523 — the help listed three tones that do not exist

`help @skintone` advertised `medium`, `dark` and `deep`; all three are
rejected by `VALID_SKINTONES` with *"not a valid skintone"*. It omitted
`golden` and `rich`, which work.

The irony is local: `_show_available_tones`, immediately below, carries
a docstring about fixing a discoverability bug by sourcing its list from
the species registry. The dynamic listing was fixed; the hardcoded one
directly above it was not.
"""
from evennia.utils.test_resources import EvenniaTest

def _fit_row(content, width=48):
    """Imported lazily so this module still LOADS against the unfixed
    tree — otherwise every test errors on a missing import and the
    source-pinning class below proves nothing."""
    from commands.CmdCharacter import _fit_row as real
    return real(content, width)


def visible(text):
    from commands.CmdCharacter import _strip_color_codes
    return len(_strip_color_codes(text))


class TestEveryRowIsExactlyTheBoxWidth(EvenniaTest):
    def test_a_short_descriptor_is_padded(self):
        self.assertEqual(
            visible(_fit_row("              Grit:       Weak")), 48)

    def test_the_thirteen_character_descriptor_fits(self):
        self.assertEqual(
            visible(_fit_row("              Resonance:  Uncomfortable")), 48)

    def test_the_other_thirteen_character_descriptor_fits(self):
        self.assertEqual(
            visible(_fit_row("              Intellect:  Knowledgeable")), 48)

    def test_colour_codes_are_not_counted(self):
        self.assertEqual(
            visible(_fit_row("              Vitals:     |gHEALTHY|n")), 48)

    def test_an_absurdly_long_row_is_clipped(self):
        self.assertEqual(visible(_fit_row("x" * 200)), 48)

    def test_an_empty_row_is_padded(self):
        self.assertEqual(visible(_fit_row("")), 48)

    def test_a_clip_does_not_leave_a_colour_open(self):
        """Codes after the clip point are appended, not dropped."""
        row = _fit_row("|r" + "x" * 60 + "|n")
        self.assertTrue(row.endswith("|n"))
        self.assertEqual(visible(row), 48)


class TestEveryRealDescriptorFits(EvenniaTest):
    """The defect was a value nobody enumerated. Enumerate them."""

    def test_no_stat_descriptor_breaks_a_row(self):
        from world.combat.constants import STAT_DESCRIPTORS
        for stat, table in STAT_DESCRIPTORS.items():
            for value in table.values():
                row = _fit_row(f"              {stat.title()}:  {value}")
                self.assertEqual(visible(row), 48,
                                 f"{stat}={value!r} broke the row")

    def test_the_two_long_ones_are_still_in_the_table(self):
        """If they are ever shortened this test should be deleted, not
        quietly kept passing on a table that no longer has them."""
        from world.combat.constants import STAT_DESCRIPTORS
        all_values = {v for t in STAT_DESCRIPTORS.values() for v in t.values()}
        self.assertIn("Uncomfortable", all_values)
        self.assertIn("Knowledgeable", all_values)

    def test_no_medical_status_breaks_the_vitals_row(self):
        """Latent when filed: every status is <= 11 chars today."""
        from world.medical import utils as medutils
        import inspect
        src = inspect.getsource(medutils.get_medical_status_description)
        import re
        for literal in re.findall(r'"([A-Z][A-Z ]{2,})"', src):
            row = _fit_row(f"              Vitals:     {literal}")
            self.assertEqual(visible(row), 48, f"{literal!r} broke the row")


class TestTheSkintoneHelpNamesRealTones(EvenniaTest):
    def _help(self):
        from commands.CmdCharacter import CmdSkintone
        return CmdSkintone.__doc__ or ""

    def test_every_tone_named_in_the_help_is_valid(self):
        import re
        from world.combat.constants import VALID_SKINTONES
        body = self._help()
        section = body[body.index("Organic tones:"):body.index("Examples:")]
        named = set(re.findall(r"[a-z]{4,}", section))
        invented = {w for w in named if w in
                    {"medium", "dark", "deep"}}
        self.assertEqual(invented, set(), f"invented tones: {invented}")
        for tone in ("porcelain", "golden", "rich", "chrome"):
            self.assertIn(tone, section)
            self.assertIn(tone, VALID_SKINTONES)

    def test_the_help_no_longer_names_the_three_that_do_not_exist(self):
        from world.combat.constants import VALID_SKINTONES
        for gone in ("medium", "dark", "deep"):
            self.assertNotIn(gone, VALID_SKINTONES)
            self.assertNotIn(f" {gone},", self._help())

    def test_the_help_covers_both_families(self):
        body = self._help()
        self.assertIn("Organic tones:", body)
        self.assertIn("Synthetic tones:", body)

    def test_it_points_at_the_authoritative_listing(self):
        self.assertIn("@skintone list", self._help())



class TestTheOldShapeIsGone(EvenniaTest):
    """Pinned against the source. The defect was a hardcoded field width
    that reads as deliberate — `:<12` inside a box that is 48 wide —
    and the arithmetic only fails for two values out of 104."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdCharacter.py").read_text(
            errors="ignore")

    def test_no_stat_row_uses_a_fixed_twelve_field(self):
        import re
        rows = [ln for ln in self._source().splitlines()
                if re.search(r"_display:<12", ln)]
        self.assertEqual(rows, [])

    def test_every_stat_row_goes_through_the_fitter(self):
        body = self._source()
        for stat in ("grit", "resonance", "intellect", "motorics",
                     "vitals"):
            self.assertIn(f"{stat}_line = _fit_row(", body,
                          f"{stat} row bypasses the fitter")

    def test_the_numeric_branch_no_longer_uses_ljust(self):
        """`ljust` does not clip either — one door, not two."""
        self.assertNotIn("_content.ljust(48)", self._source())


class TestTheOldArithmeticActuallyBroke(EvenniaTest):
    """Reproduces the pre-fix row construction, so the failure is
    demonstrated rather than asserted."""

    def test_the_thirteen_character_descriptor_overflowed(self):
        old_row = f"              Resonance:  {'Uncomfortable':<12}          "
        self.assertEqual(len(old_row), 49)

    def test_a_normal_descriptor_did_not(self):
        old_row = f"              Resonance:  {'Weak':<12}          "
        self.assertEqual(len(old_row), 48)
