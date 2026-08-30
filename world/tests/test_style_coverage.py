"""Rolling a sleeve moves COVERAGE, not just prose (#2398).

`worn_items` — the location→items map everything reads to decide what is
visible and what is covered — was built from `get_current_coverage()` at the
MOMENT OF WEARING, and nothing rebuilt it. `set_style_property` wrote the new
state and returned.

So rolling a sleeve changed the description while the forearm stayed covered.
The `coverage_mod` half of the style system was inert for every garment in the
game the instant it was on a body: the layer underneath could never surface,
which is the whole reason unroll/rollup and zip/unzip exist.

The refresh lives in `set_style_property` rather than in the two style
commands, so commands, souls and the LLM `style` tool all get it from one
place instead of three that drift.
"""
from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import BaseEvenniaTest

from world import prototypes as P


class TestStyleMovesCoverage(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.wearer = create_object("typeclasses.characters.Character",
                                    key="wearer", location=self.room1)
        self.shirt = spawn(P.THERMAL_SHIRT)[0]
        self.overalls = spawn(P.WORK_COVERALLS)[0]
        for item in (self.shirt, self.overalls):
            item.move_to(self.wearer, quiet=True)
            self.wearer.wear_item(item)

    def _at(self, location):
        return [i.key for i in (self.wearer.worn_items or {}).get(location, [])]

    def test_rolling_uncovers_the_arms(self):
        """Fails toward the bug: coveralls still registered on the forearm
        after the sleeves went up."""
        self.assertIn("grey work coveralls", self._at("left_arm"))
        self.overalls.set_style_property("adjustable", "rolled")
        self.assertNotIn("grey work coveralls", self._at("left_arm"))

    def test_the_layer_beneath_surfaces(self):
        """The point of the whole style system — what is under the garment
        becomes the visible thing."""
        self.overalls.set_style_property("adjustable", "rolled")
        self.assertEqual(self._at("left_arm"), ["thermal shirt"])

    def test_unrolling_covers_them_again(self):
        self.overalls.set_style_property("adjustable", "rolled")
        self.overalls.set_style_property("adjustable", "normal")
        self.assertIn("grey work coveralls", self._at("left_arm"))

    def test_layer_order_survives_the_refresh(self):
        """`_build_clothing_coverage_map` takes items[0] as the one that
        shows, so re-seating must keep the outer garment first."""
        self.overalls.set_style_property("adjustable", "rolled")
        self.overalls.set_style_property("adjustable", "normal")
        self.assertEqual(self._at("left_arm"),
                         ["grey work coveralls", "thermal shirt"])

    def test_untouched_locations_are_left_alone(self):
        """Rolling sleeves must not disturb the legs."""
        before = self._at("left_thigh")
        self.overalls.set_style_property("adjustable", "rolled")
        self.assertEqual(self._at("left_thigh"), before)

    def test_a_closure_change_moves_coverage_too(self):
        self.assertIn("grey work coveralls", self._at("chest"))
        self.overalls.set_style_property("closure", "unzipped")
        self.assertNotIn("grey work coveralls", self._at("chest"))

    def test_an_unworn_item_restyles_without_touching_anybody(self):
        loose = spawn(P.WORK_COVERALLS)[0]
        loose.move_to(self.wearer, quiet=True)      # carried, not worn
        before = dict(self.wearer.worn_items or {})
        loose.set_style_property("adjustable", "rolled")
        self.assertEqual(dict(self.wearer.worn_items or {}), before)

    def test_restyling_never_raises_on_a_loose_garment(self):
        loose = spawn(P.WORK_COVERALLS)[0]
        loose.location = None
        self.assertTrue(loose.set_style_property("adjustable", "rolled"))
