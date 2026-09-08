"""`dress` and `undress` name the target as the room saw them
(#2520, #2532).

## #2520 — the snapshot idiom, skipped by the two third-party doors

Every first-person clothing verb in `CmdClothing.py` captures
per-observer display names BEFORE touching `worn_items`, then broadcasts
with `pre_resolved_refs`. `_snapshot_actor_names`' own docstring says
why:

    Without it, observers receive the broadcast describing the actor's
    *post-action* sdesc, which produces nonsense like "a lithe masked
    droog in a black balaclava puts on a black balaclava".

The two **third-party** doors did neither. Dressing someone in a
disguise-essential garment shifts *their* sdesc, so a broadcast composed
afterwards names the target by the identity the mask just gave them —
*"X dresses a masked stranger in a balaclava"* — instead of by who the
room was looking at a moment earlier.

`_dress_character` was given an `on_committed` hook for exactly this,
documented as being *"so the caller can interpose an action broadcast
before the mutation fires any identity-shift recognition messages"*.
**It was plumbed and never passed.**

`dress` now mirrors `CmdWear`'s two branches — essential garments route
the action through the unmask for one combined line, everything else
broadcasts from the hook. `undress` removes a *list* through
`remove_item`, so there is no single mutation to interpose on; the
snapshot plus `pre_resolved_refs` on the existing broadcast is the
faithful equivalent.

### What these tests do and do not prove

The clothing half is pinned by SOURCE INSPECTION, and that is a real
limit worth stating rather than dressing up. The observable defect is
*which name a third party hears in the broadcast*, and demonstrating it
needs the full identity fixture — a real sdesc, longdesc and disguise
wiring. A probe with the bare harness characters showed
`get_display_name` returning "Char2" before and after the mask (no
sdesc to shift) and the observer receiving nothing through a
hand-patched `msg`. I did not build that fixture, and I am not claiming
these tests exercise the rendering.

What they do establish: the two third-party doors now use the same
idiom as the four first-person ones, which are the reference
implementation for this exact problem, and the behavioural tests confirm
dress/undress still work through every target shape (character, corpse,
essential garment). The risk in the change is low because it is a copy
of an established pattern, not a new one.

## #2532 — the branding pour served a near-miss of its own recipe

The flow prompts the bartender to write a taste, stores it on the
recipe, then pours the celebratory first glass through `_pour`, which
has no `taste` parameter. So the first glass differed from every later
order of the same drink in three ways at once: the taste was dropped for
the composed default, the desc read *"a freshly-mixed drink"* instead of
*"a house pour"*, and the recipe's `order_keywords` were never applied
as aliases — so the first one could not be ordered by the names the menu
advertises.

Fixed by pouring the saved recipe rather than re-deriving from the
projection, so the first glass is the same object every later glass will
be by construction rather than by keeping two paths in step.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdClothing import CmdDress, CmdUndress


class _ClothingCase(EvenniaCommandTest):
    def consenting(self):
        """A conscious character who has not granted trust is REFUSED by
        the consent gate — correct behaviour, and it made my first
        fixtures assert that a refused dress had moved the garment.
        Patched here so these tests exercise the broadcast wiring rather
        than the gate; `test_you_can_undress_the_dead` covers the gate
        itself."""
        return mock.patch(
            "commands.CmdClothing._can_third_party_clothing",
            return_value=True)

    def garment(self, key="a black balaclava", essential=False,
                holder=None):
        item = create_object("typeclasses.items.Item", key=key,
                             location=holder or self.char1)
        item.db.is_wearable = True
        item.db.coverage = ["head"]
        item.db.worn_desc = key
        if essential:
            item.db.disguise_essential = True
            item.db.is_disguise_item = True
        return item


class TestDressSnapshotsBeforeMutating(_ClothingCase):
    def setUp(self):
        super().setUp()
        self.char2.location = self.room1
        self.char1.location = self.room1

    def test_the_source_snapshots_before_dispatch(self):
        """Ordered against the CALL, not the first mention — my first
        version compared against a reference inside a comment and
        measured prose."""
        import inspect
        body = inspect.getsource(CmdDress.func)
        self.assertIn("_snapshot_actor_names", body)
        self.assertLess(body.index("pre_resolved = _snapshot_actor_names"),
                        body.index("self._dress_character("))

    def test_it_passes_the_hook_it_was_given(self):
        import inspect
        body = inspect.getsource(CmdDress.func)
        self.assertIn("on_committed=", body)

    def test_an_essential_garment_routes_through_the_unmask(self):
        import inspect
        body = inspect.getsource(CmdDress.func)
        self.assertIn("action_pre_resolved_refs=pre_resolved", body)

    def test_dressing_still_works(self):
        item = self.garment("a wool cap")
        with self.consenting():
            self.call(CmdDress(), f"{self.char2.key} in cap",
                      caller=self.char1)
        self.assertEqual(item.location, self.char2)

    def test_dressing_an_essential_garment_still_works(self):
        item = self.garment(essential=True)
        with self.consenting():
            self.call(CmdDress(), f"{self.char2.key} in balaclava",
                      caller=self.char1)
        self.assertEqual(item.location, self.char2)

    def test_a_conscious_stranger_is_still_refused(self):
        """The gate this patches out is real and must stay."""
        item = self.garment("a wool cap")
        out = self.call(CmdDress(), f"{self.char2.key} in cap",
                        caller=self.char1)
        self.assertIn("would resist", out)
        self.assertEqual(item.location, self.char1)

    def test_a_corpse_still_gets_dressed(self):
        corpse = create_object("typeclasses.corpse.Corpse", key="a corpse",
                               location=self.room1)
        shroud = self.garment("a burial shroud")
        self.call(CmdDress(), "corpse in shroud", caller=self.char1)
        self.assertEqual(shroud.location, corpse)


class TestUndressSnapshotsToo(_ClothingCase):
    def setUp(self):
        super().setUp()
        self.char2.location = self.room1
        self.char1.location = self.room1

    def test_the_source_snapshots_before_removal(self):
        import inspect
        body = inspect.getsource(CmdUndress.func)
        self.assertIn("_snapshot_actor_names", body)
        self.assertLess(body.index("undress_pre_resolved = _snapshot"),
                        body.index("self._undress_character("))

    def test_the_broadcast_uses_the_snapshot(self):
        import inspect
        body = inspect.getsource(CmdUndress.func)
        self.assertIn("pre_resolved_refs=undress_pre_resolved", body)

    def test_undressing_still_works(self):
        item = self.garment("a wool cap", holder=self.char2)
        self.char2.wear_item(item)
        with self.consenting():
            self.call(CmdUndress(), self.char2.key, caller=self.char1)
        self.assertEqual(item.location, self.char1)

    def test_undressing_a_corpse_still_works(self):
        corpse = create_object("typeclasses.corpse.Corpse", key="a corpse",
                               location=self.room1)
        shirt = self.garment("a shirt", holder=corpse)
        self.call(CmdUndress(), "corpse", caller=self.char1)
        self.assertEqual(shirt.location, self.char1)


class TestTheBrandingPourServesItsRecipe(EvenniaCommandTest):
    def test_pour_accepts_the_recipe(self):
        import inspect

        from commands import bar_menu
        self.assertIn("recipe=None", inspect.signature(
            bar_menu._pour).__str__().replace(" ", ""))

    def test_the_branding_flow_passes_it(self):
        import inspect

        from commands import bar_menu
        body = inspect.getsource(bar_menu._process_save_taste)
        self.assertIn("recipe=recipe", body)
        self.assertIn("recipe = _save_recipe", body)

    def test_the_saved_recipe_carries_the_written_taste(self):
        from commands.bar_menu import _save_recipe
        bar = create_object("typeclasses.bar.BarCounter", key="a bar",
                            location=self.room1)
        proj = {"name": "house mix", "flavour": "sharp", "effects": {},
                "taste": "composed default", "cocktail": None,
                "method": "build"}
        recipe = _save_recipe(bar, "Ash & Iron", proj=proj,
                              taste="like a struck match")
        self.assertEqual(recipe["taste"], "like a struck match")

    def test_and_the_first_glass_is_built_from_it(self):
        """The whole point: pour the recipe, not the projection."""
        from world.bar import plate_or_mix
        bar = create_object("typeclasses.bar.BarCounter", key="a bar",
                            location=self.room1)
        recipe = {"name": "Ash & Iron", "desc": "a house pour — sharp",
                  "sips": 3, "effects": {}, "taste": "like a struck match",
                  "order_keywords": ("ash", "iron")}
        made = plate_or_mix(recipe, bar)
        self.assertEqual(made.attributes.get("drink_taste"),
                         "like a struck match")
        self.assertIn("a house pour", made.db.desc)
