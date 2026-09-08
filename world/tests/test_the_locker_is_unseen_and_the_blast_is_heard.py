"""Lockers keep their promise, and a stuck grenade is heard (#2621,
#2549).

## #2621 — "can never reach — or even see"

`LockerBank`'s own docstring promises each lease a hidden compartment
others *"can never reach — or even see"*. The compartments are plain
`Item`s carrying only a `get:false()` lock — which keeps hands off and
does nothing about eyes — and the class did not override the default
enumeration, so `look lockers` answered

```
You see: two locker compartments
```

to anybody. Two things wrong: the promise, and the **count**, which
leaks how many lockers are let — a fact about other people's tenancy.

`BarCounter`, named as the model in this module's own opening
docstring, suppresses exactly this listing for exactly this reason. It
was not copied.

## #2549 — the blast the room never heard

`grenade.location` is the room only when the grenade is lying loose. A
sticky grenade's location is the **armor it is stuck to**, so a grenade
on armor lying on the ground broadcast into that item's (empty)
contents: no explosion line in the room, no adjacent-room warning —
while the damage still landed.

`get_explosion_room` exists for this and walks grenade → armor →
character/room. It was already being *called* forty lines up, in the
stuck-on-the-ground branch, and its result was used once inside a debug
string and then discarded.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _LockerCase(EvenniaTest):
    def bank(self, leases=2):
        bank = create_object("typeclasses.lockers.LockerBank",
                             key="lockers", location=self.room1)
        for i in range(leases):
            s = create_object("typeclasses.items.Item",
                              key="locker compartment", location=bank)
            s.db.locker_owner = f"uid-{i}"
            s.db.integrate = True
            s.locks.add("get:false()")
        return bank


class TestTheCompartmentsAreNotListed(_LockerCase):
    def test_a_stranger_sees_no_compartments(self):
        bank = self.bank()
        self.assertEqual(bank.get_display_things(self.char2), "")

    def test_the_count_does_not_leak(self):
        bank = self.bank(leases=5)
        shown = bank.return_appearance(self.char2)
        self.assertNotIn("compartment", shown)

    def test_nor_to_a_lessee(self):
        """A lessee gets their own contents line instead — the listing
        is suppressed for everyone."""
        bank = self.bank()
        self.assertEqual(bank.get_display_things(self.char1), "")

    def test_the_bank_still_describes_itself(self):
        bank = self.bank()
        bank.db.desc = "A wall of dented steel lockers."
        self.assertIn("dented steel", bank.return_appearance(self.char2))

    def test_it_matches_the_model_it_names(self):
        """`BarCounter` is cited in this module's opening docstring as
        the pattern; both suppress the same listing."""
        counter = create_object("typeclasses.bar.BarCounter", key="a bar",
                                location=self.room1)
        self.assertEqual(counter.get_display_things(self.char2), "")
        self.assertEqual(self.bank().get_display_things(self.char2), "")


class TestAStuckGrenadeIsHeard(EvenniaTest):
    def armed(self, location):
        g = create_object("typeclasses.items.Item", key="a grenade",
                          location=location)
        g.db.is_explosive = True
        g.db.blast_damage = 6
        g.db.damage_type = "blast"
        g.db.dud_chance = 0.0
        return g

    def heard_by_the_room(self, grenade):
        said = []
        self.room1.msg_contents = lambda text=None, **kw: said.append(str(text))
        from commands.explosion_utils import explode_standalone_grenade
        with mock.patch("commands.explosion_utils."
                        "notify_adjacent_rooms_of_explosion") as adj:
            explode_standalone_grenade(grenade)
        return " ".join(said), adj

    def test_a_grenade_on_dropped_armor_is_heard(self):
        armor = create_object("typeclasses.items.Item", key="a vest",
                              location=self.room1)
        said, _adj = self.heard_by_the_room(self.armed(armor))
        self.assertIn("grenade", said.lower())

    def test_and_the_adjacent_rooms_are_warned(self):
        armor = create_object("typeclasses.items.Item", key="a vest",
                              location=self.room1)
        _said, adj = self.heard_by_the_room(self.armed(armor))
        adj.assert_called_once()
        self.assertIs(adj.call_args.args[0], self.room1)

    def test_a_loose_grenade_still_works(self):
        said, adj = self.heard_by_the_room(self.armed(self.room1))
        self.assertIn("grenade", said.lower())
        self.assertIs(adj.call_args.args[0], self.room1)

    def test_the_room_is_resolved_not_assumed(self):
        """`get_explosion_room` walks grenade -> armor -> room."""
        from world.combat.utils import get_explosion_room
        armor = create_object("typeclasses.items.Item", key="a vest",
                              location=self.room1)
        self.assertIs(get_explosion_room(self.armed(armor)), self.room1)
