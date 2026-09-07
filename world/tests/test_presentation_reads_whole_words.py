"""Brass knuckles are not lingerie (#2478).

`derive_presentation` anchored only the LEADING edge:

```python
if re.search(r"\\b" + re.escape(word), low):
```

so every keyword matched as a **prefix**. `FEMME_KEYWORDS` contains
`"bra"`, and so anything beginning "bra…" read as femme.

The comment above `NOT_MARKED` says this was already fixed:

    #: A dress shirt is not a dress; the third time this codebase has
    #: been bitten by substrings (a "brass-toed boot" once read as a bra).

It wasn't. `NOT_MARKED` is a phrase blacklist applied by `str.replace`
before matching — it catches `dress shirt` and `slipper`, and does not
contain `brass`. **The very example the comment names is live in the
world and still reads femme.** Measured across all 1,228 object names in
the running database, prefix matching claims:

```
brass knuckles      brass-toed boots      strut brace
```

plus every room in The Brackett Arms — 240-odd of them — because the
building's name begins "Bra". Rooms are not garments so nothing consumed
that, but it shows how wide the prefix was.

The correct pattern was already in this file ninety lines down, in
`derive_rung`, which anchors both ends. That is what this adopts, so
there is now one way to match a style keyword rather than two.

**Checked before changing it:** anchoring the trailing edge also stops a
keyword matching its own plural. Compared strict `\\b…\\b` against a
plural-tolerant `\\b…(?:s|es)?\\b` over every prototype key and every
live object name — **they agree on all 1,228**, so nothing in the world
is named for a pluralised keyword and the stricter form costs nothing.

**Scope of the consequence, stated plainly:** this feeds
`presentation_affinity`, which only weights what a soul reaches for.
Rule 2 of this module is *"It never gates. Anyone wears anything."* So
nothing was blocked; a femme-leaning soul was merely a little more
inclined to pick up brass knuckles. It is worth fixing because it is a
*derivation* that runs on any garment name, including ones authored
tomorrow.

Now redundant but left alone: `"slipper"` in `NOT_MARKED`, which existed
only because `"slip"` used to match its prefix.
"""
from evennia.utils.test_resources import EvenniaTest


def derive(name):
    from world.style import derive_presentation
    return derive_presentation(name)


class TestTheNamesThatWereWrong(EvenniaTest):
    def test_brass_knuckles_are_unmarked(self):
        self.assertEqual(derive("brass knuckles"), ())

    def test_brass_toed_boots_are_unmarked(self):
        """The example the file's own comment claims was fixed."""
        self.assertEqual(derive("brass-toed boots"), ())

    def test_a_strut_brace_is_unmarked(self):
        self.assertEqual(derive("strut brace"), ())

    def test_a_building_named_brackett_is_unmarked(self):
        self.assertEqual(derive("The Brackett Arms - Lobby"), ())


class TestTheKeywordsStillRead(EvenniaTest):
    def test_a_bra_is_still_femme(self):
        self.assertEqual(derive("a lace bra"), ("femme",))

    def test_a_skirt_is_still_femme(self):
        self.assertEqual(derive("a pleated skirt"), ("femme",))

    def test_a_gown_is_still_femme(self):
        self.assertEqual(derive("a beaded gown"), ("femme",))

    def test_a_necktie_is_still_masc(self):
        self.assertEqual(derive("a narrow necktie"), ("masc",))

    def test_a_waistcoat_is_still_masc(self):
        self.assertEqual(derive("a grey waistcoat"), ("masc",))

    def test_a_multi_word_keyword_still_reads(self):
        self.assertEqual(derive("a black bow tie"), ("masc",))

    def test_a_hyphen_is_a_boundary(self):
        """"heeled" in "high-heeled boots" — the hyphen must not hide
        it."""
        self.assertEqual(derive("high-heeled boots"), ("femme",))


class TestTheBlacklistStillApplies(EvenniaTest):
    """`NOT_MARKED` still has work to do: with both boundaries, "dress"
    matches "dress shirt" exactly, which is the compound it exists for."""

    def test_a_dress_shirt_is_not_a_dress(self):
        self.assertEqual(derive("a white dress shirt"), ())

    def test_a_dress_is_still_a_dress(self):
        self.assertEqual(derive("a black dress"), ("femme",))

    def test_a_slip_on_is_not_a_slip(self):
        self.assertEqual(derive("canvas slip-ons"), ())

    def test_a_slip_is_still_a_slip(self):
        self.assertEqual(derive("a silk slip"), ("femme",))


class TestUnmarkedIsMostClothing(EvenniaTest):
    def test_a_plain_shirt(self):
        self.assertEqual(derive("a work shirt"), ())

    def test_an_empty_name(self):
        self.assertEqual(derive(""), ())

    def test_no_name_at_all(self):
        self.assertEqual(derive(None), ())


class TestNothingInTheWorldRegresses(EvenniaTest):
    """The trailing boundary also stops a keyword matching its own
    plural. Nothing is named that way — pinned, so a future garment
    called "stockings…" is caught by a test rather than by a player."""

    def test_strict_and_plural_tolerant_agree_on_every_prototype(self):
        import re
        from world.style import FEMME_KEYWORDS, MASC_KEYWORDS, NOT_MARKED
        import world.prototypes as protos

        def match(name, tail):
            low = (name or "").lower()
            for phrase in NOT_MARKED:
                low = low.replace(phrase, " ")
            for reading, words in (("femme", FEMME_KEYWORDS),
                                   ("masc", MASC_KEYWORDS)):
                for word in words:
                    if re.search(r"\b" + re.escape(word) + tail, low):
                        return reading
            return None

        names = {str(v["key"]) for v in vars(protos).values()
                 if isinstance(v, dict) and v.get("key")}
        self.assertTrue(names, "no prototype keys found to check")
        disagreed = [n for n in names
                     if match(n, r"\b") != match(n, r"(?:s|es)?\b")]
        self.assertEqual(disagreed, [])
