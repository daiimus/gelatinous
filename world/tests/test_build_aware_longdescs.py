"""Bodies get described like the bodies they are (#2158).

Longdesc lines were drawn from one flat pool per slot, so a heavyset
resident could be handed thighs "thin enough that the bones of the
iliac crest are sharply visible" while their own sdesc called them
heavyset. Eighteen such contradictions were live across forty
civilians.

A catalogue entry may now be a ``(build_tag, line)`` pair. Tagged
lines are offered only to that build or a neighbouring one; untagged
lines stay universal, which is most of the catalogue — moles, grit,
posture and old scars are true of any body.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world import mob_flavor


class TestEligibility(EvenniaCommandTest):
    POOL = [
        "A universal line.",
        ("slight", "A line for thin bodies."),
        ("heavyset", "A line for heavy bodies."),
    ]

    def test_a_heavy_body_is_never_offered_the_thin_line(self):
        pool = mob_flavor._eligible(self.POOL, "heavyset")
        self.assertIn("A universal line.", pool)
        self.assertIn("A line for heavy bodies.", pool)
        self.assertNotIn("A line for thin bodies.", pool)

    def test_a_thin_body_is_never_offered_the_heavy_line(self):
        pool = mob_flavor._eligible(self.POOL, "slight")
        self.assertIn("A line for thin bodies.", pool)
        self.assertNotIn("A line for heavy bodies.", pool)

    def test_a_neighbouring_build_may_borrow(self):
        """'lean' has nothing of its own here, but sits beside 'slight'."""
        pool = mob_flavor._eligible(self.POOL, "lean")
        self.assertIn("A line for thin bodies.", pool)
        self.assertNotIn("A line for heavy bodies.", pool)

    def test_a_build_with_no_neighbour_gets_only_universals(self):
        pool = mob_flavor._eligible(self.POOL, "athletic")
        self.assertEqual(pool, ["A universal line."])

    def test_an_unknown_build_still_gets_a_line(self):
        self.assertTrue(mob_flavor._eligible(self.POOL, None))
        self.assertTrue(mob_flavor._eligible(self.POOL, "gelatinous"))

    def test_a_plain_list_is_untouched(self):
        plain = ["one", "two", "three"]
        self.assertEqual(mob_flavor._eligible(plain, "stocky"), plain)

    def test_an_all_tagged_slot_never_returns_empty(self):
        """A wrong line beats a blank body."""
        only_tagged = [("slight", "thin"), ("lean", "stringy")]
        self.assertTrue(mob_flavor._eligible(only_tagged, "heavyset"))


class TestFillingWhatIsBlank(EvenniaCommandTest):
    """Authored cast keep their prose; they just stop being faces with
    no body attached."""

    def test_an_authored_line_is_never_overwritten(self):
        self.char1.set_longdesc("face", "A face somebody wrote by hand.")
        mob_flavor.fill_missing_longdescs(self.char1)
        self.assertEqual(self.char1.get_longdesc("face"),
                         "A face somebody wrote by hand.")

    def test_blank_slots_get_filled(self):
        self.assertGreater(mob_flavor.fill_missing_longdescs(self.char1), 0)

    def test_the_short_desc_is_left_alone(self):
        """db.desc is the glance, and it is somebody's prose."""
        self.char1.db.desc = "A wiry woman with a courier's stoop."
        mob_flavor.fill_missing_longdescs(self.char1)
        self.assertEqual(self.char1.db.desc,
                         "A wiry woman with a courier's stoop.")

    def test_running_twice_fills_nothing_the_second_time(self):
        mob_flavor.fill_missing_longdescs(self.char1)
        self.assertEqual(mob_flavor.fill_missing_longdescs(self.char1), 0)
