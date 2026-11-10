"""Every clothing verb names its garment through the core matcher (#3783).

`wear`, `remove`, `rollup`, `zip` and `undress <target> <item>` each
used to compare the typed text to keys in a loop of their own: a key
substring for the worn-item verbs (so `irt` found a shirt, an alias
never matched, and `2nd shirt` was "not wearing"), an exact key over
the hands for `wear`, and a three-tier key/alias picker (`pick_worn`)
for `undress`. They now call `Character.search` with their own pool as
`candidates=`, the way `commands/CmdInventory.py` does.

For each verb these pin the three things the core matcher gives and
the loops did not, or did wrongly:

* an alias that is not a substring of the key resolves;
* an ordinal picks the second of two twins;
* a fragment from the middle of a word is refused, with the verb's
  own refusal text.

The picker cases that `world/tests/test_dressing_the_dead.py` pinned
on `pick_worn` are carried over onto the `undress` door at the end.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdClothing import CmdRemove, CmdRollUp, CmdUndress, CmdWear, CmdZip
from world.combat.constants import (
    STYLE_ADJUSTABLE,
    STYLE_CLOSURE,
    STYLE_STATE_NORMAL,
    STYLE_STATE_ROLLED,
    STYLE_STATE_UNZIPPED,
    STYLE_STATE_ZIPPED,
)

#: A branded key, and an alias that appears nowhere inside it.
BRANDED = "Vantage all-weather greatcoat"
ALIAS = "parka"
#: From inside "Vantage": starts no word of the key or the alias.
FRAGMENT = "antage"

ROLLABLE = {
    STYLE_ADJUSTABLE: {
        STYLE_STATE_NORMAL: {"coverage_mod": [], "desc_mod": ""},
        STYLE_STATE_ROLLED: {"coverage_mod": [], "desc_mod": " rolled"},
    },
}
ZIPPABLE = {
    STYLE_CLOSURE: {
        STYLE_STATE_ZIPPED: {"coverage_mod": [], "desc_mod": ""},
        STYLE_STATE_UNZIPPED: {"coverage_mod": [], "desc_mod": " open"},
    },
}


class _Wardrobe(EvenniaCommandTest):
    """Real garments, created on a real holder."""

    def garment(
        self,
        key: str,
        where: object | None = None,
        coverage: tuple = ("chest",),
        aliases: tuple = (),
        styles: dict | None = None,
        start: dict | None = None,
    ) -> object:
        item = create_object(
            "typeclasses.items.Item", key=key, location=where or self.char1)
        item.attributes.add("coverage", list(coverage))
        item.attributes.add("worn_desc", f"{key} worn")
        for alias in aliases:
            item.aliases.add(alias)
        if styles:
            item.attributes.add("style_configs", styles)
            item.attributes.add("style_properties", start or {})
        return item

    def worn(self, key: str, **kwargs) -> object:
        item = self.garment(key, **kwargs)
        ok, msg = self.char1.wear_item(item)
        self.assertTrue(ok, msg)
        return item


# ---------------------------------------------------------------- wear


class TestWearNamesTheGarment(_Wardrobe):

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        coat = self.garment(BRANDED, aliases=(ALIAS,))
        self.call(CmdWear(), ALIAS)
        self.assertTrue(self.char1.is_item_worn(coat))

    def test_an_ordinal_picks_the_second_twin(self):
        first = self.garment("leather glove", coverage=("left_hand",))
        second = self.garment("leather glove", coverage=("right_hand",))
        self.call(CmdWear(), "2nd leather glove")
        self.assertTrue(self.char1.is_item_worn(second))
        self.assertFalse(self.char1.is_item_worn(first))

    def test_a_mid_word_fragment_is_refused(self):
        coat = self.garment(BRANDED, aliases=(ALIAS,))
        out = self.call(CmdWear(), FRAGMENT)
        self.assertIn(f"You don't have '{FRAGMENT}'.", out)
        self.assertFalse(self.char1.is_item_worn(coat))

    def test_a_held_garment_is_still_found_by_name(self):
        """The deleted hands loop found nothing the core search did not:
        a held item stays in the holder's contents."""
        coat = self.garment(BRANDED, aliases=(ALIAS,))
        self.char1.wield_item(coat, "right")
        self.assertIn(coat, self.char1.hands.values(), "control: not held")
        self.call(CmdWear(), BRANDED)
        self.assertTrue(self.char1.is_item_worn(coat))


# -------------------------------------------------------------- remove


class TestRemoveNamesTheGarment(_Wardrobe):

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        coat = self.worn(BRANDED, aliases=(ALIAS,))
        self.call(CmdRemove(), ALIAS)
        self.assertFalse(self.char1.is_item_worn(coat))

    def test_an_ordinal_picks_the_second_twin(self):
        first = self.worn("leather glove", coverage=("left_hand",))
        second = self.worn("leather glove", coverage=("right_hand",))
        self.call(CmdRemove(), "2nd leather glove")
        self.assertFalse(self.char1.is_item_worn(second))
        self.assertTrue(self.char1.is_item_worn(first))

    def test_a_mid_word_fragment_is_refused(self):
        coat = self.worn(BRANDED, aliases=(ALIAS,))
        out = self.call(CmdRemove(), FRAGMENT)
        self.assertIn(f"You're not wearing '{FRAGMENT}'.", out)
        self.assertTrue(self.char1.is_item_worn(coat))

    def test_a_carried_garment_is_not_in_the_pool(self):
        """The pool is what is worn: a carried twin is not removed."""
        self.garment("leather glove", coverage=("left_hand",))
        out = self.call(CmdRemove(), "leather glove")
        self.assertIn("You're not wearing 'leather glove'.", out)

    def test_me_is_not_a_garment(self):
        """A scoped search does not hand back the caller (#3783)."""
        self.worn(BRANDED)
        out = self.call(CmdRemove(), "me")
        self.assertIn("You're not wearing 'me'.", out)


# -------------------------------------------------------------- rollup


class TestRollupNamesTheGarment(_Wardrobe):

    def rollable(self, key: str = BRANDED, **kwargs):
        return self.worn(
            key, styles=ROLLABLE,
            start={STYLE_ADJUSTABLE: STYLE_STATE_NORMAL}, **kwargs)

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        coat = self.rollable(aliases=(ALIAS,))
        self.call(CmdRollUp(), ALIAS, cmdstring="rollup")
        self.assertEqual(
            coat.get_style_property(STYLE_ADJUSTABLE), STYLE_STATE_ROLLED)

    def test_an_ordinal_picks_the_second_twin(self):
        first = self.rollable("flannel shirt", coverage=("left_arm",))
        second = self.rollable("flannel shirt", coverage=("right_arm",))
        self.call(CmdRollUp(), "2nd flannel shirt", cmdstring="rollup")
        self.assertEqual(
            second.get_style_property(STYLE_ADJUSTABLE), STYLE_STATE_ROLLED)
        self.assertEqual(
            first.get_style_property(STYLE_ADJUSTABLE), STYLE_STATE_NORMAL)

    def test_a_mid_word_fragment_is_refused(self):
        coat = self.rollable(aliases=(ALIAS,))
        out = self.call(CmdRollUp(), FRAGMENT, cmdstring="rollup")
        self.assertIn(f"You're not wearing '{FRAGMENT}'.", out)
        self.assertEqual(
            coat.get_style_property(STYLE_ADJUSTABLE), STYLE_STATE_NORMAL)

    def test_a_worn_garment_with_nothing_to_roll_keeps_its_refusal(self):
        """The pool is every worn item, so the garment is FOUND and gets
        the refusal that names what it lacks."""
        self.worn("plain vest")
        out = self.call(CmdRollUp(), "vest", cmdstring="rollup")
        self.assertIn("The plain vest doesn't have anything to roll up.", out)


# ----------------------------------------------------------------- zip


class TestZipNamesTheGarment(_Wardrobe):

    def zippable(self, key: str = BRANDED, **kwargs):
        return self.worn(
            key, styles=ZIPPABLE,
            start={STYLE_CLOSURE: STYLE_STATE_UNZIPPED}, **kwargs)

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        coat = self.zippable(aliases=(ALIAS,))
        self.call(CmdZip(), ALIAS, cmdstring="zip")
        self.assertEqual(
            coat.get_style_property(STYLE_CLOSURE), STYLE_STATE_ZIPPED)

    def test_zip_up_takes_the_alias_too(self):
        coat = self.zippable(aliases=(ALIAS,))
        self.call(CmdZip(), f"up {ALIAS}", cmdstring="zip")
        self.assertEqual(
            coat.get_style_property(STYLE_CLOSURE), STYLE_STATE_ZIPPED)

    def test_an_ordinal_picks_the_second_twin(self):
        first = self.zippable("track jacket", coverage=("left_arm",))
        second = self.zippable("track jacket", coverage=("right_arm",))
        self.call(CmdZip(), "up 2nd track jacket", cmdstring="zip")
        self.assertEqual(
            second.get_style_property(STYLE_CLOSURE), STYLE_STATE_ZIPPED)
        self.assertEqual(
            first.get_style_property(STYLE_CLOSURE), STYLE_STATE_UNZIPPED)

    def test_a_mid_word_fragment_is_refused(self):
        coat = self.zippable(aliases=(ALIAS,))
        out = self.call(CmdZip(), FRAGMENT, cmdstring="zip")
        self.assertIn(f"You're not wearing '{FRAGMENT}'.", out)
        self.assertEqual(
            coat.get_style_property(STYLE_CLOSURE), STYLE_STATE_UNZIPPED)

    def test_the_refusal_quotes_what_was_typed(self):
        self.zippable()
        out = self.call(CmdZip(), f"up {FRAGMENT}", cmdstring="zip")
        self.assertIn(f"You're not wearing 'up {FRAGMENT}'.", out)

    def test_a_worn_garment_with_no_zipper_keeps_its_refusal(self):
        self.worn("plain vest")
        out = self.call(CmdZip(), "vest", cmdstring="zip")
        self.assertIn("The plain vest doesn't have a zipper.", out)


# ------------------------------------------------------------- undress


class _UndressCase(_Wardrobe):

    def corpse(self):
        return create_object(
            "typeclasses.corpse.Corpse", key="a corpse", location=self.room1)


class TestUndressNamesTheGarment(_UndressCase):
    """Through the whole command, on a corpse (it cannot refuse)."""

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        body = self.corpse()
        coat = self.garment(BRANDED, where=body, aliases=(ALIAS,))
        shirt = self.garment("a work shirt", where=body)
        self.call(CmdUndress(), f"corpse {ALIAS}")
        self.assertEqual(coat.location, self.char1)
        self.assertEqual(shirt.location, body)

    def test_an_ordinal_picks_the_second_twin(self):
        """The dash form: `undress` splits target from item at the last
        space, so the item phrase is one token."""
        body = self.corpse()
        first = self.garment("jacket", where=body)
        second = self.garment("jacket", where=body)
        self.call(CmdUndress(), "corpse jacket-2")
        self.assertEqual(second.location, self.char1)
        self.assertEqual(first.location, body)

    def test_a_mid_word_fragment_is_refused(self):
        body = self.corpse()
        shirt = self.garment("a work shirt", where=body)
        out = self.call(CmdUndress(), "corpse irt")
        self.assertIn("isn't wearing 'irt'.", out)
        self.assertEqual(shirt.location, body)


class TestUndressTakesWhatWasNamed(_UndressCase):
    """The `pick_worn` cases from test_dressing_the_dead.py, on the
    door that replaced it."""

    def undress(self, target, phrase):
        cmd = CmdUndress()
        cmd.caller = self.char1
        return cmd._undress_remains(target, phrase)

    def test_it_takes_one_item_not_every_match(self):
        body = self.corpse()
        shirt = self.garment("a work shirt", where=body)
        dress_shirt = self.garment("a dress shirt", where=body)
        removed = self.undress(body, "shirt")
        self.assertEqual(len(removed), 1)
        self.assertIn(removed[0], (shirt, dress_shirt))

    def test_an_exact_key_beats_a_longer_match(self):
        body = self.corpse()
        dress_shirt = self.garment("a dress shirt", where=body)
        shirt = self.garment("shirt", where=body)
        self.assertEqual(self.undress(body, "shirt"), [shirt])
        self.assertEqual(dress_shirt.location, body)

    def test_an_alias_is_found(self):
        body = self.corpse()
        coat = self.garment(BRANDED, where=body, aliases=("coat",))
        self.assertEqual(self.undress(body, "coat"), [coat])

    def test_an_unmatched_phrase_finds_nothing(self):
        body = self.corpse()
        self.garment("a shirt", where=body)
        self.assertEqual(self.undress(body, "hat"), [])

    def test_an_empty_phrase_finds_nothing(self):
        """An empty name is refused before any search runs."""
        body = self.corpse()
        shirt = self.garment("a shirt", where=body)
        out = self.call(CmdUndress(), "")
        self.assertIn("Usage: undress <target> [<item>]", out)
        self.assertEqual(shirt.location, body)


class TestUndressingTheLiving(_UndressCase):
    """`_undress_character` reads the same matcher over the target's
    worn list, a pool that sits on someone else."""

    def test_the_named_garment_by_alias_comes_off(self):
        coat = self.garment(BRANDED, where=self.char2, aliases=(ALIAS,))
        shirt = self.garment(
            "a work shirt", where=self.char2, coverage=("left_arm",))
        self.char2.wear_item(coat)
        self.char2.wear_item(shirt)
        cmd = CmdUndress()
        cmd.caller = self.char1
        self.assertEqual(cmd._undress_character(self.char2, ALIAS), [coat])
        self.assertTrue(self.char2.is_item_worn(shirt))

    def test_a_mid_word_fragment_takes_nothing(self):
        shirt = self.garment("a work shirt", where=self.char2)
        self.char2.wear_item(shirt)
        cmd = CmdUndress()
        cmd.caller = self.char1
        self.assertEqual(cmd._undress_character(self.char2, "irt"), [])
        self.assertTrue(self.char2.is_item_worn(shirt))
