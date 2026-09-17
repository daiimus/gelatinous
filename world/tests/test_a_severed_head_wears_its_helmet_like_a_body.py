"""A severed head wears its helmet the way a body does (#3578).

Owner ruling, 2026-09-16: *a severed part must display garments "just
like it does on a character, mixing the worn descs and longdesc where
appropriate."*

Before this, a severed part described the body it came from in full —
skull, face, ears, neck — and then bolted a sentence on the end:
*"It still wears a mining helmet."* The helmet was a footnote to a bare
head, and Evennia's own contents listing printed *"You see: a mining
helmet"* underneath for good measure. On a living body and on a corpse
the same helmet has always *replaced* the head's prose, because that is
what a helmet does to a head: you see the helmet, not the skull, and not
the scar under it either.

So the part now renders from the same three rules the living
:meth:`~typeclasses.appearance_mixin.AppearanceMixin._get_visible_body_descriptions`
and :meth:`typeclasses.corpse.Corpse._get_preserved_longdesc_descriptions`
render from, walking the species display order:

* a covered location shows the garment's ``worn_desc`` in place of its
  longdesc — once per garment, however many locations it covers;
* what is under the garment stays under it: the longdesc *and* the
  wounds at that location are hidden, not merely reordered;
* an uncovered location renders longdesc + wounds exactly as before.

What is *worn* is the ledger's answer (``worn_items`` via
``worn_garments()``), never the mere fact of being inside the limb: a
glove stuffed into a severed hand is carried, not worn, and describes
nothing.

Run via::

    evennia test world.tests.test_a_severed_head_wears_its_helmet_like_a_body
"""

from __future__ import annotations

from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

# Authored the way live prototypes author it: brace tokens for the
# owner's pronouns, a ``{color}`` placeholder the item resolves itself.
# The helmet text is MINING_HELMET's shape (world/prototypes.py) —
# including its lack of a closing period, which is load-bearing for
# ``TestGarmentPunctuation`` at the foot of this module.
HELMET_WORN_DESC = (
    "A {color}yellow|n composite mining helmet sits square on {their} head, "
    "the chin strap left hanging rather than buckled"
)
GOGGLES_WORN_DESC = (
    "Scratched {color}amber|n goggles are strapped over {their} eyes, "
    "the lenses fogged from the inside"
)

LONGDESCS = {
    "hair": "{Their} hair is cropped close to the scalp.",
    "left_eye": "{Their} left eye is a flat, pale grey.",
    "right_eye": "{Their} right eye is a flat, pale grey.",
    "head": "{Their} skull is long and narrow.",
    "face": "{Their} face is all cheekbone and old stubble.",
    "left_ear": "{Their} left ear is notched at the top.",
    "right_ear": "{Their} right ear sits flat to the skull.",
    "neck": "{Their} neck is corded with hard-worn muscle.",
}

#: The part of each longdesc that survives token substitution against a
#: male owner — what we actually assert on.
RENDERED = {loc: text.replace("{Their}", "His")
            for loc, text in LONGDESCS.items()}

HEAD_DESC = "Cut clean through at the neck, the stump crusted dark."


class _SeveredHeadCase(EvenniaTest):
    """A real Appendage carrying a real head's worth of prose."""

    def setUp(self):
        super().setUp()
        self.head = create_object("typeclasses.items.Appendage",
                                  key="a severed head", location=self.room1)
        self.head.db.longdesc_data = dict(LONGDESCS)
        self.head.db.wounds_at_death = []
        self.head.db.original_gender = "male"
        self.head.db.original_character_name = "Iver"
        self.head.db.source_species = "human"
        self.head.db.desc = HEAD_DESC

    def garment(self, key, worn_desc, coverage, color, worn=True):
        """Create a garment INSIDE the head; enrol it in the ledger unless
        ``worn=False`` (carried, not worn).

        ``typeclasses.items.Item`` is the typeclass the clothing
        prototypes use — MINING_HELMET and the rest are plain Items with
        a ``category`` of ``"clothing"``, so that is what a severed part
        actually meets.
        """
        item = create_object("typeclasses.items.Item", key=key,
                             location=self.head)
        item.db.category = "clothing"
        item.db.is_wearable = True
        item.db.worn_desc = worn_desc
        item.db.coverage = list(coverage)
        item.db.color = color
        item.db.layer = 5
        if worn:
            ledger = dict(self.head.db.worn_items or {})
            # The ledger keys by the location the garment was worn at on
            # the source body — the shape `detach_items_to_appendage`
            # writes. Coverage is read off the ITEM, not off this key.
            # worn at every location it covers, newest outermost --
            # the shape detach_items_to_appendage / dress leave behind
            for loc in coverage:
                ledger.setdefault(loc, []).insert(0, item)
            self.head.db.worn_items = ledger
        return item

    def helmet(self, worn=True):
        return self.garment("a mining helmet", HELMET_WORN_DESC,
                            ["head"], "yellow", worn=worn)

    def goggles(self, worn=True):
        return self.garment("a pair of goggles", GOGGLES_WORN_DESC,
                            ["left_eye", "right_eye"], "amber", worn=worn)

    def unwear(self, item):
        """Take the garment off the ledger without moving it — the state
        `undress` leaves behind."""
        ledger = {loc: [i for i in items if i != item]
                  for loc, items in (self.head.db.worn_items or {}).items()}
        self.head.db.worn_items = {loc: items
                                   for loc, items in ledger.items() if items}

    def look(self):
        return self.head.return_appearance(self.char1)


class TestTheHelmetStandsInForTheHead(_SeveredHeadCase):
    """(a) A covered location shows the garment, once, and nothing else."""

    def test_the_helmet_is_described_once(self):
        self.helmet()
        out = self.look()
        self.assertEqual(out.count("composite mining helmet sits square"), 1,
                         f"helmet described {out.count('composite mining helmet sits square')}x: {out!r}")

    def test_its_pronoun_is_the_owners(self):
        self.helmet()
        self.assertIn("sits square on his head", self.look())

    def test_its_color_placeholder_is_resolved(self):
        """``{color}`` is the item's own token — ``_process_color_codes``
        runs before the pronoun pass, which leaves ``{color}`` alone."""
        self.helmet()
        out = self.look()
        self.assertNotIn("{color}", out)
        self.assertIn("yellow", out)

    def test_the_skull_under_it_is_not_described(self):
        self.helmet()
        self.assertNotIn(RENDERED["head"], self.look())

    def test_everything_it_does_not_cover_still_reads(self):
        self.helmet()
        out = self.look()
        for loc in ("hair", "face", "left_ear", "right_ear", "neck",
                    "left_eye", "right_eye"):
            self.assertIn(RENDERED[loc], out, f"{loc} longdesc vanished")


class TestNothingIsBoltedOnTheEnd(_SeveredHeadCase):
    """(b) No contents listing, no "still wears" sentence."""

    def test_no_contents_listing(self):
        self.helmet()
        self.assertNotIn("You see", self.look())

    def test_no_still_wears_sentence(self):
        self.helmet()
        self.assertNotIn("still wears", self.look())

    def test_the_bare_item_name_is_not_listed_either(self):
        """The helmet appears as PROSE, not as the object's key."""
        self.helmet()
        out = self.look()
        self.assertNotIn("You see: a mining helmet", out)


class TestTheProseStartsItsOwnParagraph(_SeveredHeadCase):
    """(c) Name + desc, blank line, then the body — the living body's
    ``f"{base_desc}\\n\\n{formatted}"`` shape, not a space-join."""

    def test_a_blank_line_separates_desc_from_body(self):
        self.assertIn(f"{HEAD_DESC}\n\n{RENDERED['hair']}", self.look())

    def test_it_holds_with_a_garment_on(self):
        self.helmet()
        self.assertIn(f"{HEAD_DESC}\n\n{RENDERED['hair']}", self.look())

    def test_the_name_is_still_its_own_line(self):
        out = self.look()
        self.assertIn("severed head", out.split("\n")[0])


class TestAPairIsCoveredByOneGarment(_SeveredHeadCase):
    """(d) One garment over two locations describes itself once."""

    def test_both_eyes_disappear_under_the_goggles(self):
        self.goggles()
        out = self.look()
        self.assertNotIn(RENDERED["left_eye"], out)
        self.assertNotIn(RENDERED["right_eye"], out)

    def test_the_goggles_are_described_once(self):
        self.goggles()
        out = self.look()
        self.assertEqual(out.count("goggles are strapped over"), 1,
                         f"goggles described twice: {out!r}")

    def test_a_helmet_and_goggles_coexist(self):
        self.helmet()
        self.goggles()
        out = self.look()
        self.assertEqual(out.count("composite mining helmet sits square"), 1)
        self.assertEqual(out.count("goggles are strapped over"), 1)
        self.assertNotIn(RENDERED["head"], out)
        self.assertNotIn(RENDERED["left_eye"], out)
        self.assertIn(RENDERED["face"], out)


class TestCarriedIsNotWorn(_SeveredHeadCase):
    """(e) Being inside the limb is not the same as being worn on it."""

    def test_a_carried_helmet_is_listed_not_described(self):
        helmet = self.helmet(worn=False)
        self.assertEqual(helmet.location, self.head)
        out = self.look()
        self.assertNotIn("composite mining helmet", out)
        # carried, not worn: it is contents, and contents are listed
        # (that line is how carried hardware is found, #3487)
        self.assertIn("You see", out)
        self.assertIn(helmet.get_display_name(self.char1), out)

    def test_and_the_head_under_it_still_reads(self):
        self.helmet(worn=False)
        self.assertIn(RENDERED["head"], self.look())

    def test_taking_it_off_the_ledger_gives_the_head_back(self):
        helmet = self.helmet()
        self.assertNotIn(RENDERED["head"], self.look())
        self.unwear(helmet)
        out = self.look()
        self.assertIn(RENDERED["head"], out)
        self.assertNotIn("composite mining helmet", out)


#: The wound renderer picks at random from an authored vocabulary, so
#: its output cannot be matched by substring. Every test below pins it
#: to one sentinel sentence instead — the question here is *whether* a
#: wound renders and how many times, never what it says.
WOUND_SENTINEL = "|RA sentinel wound sits here.|n"
WOUND_RENDERER = "world.medical.wounds.get_wound_description"


class TestWhatIsUnderTheGarmentStaysUnderIt(_SeveredHeadCase):
    """(f) A wound at a covered location is hidden with the prose it
    belongs to — and comes back the moment the garment does not."""

    def setUp(self):
        super().setUp()
        patcher = patch(WOUND_RENDERER, return_value=WOUND_SENTINEL)
        self.rendered_wound = patcher.start()
        self.addCleanup(patcher.stop)

    def wound(self, location):
        self.head.db.wounds_at_death = [
            {"injury_type": "cut", "location": location,
             "severity": "Severe", "stage": "old"},
        ]

    def test_the_wound_reads_when_the_head_is_bare(self):
        """CONTROL for the hiding test below: the instrument can see a
        wound at this location when nothing is covering it."""
        self.wound("head")
        self.assertIn(WOUND_SENTINEL, self.look())

    def test_the_helmet_hides_it(self):
        self.wound("head")
        self.helmet()
        self.assertNotIn(WOUND_SENTINEL, self.look())

    def test_it_is_not_re_emitted_at_the_end(self):
        """The trailing "unhandled wounds" sweep must not smuggle it back
        in as an orphan sentence — that is the shape of bug this rule
        invites, and it would be invisible to a plain assertNotIn on a
        renderer that also fires at the location."""
        self.wound("head")
        helmet = self.helmet()
        self.assertEqual(self.look().count(WOUND_SENTINEL), 0)
        self.unwear(helmet)
        self.assertEqual(self.look().count(WOUND_SENTINEL), 1)

    def test_a_wound_elsewhere_is_untouched(self):
        self.wound("face")
        self.helmet()
        out = self.look()
        self.assertEqual(out.count(WOUND_SENTINEL), 1)
        self.assertIn(RENDERED["face"], out)

    def test_a_wound_under_a_pair_covering_garment_is_hidden_too(self):
        self.wound("left_eye")
        self.goggles()
        self.assertNotIn(WOUND_SENTINEL, self.look())


class TestTheUndressedHeadIsUnchanged(_SeveredHeadCase):
    """(g) CONTROL: with nothing worn, the part renders exactly the prose
    it rendered before #3578 — every location, in display order — the
    only difference being the paragraph break that replaced the
    space-join."""

    def test_every_longdesc_is_present(self):
        out = self.look()
        for loc, text in RENDERED.items():
            self.assertIn(text, out, f"{loc} longdesc missing")

    def test_they_are_in_anatomical_display_order(self):
        out = self.look()
        positions = [out.index(RENDERED[loc]) for loc in
                     ("hair", "left_eye", "right_eye", "head", "face",
                      "left_ear", "right_ear", "neck")]
        self.assertEqual(positions, sorted(positions),
                         f"display order scrambled: {out!r}")

    def test_the_body_is_one_space_joined_run(self):
        out = self.look()
        body = out.split(f"{HEAD_DESC}\n\n", 1)[1]
        self.assertNotIn("\n", body, f"unexpected break inside the body: {body!r}")

    def test_nothing_claims_it_wears_anything(self):
        out = self.look()
        self.assertNotIn("still wears", out)
        self.assertNotIn("You see", out)


class TestGarmentPunctuation(_SeveredHeadCase):
    """The garment's sentence is terminated, like the body's.

    Both renderers this one is meant to match TERMINATE the garment's
    sentence: the living path goes through
    ``Item.get_current_worn_desc`` (``f"{self.worn_desc}."``) and the
    corpse path through ``Corpse._get_clothing_desc_for_corpse``
    ("Ensure the description ends with proper punctuation"). Live
    prototypes are authored WITHOUT the closing period on that
    assumption — MINING_HELMET and NECK_REBREATHER both end bare.

    The first #3578 cut read ``item.db.worn_desc`` raw, so the garment's
    sentence ran straight into the next location's ("...rather than
    buckled His face is all cheekbone..."). The part now reads through
    ``get_current_worn_desc`` like the body; this pins it.
    """

    def test_the_garment_sentence_is_terminated(self):
        self.helmet()
        out = self.look()
        self.assertIn("rather than buckled.", out,
                      "worn_desc ran into the next sentence unpunctuated")
