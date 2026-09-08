"""A menu entry naming a `proto` is plated, whichever door serves it
(#2531).

`plate_or_mix` exists for one reason, stated in its own docstring:

    A recipe naming a ``proto`` is PLATED — the real prototype spawned
    onto the surface, so a kitchen serves the same items the shelf sold.
    Everything else is MIXED from ingredients.

`make_drink_from_recipe` has **no `proto` branch at all**. It reads
`name` / `desc` / `effects` / `sips` / `taste` / `order_keywords` — none
of which a plated entry supplies. So a plated dish served through the
wrong door came out as a hollow fake drink: `eat` refuses it, `drink`
accepts it.

#2342 converted the NPC serve path and left the **two hands-on doors a
tender actually uses** — the mixing menu's `[3] Make a known recipe`,
and `prepare <drink>`. `typeclasses/bar.py` even imported
`plate_or_mix` and then called the other one.

Both doors now go through the wrapper, so `make_drink_from_recipe` has
exactly one caller left: `plate_or_mix` itself.

`plate_or_mix` can return `None` when a prototype fails to spawn, which
`make_drink_from_recipe` never did — so both call sites gained the guard
the NPC path already had.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.bar import plate_or_mix


class _BarCase(EvenniaTest):
    def bar(self):
        return create_object("typeclasses.bar.BarCounter", key="a bar",
                             location=self.room1)

    def plated_recipe(self):
        """A menu entry that names a real prototype."""
        return {"name": "a bowl of snails", "proto": "GROUND_MYSTERY_MEAT",
                "craft": "ladles it out"}

    def mixed_recipe(self):
        return {"name": "rotgut", "desc": "a mug of rotgut",
                "sips": 3, "effects": {}, "taste": "harsh"}


class TestPlateOrMixItself(_BarCase):
    def test_a_proto_entry_spawns_the_prototype(self):
        bar = self.bar()
        made = plate_or_mix(self.plated_recipe(), bar)
        self.assertIsNotNone(made)
        self.assertIs(made.location, bar)

    def delivery(self, obj):
        """What verb the consumption layer will accept for this item."""
        return obj.tags.get(category="delivery_method")

    def test_a_plated_dish_is_food_not_a_drink(self):
        """The issue's exact symptom: `eat` refused, `drink` worked.

        Asserted on the `delivery_method` tag, which is what the
        consumption command reads. Three earlier attempts here were
        wrong and worth recording — `sips` is a RECIPE key and not an
        object attribute; `uses_left` is set on the food prototype too;
        `DRINK_TYPECLASS` is plain `typeclasses.items.Item`, shared by
        both. `drink_effects` is an autocreating AttributeProperty and
        exists on both as well. Only the tags actually separate them.
        """
        made = plate_or_mix(self.plated_recipe(), self.bar())
        self.assertEqual(self.delivery(made), "eat")
        self.assertIn("food", made.tags.get(category="item_type",
                                            return_list=True))

    def test_a_mixed_entry_still_mixes(self):
        made = plate_or_mix(self.mixed_recipe(), self.bar())
        self.assertIsNotNone(made)
        self.assertEqual(self.delivery(made), "drink")
        self.assertTrue(made.attributes.get("is_drink"))

    def test_an_unspawnable_proto_returns_none(self):
        bar = self.bar()
        self.assertIsNone(
            plate_or_mix({"name": "x", "proto": "NO_SUCH_PROTOTYPE"}, bar))


class TestBothHandsOnDoorsUseIt(EvenniaTest):
    """The point of the issue: one decision, three doors, and only one
    of them had been converted."""

    def source(self, *parts):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return root.joinpath(*parts).read_text(errors="ignore")

    def test_prepare_plates(self):
        body = self.source("typeclasses", "bar.py")
        self.assertIn("plate_or_mix(recipe, bar)", body)

    def test_the_mixing_menu_plates(self):
        body = self.source("commands", "bar_menu.py")
        self.assertIn("plate_or_mix(recipe, bar)", body)

    def test_the_raw_mixer_has_exactly_one_caller(self):
        """`make_drink_from_recipe` should now be reachable only through
        the wrapper — that is what makes the doors agree."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        callers = []
        for path in root.rglob("*.py"):
            if "test" in path.parts or "/tests/" in str(path):
                continue
            body = path.read_text(errors="ignore")
            for i, line in enumerate(body.split("\n"), 1):
                if ("make_drink_from_recipe(" in line
                        and "def " not in line
                        and not line.strip().startswith("#")):
                    callers.append(f"{path.name}:{i}")
        self.assertEqual(callers, ["bar.py:826"],
                         f"unexpected direct callers: {callers}")

    def test_both_doors_guard_the_none(self):
        """`plate_or_mix` can fail to spawn where the raw mixer never
        could."""
        for parts in (("typeclasses", "bar.py"), ("commands", "bar_menu.py")):
            body = self.source(*parts)
            idx = body.index("plate_or_mix(recipe, bar)")
            self.assertIn("if drink is None:", body[idx:idx + 200],
                          f"{parts[-1]} does not guard the None")
