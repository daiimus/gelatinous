"""An explosion does not reach through a wall (#2490).

Two independent defects, each survivable alone and harmful together.

## The blast list had no room filter

`get_unified_explosion_proximity` starts from the grenade's own
proximity list, then merges in each proximate character's **combat**
proximity. The merge is deliberate — the human-shield mechanic has to
work regardless of when the grapple was established relative to the
grenade landing — but it is transitive and never asked where those
people are standing. The damage loop's only guard is
`hasattr(character, 'msg')`: *"is this a character?"*.

Tellingly, the code immediately after the damage loop sends the observer
message to `character.location`. It already knew the victim might be
somewhere else. It just never asked whether they should have been hit.

## Combat movement never cleared proximity

Proximity cleanup lived in exactly one place — `Exit.at_traverse` — and
**combat does not traverse exits**. `advance`, a cross-room `charge` and
a grapple drag all call `char.move_to(target_room)` directly.

Those paths hand-roll the traversal side effects and got three of four:
both `_do_advance_move` and `_resolve_charge_cross_room` re-implement
aim clearing, the rigged-grenade check and auto-defuse, and neither
clears proximity. An incomplete compensation list rather than an
oversight — someone enumerated what traversal does and missed an item.

## Composed

A and B fight in the bar with a live grenade on the floor; both are in
its proximity. A advances to the back room — direct `move_to`, so A
keeps the link to B *and* stays in the grenade's list. The grenade goes
off. A takes chest damage through a wall, and anyone still linked to A
by combat proximity is pulled in with them, whatever room they are in.

The dragged victim keeps proximity on purpose, exactly as
`at_traverse` exempts one — they stay adjacent to whoever is dragging
them. The room filter is what makes that safe.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import NDB_PROXIMITY, NDB_PROXIMITY_UNIVERSAL
# `clear_proximity_on_room_change` is NEW, so a module-scope import of
# it turns this whole file into a loader error against the unfixed code
# — which proves nothing about the blast-room half. Imported per test.
from world.combat.proximity import establish_proximity, is_in_proximity


class _BlastCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.grenade = create_object("typeclasses.items.Item",
                                     key="a grenade", location=self.room1)

    def in_blast(self, *chars):
        setattr(self.grenade.ndb, NDB_PROXIMITY_UNIVERSAL, list(chars))
        for char in chars:
            setattr(char.ndb, NDB_PROXIMITY_UNIVERSAL, [self.grenade])

    def unified(self):
        from commands.explosion_utils import get_unified_explosion_proximity
        return get_unified_explosion_proximity(self.grenade)


class TestTheBlastStopsAtTheWall(_BlastCase):
    def test_someone_who_walked_out_is_not_hit(self):
        self.in_blast(self.char1, self.char2)
        self.char1.location = self.room2
        self.assertNotIn(self.char1, self.unified())

    def test_the_person_still_standing_over_it_is(self):
        self.in_blast(self.char1, self.char2)
        self.char1.location = self.room2
        self.assertIn(self.char2, self.unified())

    def test_a_transitive_link_into_another_room_is_dropped(self):
        """The composed failure: B is pulled in through A's combat
        proximity, from a room the grenade is not in."""
        far = create_object("typeclasses.characters.Character",
                            key="someone else", location=self.room2)
        self.in_blast(self.char1)
        establish_proximity(self.char1, far)
        self.assertNotIn(far, self.unified())

    def test_a_transitive_link_in_the_SAME_room_is_kept(self):
        """The merge exists for the human shield; it must survive."""
        self.in_blast(self.char1)
        establish_proximity(self.char1, self.char2)
        self.assertIn(self.char2, self.unified())

    def test_everyone_present_is_still_included(self):
        self.in_blast(self.char1, self.char2)
        found = self.unified()
        self.assertIn(self.char1, found)
        self.assertIn(self.char2, found)


class TestCombatMovementClearsProximity(EvenniaTest):
    def clear(self, character):
        from world.combat.proximity import clear_proximity_on_room_change
        return clear_proximity_on_room_change(character)

    def test_the_melee_link_is_dropped(self):
        establish_proximity(self.char1, self.char2)
        self.assertTrue(is_in_proximity(self.char1, self.char2))
        self.clear(self.char1)
        self.assertFalse(is_in_proximity(self.char1, self.char2))

    def test_it_is_dropped_on_both_sides(self):
        establish_proximity(self.char1, self.char2)
        self.clear(self.char1)
        self.assertNotIn(self.char1,
                         getattr(self.char2.ndb, NDB_PROXIMITY) or set())

    def test_the_grenade_link_is_dropped_too(self):
        grenade = create_object("typeclasses.items.Item", key="a grenade",
                                location=self.room1)
        setattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [self.char1])
        setattr(self.char1.ndb, NDB_PROXIMITY_UNIVERSAL, [grenade])
        self.clear(self.char1)
        self.assertEqual(
            getattr(self.char1.ndb, NDB_PROXIMITY_UNIVERSAL), [])
        self.assertNotIn(self.char1,
                         getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL))

    def test_someone_with_no_links_is_fine(self):
        self.clear(self.char1)   # must not raise

    def test_an_unrelated_pair_is_untouched(self):
        third = create_object("typeclasses.characters.Character",
                              key="a third", location=self.room1)
        establish_proximity(self.char2, third)
        self.clear(self.char1)
        self.assertTrue(is_in_proximity(self.char2, third))


class TestTheMoversCallIt(EvenniaTest):
    """Pinned at the source: three direct `move_to` sites, and the
    compensation list beside them already forgot this once."""

    def source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "world" / "combat" /
                "movement_resolution.py").read_text(errors="ignore")

    def test_every_direct_move_clears_first(self):
        body = self.source()
        moves = body.count("char.move_to(target_room)")
        clears = body.count("clear_proximity_on_room_change(char)")
        self.assertGreaterEqual(clears, moves,
                                "a direct move_to with no proximity clear")

    def test_the_dragged_victim_is_still_exempt(self):
        """`at_traverse` exempts a dragged character on purpose — they
        stay adjacent to whoever is dragging them."""
        body = self.source()
        self.assertNotIn("clear_proximity_on_room_change(grappled_victim)",
                         body)
