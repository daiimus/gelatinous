"""A delivery is something the room can see.

Regression pin for #2716. `hand_over` moves the parcel with
`quiet=True, move_hooks=False` and there was no room broadcast anywhere
in the module -- so a courier walked in, handed a parcel across the
counter and took a fee out of the till while every observer saw nothing.
The ORIGIN of a run was narrated; its arrival was not.

Narrated through `emote`, the same door a player's pose uses, so the
identity layer renders both parties per observer. No bespoke broadcast.

The issue's other half -- the fee being taken whether or not anything
was delivered -- was already fixed by #2763, and its gate is left
untouched here.
"""

from unittest import TestCase
from unittest.mock import MagicMock

from world.director.courier import hand_over


def _counter(till=999):
    counter = MagicMock()
    counter.key = "the slab"
    counter.attributes.get.return_value = till
    return counter


def _package(moves=True):
    pkg = MagicMock()
    pkg.key = "courier parcel"
    pkg.pk = 1
    pkg.move_to.return_value = moves
    return pkg


class TestTheFarEndOfARunIsVisible(TestCase):

    def _emotes(self, soul):
        return [c.args[0] for c in soul.execute_cmd.call_args_list
                if c.args and str(c.args[0]).startswith("emote")]

    def test_a_delivery_is_narrated(self):
        soul = MagicMock()
        out = hand_over(soul, _counter(), _package())
        self.assertTrue(out["delivered"])
        self.assertTrue(self._emotes(soul), "the room saw nothing")

    def test_the_parcel_is_named_in_the_beat(self):
        soul = MagicMock()
        hand_over(soul, _counter(), _package())
        self.assertIn("courier parcel", " ".join(self._emotes(soul)))

    # -- controls ----------------------------------------------------

    def test_a_failed_delivery_is_not_narrated(self):
        """No parcel changed hands, so there is nothing to announce —
        and the fee gate (#2763) still returns early."""
        soul = MagicMock()
        out = hand_over(soul, _counter(), _package(moves=False))
        self.assertFalse(out["delivered"])
        self.assertEqual(self._emotes(soul), [])

    def test_no_parcel_is_not_narrated_and_not_paid(self):
        soul = MagicMock()
        out = hand_over(soul, _counter(), None)
        self.assertFalse(out["delivered"])
        self.assertEqual(out["paid"], 0)
        self.assertEqual(self._emotes(soul), [])
