"""Two more side-effects that ran before their guard (#2599, #2598).

## #2599 — a refused `wear` left the garment out of your hand

`wear_item` pulled the item out of the wearer's hand and into inventory,
then evaluated layer conflicts and rejected **140 lines later**. Nothing
on the failure path put it back.

A player holding a jacket types `wear jacket` while already wearing
something at that layer. They are told it conflicts — correctly — and the
jacket is now in their inventory, not their hand. Every hand-slot
consumer (`get_wielded_weapon`, `inventory`, the throw / hide / give
matchers) then sees an empty hand for an action that was **refused**, and
re-wielding is a second command the player has no reason to know they
need.

The unwield now happens after the conflict check. That is safe because a
wielded item is already in `self.contents` — `wield_item` refuses
otherwise — so the "are you carrying it" validation holds either way.

**This was not a #2536 hand desync.** The write-back at the unwield is
the correct PR-H2 form and is unchanged; the hand state was persisted
faithfully, to the wrong value.

## #2598 — `order` is a fourth open-speech door

#2530 wired `say` / `to` / `emote` / `.pose` to `break_stealth`. `order`
routes arbitrary player text through the same `broadcast_speech`
backbone and called it nowhere, so a hidden patron could speak aloud to
the whole room and stay hidden. Its own comment calls it *"directed
speech … the room hears the order … as it does to any other spoken
line."*

`STEALTH_AND_DETECTION_SPEC` exempts exactly one speech verb —
`whisper` — and says nothing about `order`.

Placed **below every guard**, per the lesson of #2530: `break_stealth`
is the reveal, not a test, so a mistyped order must not blow your cover
for something that never happened.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _WearCase(EvenniaTest):
    def garment(self, key, coverage, layer=2):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=self.char1)
        obj.coverage = list(coverage)
        obj.worn_desc = key
        obj.db.layer = layer
        return obj

    def held(self):
        return dict(self.char1.held_items or {})


class TestARefusedWearKeepsItInHand(_WearCase):
    def setUp(self):
        super().setUp()
        self.worn = self.garment("a work shirt", ["chest"])
        self.assertTrue(self.char1.wear_item(self.worn)[0])
        self.spare = self.garment("a dress shirt", ["chest"])
        self.assertIn("wield",
                      self.char1.wield_item(self.spare, "right_hand").lower())

    def test_the_wear_is_refused(self):
        ok, _msg = self.char1.wear_item(self.spare)
        self.assertFalse(ok, "the layer conflict was not detected")

    def test_it_stays_in_the_hand(self):
        self.char1.wear_item(self.spare)
        self.assertEqual(self.held().get("right_hand"), self.spare)

    def test_the_hands_view_agrees(self):
        self.char1.wear_item(self.spare)
        self.assertTrue(self.char1.is_wielding(self.spare, "right_hand"))

    def test_it_is_not_worn_either(self):
        self.char1.wear_item(self.spare)
        self.assertFalse(self.char1.is_item_worn(self.spare))


class TestAnAcceptedWearStillTakesItFromTheHand(_WearCase):
    """The fix must move the unwield, not remove it."""

    def setUp(self):
        super().setUp()
        self.hat = self.garment("a felt hat", ["head"])
        self.assertIn("wield",
                      self.char1.wield_item(self.hat, "right_hand").lower())

    def test_the_wear_succeeds(self):
        ok, _msg = self.char1.wear_item(self.hat)
        self.assertTrue(ok)

    def test_the_hand_is_freed(self):
        self.char1.wear_item(self.hat)
        self.assertIsNone(self.held().get("right_hand"))

    def test_it_is_worn(self):
        self.char1.wear_item(self.hat)
        self.assertTrue(self.char1.is_item_worn(self.hat))

    def test_wearing_something_never_held_still_works(self):
        loose = self.garment("a scarf", ["neck"])
        self.assertTrue(self.char1.wear_item(loose)[0])
        self.assertTrue(self.char1.is_item_worn(loose))


class TestOrderBreaksStealth(EvenniaTest):
    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "typeclasses" / "bar.py").read_text(errors="ignore")

    def test_the_bar_calls_break_stealth(self):
        self.assertIn("break_stealth(caller)", self._source())

    def test_it_sits_below_the_guards(self):
        """Per #2530: the reveal must not fire for a refused order."""
        body = self._source()
        reveal = body.index("break_stealth(caller)")
        for guard in ('caller.msg("Order what?")',
                      'caller.msg("You aren\'t at the counter.")'):
            self.assertLess(body.index(guard), reveal,
                            f"the reveal runs before: {guard}")

    def test_it_is_above_the_broadcast(self):
        body = self._source()
        self.assertLess(body.index("break_stealth(caller)"),
                        body.index("broadcast_speech(caller, speech"))

    def test_every_open_speech_door_now_breaks_it(self):
        """The four from #2530 plus this one — the set is the point."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        comms = (root / "commands" / "CmdCommunication.py").read_text(
            errors="ignore")
        self.assertEqual(comms.count("break_stealth(caller)"), 4)
        self.assertEqual(self._source().count("break_stealth(caller)"), 1)

    def test_whisper_is_still_exempt(self):
        """The spec's one carve-out — the fix must not sweep it in."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        comms = (root / "commands" / "CmdCommunication.py").read_text(
            errors="ignore")
        start = comms.index("class CmdWhisper")
        end = comms.index("class ", start + 10)
        self.assertNotIn("break_stealth", comms[start:end])
