"""The human shield works, and a grenade sticks to what you wear
(#2491, #2492).

## #2491 — a search that never searched

```python
for char in proximity_list:
    if hasattr(char.ndb, NDB_COMBAT_HANDLER):
        combat_handler = getattr(char.ndb, NDB_COMBAT_HANDLER)
        break
```

`hasattr` on an Evennia `ndb` is **always True** — `DbHolder.
__getattribute__` returns `None` for a missing key rather than raising.
So the loop matched on its first iteration every time, assigned
`proximity_list[0]`'s handler (which is `None` whenever that character
isn't fighting), and broke.

The guard three lines down then returned an empty modifier dict and the
entire human-shield mechanic was skipped: the grappler who should have
been shielded took full damage, the victim who should have absorbed
double took normal, and `send_grenade_shield_messages` never fired, so
there was no narration either. Silent and symmetric — which is why a
spec'd, checked-off feature could be dead without anyone noticing.

All four call sites rely on this discovery path; none passes a handler.

## #2492 — a grenade stuck to the wrong coat

`get_outermost_armor_at_location` had two independent defects.

**It never checked whether the item was worn.** The docstring said
"worn items" and the inline comment said "Check all worn items", and the
loop walked `character.contents` — everything they *carry*. The only
filter was `db.coverage`, which is a **prototype property**: a jacket
declares its coverage whether it is worn, held, or loose in a pocket. So
a sticky grenade could adhere to a spare jacket in the target's
inventory, and `establish_stick` would then set
`grenade.location = armor` — a live grenade bonded to a carried item.

**And it read `item.db.layer`**, bypassing the `Item.layer` property,
which falls back to `world.style.derive_rung` when nobody set one
explicitly. Every garment with a derived layer read as 0, so an outer
coat and a shirt tied and the first one seen won.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import NDB_COMBAT_HANDLER
from world.combat.explosives import (check_grenade_human_shield,
                                     get_outermost_armor_at_location)


class _ShieldCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.bystander = create_object("typeclasses.characters.Character",
                                       key="a bystander", location=self.room1)

    def handler_with_grapple(self, grappler, victim):
        handler = mock.MagicMock()
        from world.combat.constants import DB_CHAR, DB_GRAPPLING_DBREF
        handler.db.combatants = [
            {DB_CHAR: grappler, DB_GRAPPLING_DBREF: victim.dbref},
            {DB_CHAR: victim, DB_GRAPPLING_DBREF: None},
        ]
        return handler


class TestTheShieldFindsItsHandler(_ShieldCase):
    def test_a_bystander_first_in_the_list_does_not_kill_the_search(self):
        """The reported shape: the blast list starts with someone who
        is not fighting."""
        handler = self.handler_with_grapple(self.char1, self.char2)
        setattr(self.char1.ndb, NDB_COMBAT_HANDLER, handler)
        setattr(self.char2.ndb, NDB_COMBAT_HANDLER, handler)
        with mock.patch("world.combat.explosives.send_grenade_shield_messages"):
            mods = check_grenade_human_shield(
                [self.bystander, self.char1, self.char2])
        self.assertEqual(mods.get(self.char1), 0.0)
        self.assertEqual(mods.get(self.char2), 2.0)

    def test_the_grappler_is_shielded(self):
        handler = self.handler_with_grapple(self.char1, self.char2)
        setattr(self.char1.ndb, NDB_COMBAT_HANDLER, handler)
        with mock.patch("world.combat.explosives.send_grenade_shield_messages"):
            mods = check_grenade_human_shield([self.char1, self.char2])
        self.assertEqual(mods.get(self.char1), 0.0)

    def test_the_narration_fires(self):
        handler = self.handler_with_grapple(self.char1, self.char2)
        setattr(self.bystander.ndb, NDB_COMBAT_HANDLER, None)
        setattr(self.char1.ndb, NDB_COMBAT_HANDLER, handler)
        with mock.patch("world.combat.explosives.send_grenade_shield_messages") as say:
            check_grenade_human_shield([self.bystander, self.char1, self.char2])
        say.assert_called_once_with(self.char1, self.char2)

    def test_nobody_fighting_is_still_no_shield(self):
        mods = check_grenade_human_shield([self.bystander, self.char1])
        self.assertEqual(mods, {})

    def test_a_victim_outside_the_blast_is_not_shielded_against(self):
        handler = self.handler_with_grapple(self.char1, self.char2)
        setattr(self.char1.ndb, NDB_COMBAT_HANDLER, handler)
        with mock.patch("world.combat.explosives.send_grenade_shield_messages"):
            mods = check_grenade_human_shield([self.char1])   # victim absent
        self.assertEqual(mods, {})


class _ArmorCase(EvenniaTest):
    def garment(self, key, coverage=("chest",), layer=None, wear=True):
        item = create_object("typeclasses.items.Item", key=key,
                             location=self.char1)
        item.db.is_wearable = True
        item.db.coverage = list(coverage)
        item.db.worn_desc = key
        if layer is not None:
            item.db.layer = layer
        if wear:
            self.char1.wear_item(item)
        return item


class TestTheGrenadeSticksToWhatYouWear(_ArmorCase):
    def test_a_carried_jacket_is_not_a_target(self):
        carried = self.garment("a spare jacket", layer=9, wear=False)
        worn = self.garment("a shirt", layer=1)
        found = get_outermost_armor_at_location(self.char1, "chest")
        self.assertIsNot(found, carried, "it stuck to a jacket in the pocket")
        self.assertIs(found, worn)

    def test_with_nothing_worn_there_is_no_armour(self):
        self.garment("a spare jacket", layer=9, wear=False)
        self.assertIsNone(
            get_outermost_armor_at_location(self.char1, "chest"))

    def test_the_outermost_worn_layer_wins(self):
        self.garment("a shirt", layer=1)
        coat = self.garment("a coat", layer=5)
        self.assertIs(get_outermost_armor_at_location(self.char1, "chest"),
                      coat)

    def test_an_uncovered_location_finds_nothing(self):
        self.garment("a shirt", layer=1)
        self.assertIsNone(
            get_outermost_armor_at_location(self.char1, "left_leg"))


class TestTheDerivedLayerIsRead(_ArmorCase):
    """`Item.layer` falls back to `world.style.derive_rung`. Reading
    `db.layer` made every derived garment read 0, so ties went to
    whichever was seen first."""

    def test_a_derived_layer_is_not_zero(self):
        item = self.garment("a heavy overcoat", wear=False)
        self.assertIsNone(item.db.layer)
        self.assertIsNotNone(item.layer)

    def test_two_derived_garments_are_ordered_by_their_property(self):
        from world.style import derive_rung
        inner_key, outer_key = "a cotton undershirt", "a heavy overcoat"
        inner_rung, outer_rung = derive_rung(inner_key), derive_rung(outer_key)
        if None in (inner_rung, outer_rung) or inner_rung == outer_rung:
            self.skipTest("these two names do not derive distinct rungs")
        inner = self.garment(inner_key)
        outer = self.garment(outer_key)
        expected = outer if outer_rung > inner_rung else inner
        self.assertIs(get_outermost_armor_at_location(self.char1, "chest"),
                      expected)

    def test_an_explicit_layer_still_wins_over_a_derived_one(self):
        self.garment("a heavy overcoat")          # derived
        explicit = self.garment("a shirt", layer=99)
        self.assertIs(get_outermost_armor_at_location(self.char1, "chest"),
                      explicit)
