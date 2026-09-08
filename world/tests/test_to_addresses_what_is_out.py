"""`to` addresses what is OUT, and the radio rule falls out of it (#3029).

`to` had no reachability rule at all for ordinary targets —
`caller.search` resolves the room plus your entire inventory, so you
could address a crate on the floor or something buried in a pocket —
and then a bespoke extra restriction for radios bolted on top:

```python
if is_radio(target):
    if (target not in caller.contents
            and target is not seated_base_station(caller)):
```

Two answers to one question, and the radio one was the odd shape. The
owner's call was that `to` should simply be able to address the things
around you, and that the radio case would then solve itself.

**The rule: you can address what is out where you or the room can see
it.** Anything in the room — people, corpses, a console, a crate — plus
anything on your person that is held or worn. What it excludes is the
pocket.

That settles the radio disagreement without a word about radios. A
pocketed handset is neither held nor worn, so `to` now refuses it
exactly as `xmit` already did (`active_transmit_radio`: *"a radio
merely carried in a pocket can receive but not be spoken through"*).
And the dispatch-board special case disappears rather than moving: a
board you are seated at is in the room, so the general rule covers it.

**Speaking AT a radio and transmitting THROUGH one are different
acts, and only the second wants it in your hands.** My first cut
collapsed them and let a base station in the room be transmitted
through while standing — which broke `test_to_console_refuses_the_
standing`, because the desk seam is that you take the chair. The
operating rule stays, but it is no longer written out a second time:
`world.radio.can_transmit_through` is the same worn / held /
seated-board answer `xmit` gets from `active_transmit_radio`, so the
picker and the judge cannot drift apart again. That divergence — not
the existence of a check — was the actual defect.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdCommunication import CmdTo


def addressable(caller, target):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree. A module-scope import of a function that does not
    exist yet turns every test in the file into a loader error, and a
    loader error is not evidence of anything — the behavioural tests
    below have to run before AND after to mean something."""
    from commands import CmdCommunication
    return CmdCommunication.addressable(caller, target)


class _ToCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1

    def item(self, key="a walkie", location=None, radio=False):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=location or self.room1)
        if radio:
            # A REAL radio, not `patch("world.radio.is_radio",
            # return_value=True)`. That patch is too broad to be safe
            # here: `_held_radios` walks every hand slot, so an always-
            # true `is_radio` makes an EMPTY hand read as a radio and
            # `active_transmit_radio` returns None from `held[0]`. The
            # stub, not the code, was the thing under test.
            obj.db.is_radio = True
            obj.db.radio_on = True
            obj.db.frequency = "447"
        return obj

    def pocketed(self, key="a walkie", radio=False):
        return self.item(key, location=self.char1, radio=radio)

    def held(self, key="a walkie", radio=False):
        obj = self.pocketed(key, radio=radio)
        self.char1.wield_item(obj, "right_hand")
        assert self.char1.is_wielding(obj), "fixture never took it in hand"
        return obj

    def worn(self, key="a jacket", radio=False):
        obj = self.pocketed(key, radio=radio)
        obj.coverage = ["chest"]
        obj.worn_desc = key
        assert self.char1.wear_item(obj)[0], "fixture never went on"
        return obj


class TestThePredicate(_ToCase):
    def test_a_person_in_the_room_is_addressable(self):
        self.assertTrue(addressable(self.char1, self.char2))

    def test_a_thing_in_the_room_is_addressable(self):
        self.assertTrue(addressable(self.char1, self.item()))

    def test_something_held_is_addressable(self):
        self.assertTrue(addressable(self.char1, self.held()))

    def test_something_worn_is_addressable(self):
        self.assertTrue(addressable(self.char1, self.worn()))

    def test_something_pocketed_is_not(self):
        self.assertFalse(addressable(self.char1, self.pocketed()))

    def test_something_in_another_room_is_not(self):
        self.assertFalse(
            addressable(self.char1, self.item(location=self.room2)))

    def test_nothing_is_not(self):
        self.assertFalse(addressable(self.char1, None))


class TestThePocketedRadioSettlesItself(_ToCase):
    """The disagreement this issue was filed about — resolved by the
    general rule, with no radio-specific code left."""

    def test_a_pocketed_radio_is_refused(self):
        self.pocketed(radio=True)
        with patch("world.radio.transmit") as sent:
            out = self.call(CmdTo(), "walkie all clear")
        sent.assert_not_called()
        self.assertIn("stowed away", out)

    def test_a_held_radio_transmits(self):
        self.held(radio=True)
        with patch("world.radio.transmit") as sent:
            self.call(CmdTo(), "walkie all clear")
        sent.assert_called_once()

    def test_a_worn_radio_transmits(self):
        """`xmit` prefers WORN over held; `to` must not disagree."""
        self.worn("a headset", radio=True)
        with patch("world.radio.transmit") as sent:
            self.call(CmdTo(), "headset all clear")
        sent.assert_called_once()

    def test_it_agrees_with_what_xmit_would_pick(self):
        """Same question asked of both doors, same answer — that is the
        whole fix. `xmit` picks a device, `to` judges the one it was
        handed, and both now read the worn/held/seated rule."""
        from world.radio import active_transmit_radio, can_transmit_through
        pocketed = self.pocketed(radio=True)
        self.assertIsNone(active_transmit_radio(self.char1))
        self.assertFalse(can_transmit_through(self.char1, pocketed))
        self.assertFalse(addressable(self.char1, pocketed))

    def test_the_picker_and_the_judge_agree_on_a_held_set(self):
        from world.radio import active_transmit_radio, can_transmit_through
        held = self.held(radio=True)
        self.assertIs(active_transmit_radio(self.char1), held)
        self.assertTrue(can_transmit_through(self.char1, held))


class TestPeopleAndThingsStillWork(_ToCase):
    def test_you_can_still_speak_to_a_person(self):
        out = self.call(CmdTo(), "Char2 you still there")
        self.assertIn("you still there", out)

    def test_you_can_still_speak_at_a_thing_in_the_room(self):
        """Not removed. The owner was hesitant about room items, so this
        pins that nothing was quietly taken away."""
        self.item("a crate")
        out = self.call(CmdTo(), "crate what are you hiding")
        self.assertIn("what are you hiding", out)

    def test_a_console_you_are_seated_at_needs_no_special_case(self):
        """`seated_base_station` used to be named here. A board in the
        room is in the room."""
        board = self.item("a dispatch board")
        self.assertTrue(addressable(self.char1, board))

    def test_a_radio_on_the_floor_can_be_spoken_AT(self):
        """Addressable — it is in the room and you can see it."""
        self.assertTrue(addressable(self.char1, self.item("a base set")))

    def test_but_not_spoken_THROUGH(self):
        """The two acts are different. Speaking at a set on the floor is
        speech; keying it is operating it, and that wants it in your
        hands — or, for a console, the seat."""
        self.item("a base set", radio=True)
        with patch("world.radio.transmit") as sent:
            out = self.call(CmdTo(), "base set all clear")
        sent.assert_not_called()
        self.assertIn("take the seat", out)
