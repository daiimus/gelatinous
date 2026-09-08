"""The mask holds, and hiding survives `look` (#2451).

Three doors onto identity, each reading the body under the mask.

**1. `Character.search` never had the presence gate.** The room roster
filters hidden characters, but the SEARCH path did not — so any
observer who guessed an sdesc fragment could type `look gaunt man`,
`give card to gaunt man` or `remember gaunt man as X` and get a hit,
confirming presence AND rendering the full appearance. The multimatch
disambiguation listing would enumerate them by display name too.

The gate is scoped to the identity pipeline. `bypass` is set for
`candidates=` / `location=` / `global_search=` / dbref queries — the
doors internal and administrative code uses — so this closes the
player-types-a-name path and leaves machinery that legitimately needs a
specific object alone. Hidden is concealment, never invulnerability.

**2 and 3 are one defect through two doors.** `world/search.py`'s
keyword fallback and `world/emote.py`'s char-ref candidates both built
handles out of the character's RAW `height` / `build` / `sdesc_keyword`,
which `appear` never touches. Viktor runs `appear woman`, presents as
"brawny woman in a black trenchcoat" with the word "droog" nowhere in
sight — and `look droog` still landed on him, and `.nod at gaunt droog`
was accepted and rendered. Anyone who met him undisguised could confirm
the disguised figure was the same person by trying his old keyword,
with no pierce roll spent.

Note the search clause is DEAD WEIGHT undisguised — the real keyword is
already a word of the sdesc, so the word-boundary test above it has
already matched. Its only live effect was the disguised case, i.e. the
one case it had to get right.

**This is the third time this leak has been found**, so the fix is a
shared `world.identity.apparent_axes` rather than a third inline copy:
#2806 fixed it for the LLM address handle by writing the override
precedence out by hand, and that hand-written copy is now refactored
onto the helper too.

**Finding 4 of the issue is NOT fixed here.** A name recovered by
piercing is displayed but cannot be typed, while `.wave at Bruce` works
because emote seeds candidates from `get_display_name`, which pierces.
Wiring piercing into the search path naively would fire an opposed roll
on every failed name lookup — farmable. It can be done cache-only
(`disguise_pierce_cache` is permanent and roll-free on a hit), but that
is a different shape from these three and is left for its own change.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

def apparent_axes(char):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree — a module-scope import of a helper that does not exist
    yet turns the whole file into a loader error, and a loader error is
    not evidence. The behavioural tests below drive `search` and the
    emote candidate builder, both of which exist either way."""
    from world import identity
    return identity.apparent_axes(char)


class _MaskCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        for char in (self.char1, self.char2):
            char.location = self.room1
        self.char2.height = "tall"
        self.char2.build = "lean"
        self.char2.sdesc_keyword = "droog"

    def disguise(self, char, height="short", build="stocky", keyword="woman"):
        char.db.height_override = height
        char.db.build_override = build
        char.db.keyword_override = keyword


class TestTheHelperReadsTheMask(_MaskCase):
    def test_undisguised_returns_the_real_axes(self):
        self.assertEqual(apparent_axes(self.char2), ("tall", "lean", "droog"))

    def test_disguised_returns_the_presented_axes(self):
        self.disguise(self.char2)
        self.assertEqual(apparent_axes(self.char2), ("short", "stocky", "woman"))

    def test_a_partial_disguise_mixes_correctly(self):
        self.char2.db.keyword_override = "woman"
        self.assertEqual(apparent_axes(self.char2), ("tall", "lean", "woman"))

    def test_a_missing_keyword_falls_back_to_the_gender_default(self):
        self.char2.sdesc_keyword = None
        self.assertTrue(apparent_axes(self.char2)[2])


class TestTheRealKeywordStopsResolving(_MaskCase):
    def test_the_disguised_keyword_finds_them(self):
        self.disguise(self.char2)
        self.assertIs(self.char1.search("woman"), self.char2)

    def test_the_real_keyword_does_not(self):
        self.disguise(self.char2)
        self.assertIsNone(self.char1.search("droog", quiet=True) or None)

    def test_undisguised_the_real_keyword_still_works(self):
        """The clause is dead weight undisguised — but it must not have
        broken the ordinary case."""
        self.assertIs(self.char1.search("droog"), self.char2)


class TestPosesCannotAddressTheBodyUnderTheMask(_MaskCase):
    def _candidates(self):
        """Characters only — production filters to occupants before
        calling, and `room.contents` also holds exits, which have no
        `get_sdesc`. Returns (name, char, requires_capital) triples."""
        from world.emote import build_char_candidates
        occupants = [o for o in self.room1.contents
                     if hasattr(o, "get_sdesc")]
        return [name.lower()
                for name, _char, _requires_capital
                in build_char_candidates(self.char1, occupants)]

    def test_the_real_keyword_is_not_a_handle(self):
        self.disguise(self.char2)
        self.assertNotIn("droog", self._candidates())

    def test_the_presented_keyword_is(self):
        self.disguise(self.char2)
        self.assertIn("woman", self._candidates())

    def test_undisguised_the_real_keyword_is_still_a_handle(self):
        self.assertIn("droog", self._candidates())


class TestHidingSurvivesLook(_MaskCase):
    def test_a_hidden_character_is_not_found_by_sdesc(self):
        self.char2.db.hidden = True
        self.assertIsNone(self.char1.search("droog", quiet=True) or None)

    def test_a_visible_one_still_is(self):
        self.assertIs(self.char1.search("droog"), self.char2)

    def test_an_alert_looker_can_still_find_them(self):
        """Concealment, not invulnerability — detection is the
        precondition."""
        from world.stealth import ALERT, set_awareness
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, ALERT)
        self.assertIs(self.char1.search("droog"), self.char2)

    def test_an_explicit_candidate_list_still_resolves_them(self):
        """`candidates=` sets bypass — internal and administrative code
        must not lose the ability to name a specific object."""
        self.char2.db.hidden = True
        found = self.char1.search(self.char2.key, candidates=[self.char2],
                                  quiet=True)
        self.assertIn(self.char2, found if isinstance(found, list) else [found])
