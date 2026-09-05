"""A keeper's placement line has to reach the ROOM RENDER (#2465).

Two faults, one on top of the other, and the first hid the second.

`temp_place` is `AttributeProperty("", category='description')`
(`typeclasses/characters.py:179`). A categorised property and a bare
`.db.temp_place` are DIFFERENT ROWS. The souls layer wrote the bare one;
`Room.get_display_characters` reads the property. So the write landed
where nothing looks, and every venue keeper in the colony stood at their
post rendering the `look_place` default, "standing here." The souls
bookkeeping looked healthy the whole time because it wrote and cleared
its own phantom row consistently -- a missing placement line reads as
"this NPC hasn't got one", not as a fault.

Underneath that: the renderer supplies the verb (`f"{name} is
{placement}"`), so placements are authored as clauses -- "standing
here.", "unconscious and motionless.". All eight `post_work_place`
fixtures instead begin "is ...", because they were written against the
phantom row and nobody could see the doubling they produced. Fixing the
row alone would have shipped "Ottilie is is working the cart."

So these tests assert the RENDERED LINE, not the attribute. Asserting
`soul.temp_place == line` would pass on a build that renders the double
copula, which is the exact class of green-test-over-broken-surface this
codebase has been bitten by before.
"""
from evennia.utils.test_resources import EvenniaTest

from world.souls.jobs import _leave_the_post, _post_placement, _take_the_post


class _PostCase(EvenniaTest):
    """A keeper, a counter that declares how it is worked, and a looker."""

    LINE = "is working the cart, cleaver within reach"
    CLAUSE = "working the cart, cleaver within reach"

    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.looker = self.char2
        self.post = self.room1
        self.soul.location = self.post
        self.looker.location = self.post
        self.soul.db.soul_post = self.post
        self.counter = self.obj1
        self.counter.location = self.post
        self.counter.key = "a hull-plate food cart"
        self.counter.db.post_work_place = self.LINE

    def render(self):
        return self.post.get_display_characters(self.looker)


class TestThePlacementLineReachesTheRender(_PostCase):
    def test_taking_the_post_renders_the_placement(self):
        _take_the_post(self.soul)
        self.assertIn(self.CLAUSE, self.render())

    def test_it_renders_one_copula_not_two(self):
        """The fixture says "is working ..." and the renderer says
        "X is ...". Only one of them gets to."""
        _take_the_post(self.soul)
        rendered = self.render()
        self.assertNotIn("is is", rendered)
        self.assertIn(f"is {self.CLAUSE}", rendered)

    def test_before_the_shift_the_default_shows(self):
        self.assertIn("standing here.", self.render())

    def test_leaving_the_post_takes_the_line_back_off(self):
        _take_the_post(self.soul)
        _leave_the_post(self.soul)
        rendered = self.render()
        self.assertNotIn(self.CLAUSE, rendered)
        self.assertIn("standing here.", rendered)

    def test_two_keepers_at_one_counter_read_as_plural(self):
        """The renderer switches to "A and B are {placement}". An
        unstripped line makes that "are is working the cart"."""
        self.looker.db.soul_post = self.post
        _take_the_post(self.soul)
        _take_the_post(self.looker)
        rendered = self.room1.get_display_characters(self.char1)
        self.assertNotIn("are is", rendered)


class TestTheClauseNormalisation(_PostCase):
    def test_a_fixture_authored_as_a_clause_is_left_alone(self):
        """The eight in the world today all say "is ...", but the ninth
        may be written correctly. Both have to work."""
        self.counter.db.post_work_place = self.CLAUSE
        self.assertEqual(_post_placement(self.soul), f"{self.CLAUSE}.")

    def test_a_fixture_authored_as_a_sentence_is_reduced(self):
        self.assertEqual(_post_placement(self.soul), f"{self.CLAUSE}.")

    def test_a_plural_copula_is_stripped_too(self):
        self.counter.db.post_work_place = "are working the cart"
        self.assertEqual(_post_placement(self.soul), "working the cart.")

    def test_a_line_merely_beginning_with_is_inside_a_word_survives(self):
        """"island" must not lose its first two letters."""
        self.counter.db.post_work_place = "island-side, watching the water"
        self.assertEqual(_post_placement(self.soul),
                         "island-side, watching the water.")

    def test_no_post_no_placement(self):
        self.soul.db.soul_post = None
        self.assertIsNone(_post_placement(self.soul))


class TestThePhantomRowIsCleanedUp(_PostCase):
    def test_taking_the_post_removes_the_stale_uncategorised_row(self):
        """The souls layer left a value on the bare row for every keeper
        it ever placed. Nothing reads it, but it is the evidence that
        made this look fine, so the repair rides the shift tick rather
        than a migration script."""
        self.soul.attributes.add("temp_place", "is working the cart")
        _take_the_post(self.soul)
        self.assertFalse(
            self.soul.attributes.has("temp_place", category=None))

    def test_leaving_the_post_removes_it_too(self):
        """A soul whose shift ends without ever taking a post again --
        dead, reassigned -- still gets the row cleared."""
        self.soul.attributes.add("temp_place", "is working the cart")
        _leave_the_post(self.soul)
        self.assertFalse(
            self.soul.attributes.has("temp_place", category=None))

    def test_the_phantom_row_never_reaches_the_render(self):
        self.soul.attributes.add("temp_place", "haunting the phantom row")
        self.assertNotIn("haunting", self.render())


class TestPlayerAuthoredPlacementIsNotTrampled(_PostCase):
    def test_leaving_a_post_we_never_placed_leaves_the_line_alone(self):
        """`placed_by_shift` is the permission to clear. Without it the
        shift must not touch a placement a player set on themselves."""
        self.soul.temp_place = "leaning on the counter, waiting"
        self.soul.db.placed_by_shift = False
        _leave_the_post(self.soul)
        self.assertIn("leaning on the counter, waiting", self.render())


class TestThePlacementIsTerminated(_PostCase):
    """A clause without a full stop runs into whoever is described next
    -- the renderer concatenates placements into a paragraph (#2913).

    Caught in-game, not by the suite: the tests above assert the copula
    and never looked at what followed the clause."""

    def test_the_rendered_line_terminates(self):
        _take_the_post(self.soul)
        self.assertIn(f"{self.CLAUSE}.", self.render())

    def test_an_unterminated_fixture_gains_a_full_stop(self):
        self.assertTrue(_post_placement(self.soul).endswith("."))

    def test_an_already_terminated_one_is_not_doubled(self):
        self.counter.db.post_work_place = "working the cart."
        self.assertEqual(_post_placement(self.soul), "working the cart.")

    def test_other_terminators_are_respected(self):
        self.counter.db.post_work_place = "working the cart!"
        self.assertEqual(_post_placement(self.soul), "working the cart!")
