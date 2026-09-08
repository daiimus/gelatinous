"""Four declared-but-unwired structures, cleared (#2473).

None of these was a live bug. Each was structure that reads as a
mechanism and is not one, which is worth clearing so it stops misleading
the next reader — and, in two cases, so it stops being a trap.

**1. `cached_appearance`** — `Corpse.at_object_receive` and
`at_object_leave` each invalidated a cache that is never assigned
anywhere in the repo. Harmless behind its `hasattr` guard, and actively
misleading: someone optimising corpse rendering would reasonably assume
a cache was in play.

**2. `weakness_exploited`** — read off each armour layer and subtracted
from that layer's reduction, and written nowhere. The subtraction was
always `max(0.0, x - 0.0)` and the `(-N%)` it fed into the combat debug
line could never render. `MODULAR_ARMOR_SYSTEM_SPEC` does not describe
armour weakness at all; the idea is now recorded there as unbuilt,
which is where an unbuilt idea belongs.

**3. Two dead locals in `at_traverse`** — already removed under #2466.

**4. `take_damage` ignoring a non-int** — this one is a trap, not just
noise. A float dealt ZERO damage and returned `(False, 0)`, which every
caller reads as *"survived, unharmed"*: no error, no log. Every current
caller coerces, but `blast_damage` is author-supplied PROTOTYPE data, so
the day somebody writes `2.5` the grenade silently stops working and
nothing anywhere says why. Coerced now — a number is a number.

**5. The ordinal naming constraint** — `get first aid kit` is rewritten
to a search for `aid kit-1`, so an item whose name begins with an
ordinal can never be found by its own name. No prototype does this
today and the natural-language win is worth keeping, but the constraint
is permanent and was invisible. Documented at `ORDINAL_WORDS`.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestDamageIsANumber(EvenniaTest):
    """A float used to deal ZERO and return `(False, 0)` — which reads,
    at every call site, as "survived, unharmed".

    `take_damage` returns `(died, actual_damage)`, so the damage figure
    is what these assert on. `died` is False for a survivable hit and
    was never the signal.
    """

    def hp(self):
        return sum(o.current_hp for o in
                   self.char1.medical_state.organs.values())

    def test_a_float_lands(self):
        before = self.hp()
        _died, dealt = self.char1.take_damage(4.0, location="chest")
        self.assertEqual(dealt, 4)
        self.assertLess(self.hp(), before)

    def test_a_fractional_float_lands(self):
        _died, dealt = self.char1.take_damage(2.5, location="chest")
        self.assertEqual(dealt, 2)

    def test_a_numeric_string_does_not(self):
        """Coercion is for NUMBERS, not for anything `int()` will take:
        a string here means a caller bug, and silently succeeding would
        hide it."""
        self.assertEqual(self.char1.take_damage("4", location="chest"),
                         (False, 0))

    def test_a_bool_does_not(self):
        """`bool` is an `int` subclass, so `True` would have dealt 1."""
        self.assertEqual(self.char1.take_damage(True, location="chest"),
                         (False, 0))

    def test_none_is_still_refused(self):
        self.assertEqual(self.char1.take_damage(None, location="chest"),
                         (False, 0))

    def test_zero_is_still_refused(self):
        self.assertEqual(self.char1.take_damage(0, location="chest"),
                         (False, 0))

    def test_a_float_below_one_is_refused(self):
        """0.4 truncates to 0, which is not damage."""
        self.assertEqual(self.char1.take_damage(0.4, location="chest"),
                         (False, 0))

    def test_negative_is_still_refused(self):
        self.assertEqual(self.char1.take_damage(-3, location="chest"),
                         (False, 0))

    def test_an_int_is_unchanged(self):
        before = self.hp()
        _died, dealt = self.char1.take_damage(4, location="chest")
        self.assertEqual(dealt, 4)
        self.assertLess(self.hp(), before)


class TestArmourStillReduces(EvenniaTest):
    """The weakness line was a no-op, so removing it must change
    nothing about what armour actually does."""

    def armoured(self):
        vest = create_object("typeclasses.items.Item", key="a vest",
                             location=self.char1)
        vest.db.is_wearable = True
        vest.db.coverage = ["chest"]
        vest.db.armor_rating = 5
        vest.db.armor_type = "ballistic"
        vest.db.worn_desc = "a vest"
        self.char1.wear_item(vest)
        return vest

    def test_armour_reduces_damage(self):
        self.armoured()
        reduced = self.char1._calculate_armor_damage_reduction(
            20, "chest", "bullet")
        self.assertLess(reduced, 20)

    def test_it_never_reduces_below_zero(self):
        self.armoured()
        self.assertGreaterEqual(
            self.char1._calculate_armor_damage_reduction(1, "chest",
                                                         "bullet"), 0)

    def test_an_unarmoured_location_is_untouched(self):
        self.armoured()
        self.assertEqual(
            self.char1._calculate_armor_damage_reduction(20, "left_leg",
                                                         "bullet"), 20)


class TestNothingStillReadsTheDeadNames(EvenniaTest):
    """Pinned: each of these is easy to reintroduce by copy-paste from
    an older revision."""

    def source(self, *parts):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return root.joinpath(*parts).read_text(errors="ignore")

    def test_the_corpse_cache_is_gone(self):
        self.assertNotIn("cached_appearance",
                         self.source("typeclasses", "corpse.py"))

    def test_the_armour_weakness_read_is_gone(self):
        body = self.source("typeclasses", "armor_mixin.py")
        self.assertNotIn("armor_layer.get('weakness_exploited'", body)
        self.assertNotIn("weakness_penalty", body)

    def test_the_idea_survives_in_the_spec(self):
        """Deleted from the code, kept where an unbuilt idea belongs."""
        spec = self.source("specs", "MODULAR_ARMOR_SYSTEM_SPEC.md")
        self.assertIn("Weakness Exploitation", spec)
        self.assertIn("UNBUILT", spec)

    def test_the_dead_traversal_locals_are_gone(self):
        body = self.source("typeclasses", "exits.py")
        self.assertNotIn('hands = getattr(traversing_object, "hands", {})',
                         body)

    def test_the_ordinal_constraint_is_written_down(self):
        body = self.source("typeclasses", "objects.py")
        start = body.index("ORDINAL_WORDS = {")
        self.assertIn("first aid kit", body[max(0, start - 900):start])
