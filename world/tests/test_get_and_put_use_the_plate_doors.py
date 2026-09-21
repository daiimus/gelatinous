"""`get <plate> from <carrier>` and `put <plate> in <carrier>` are the
unslot and slot doors (#3619; owner ruling: "get/put should work as
unslot/slot but require further clarification with the from command").

`get` used to lift a slotted plate out through the plain container path
and leave `installed_plates` pointing at it: the carrier kept counting a
plate that was in your hand, `slot list` showed it, and `unslot` "found"
it. There was no `put` at all except a `put` alias on the Kettle's locker
bank, which a game-wide verb would have collided with in that one room.

Asserts on STATE (carrier.installed_plates, plate.location, hands) and
on the one word of a message that tells the doors apart.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdArmor import CmdSlot, CmdUnslot, peel_slot_name
from commands.CmdInventory import CmdGet, CmdPut
from typeclasses.lockers import CmdLockerStash
from world.prototypes import CERAMIC_PLATES, PLATE_CARRIER, STANDARD_PLATE


class _PlateCase(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.carrier = spawn(PLATE_CARRIER)[0]
        self.plate = spawn(STANDARD_PLATE)[0]
        for o in (self.carrier, self.plate):
            o.move_to(self.char1, quiet=True)
        self.char1.wield_item(self.plate, hand="right")
        self.knife = create_object("typeclasses.items.Item", key="knife",
                                   location=self.char1)

    def _installed(self):
        return {k: v for k, v in (self.carrier.installed_plates or {}).items() if v}

    def _slot_it(self, slot="front"):
        self.call(CmdSlot(), f"standard plate in plate carrier {slot}")
        assert self._installed().get(slot) is self.plate, self._installed()

    def _fill_hands(self):
        for hand in ("left", "right"):
            if self.char1.hands.get(f"{hand}_hand") is None:
                filler = spawn(CERAMIC_PLATES)[0]
                filler.move_to(self.char1, quiet=True)
                self.char1.wield_item(filler, hand=hand)
        assert all(self.char1.hands.values()), self.char1.hands


class GetFromACarrierIsUnslot(_PlateCase):

    def test_get_from_carrier_takes_the_plate_and_clears_the_ledger(self):
        self._slot_it()
        self.call(CmdGet(), "standard plate from plate carrier")
        self.assertEqual(self.plate.location, self.char1)
        self.assertIn(self.plate, self.char1.hands.values(), "plate did not land in a hand")
        self.assertNotIn(self.plate, self._installed().values(),
                         "the defect: installed_plates still points at the plate")

    def test_get_from_a_worn_carrier(self):
        self.char1.wear_item(self.carrier)
        assert self.char1.is_item_worn(self.carrier)
        self._slot_it()
        self.call(CmdGet(), "standard plate from plate carrier")
        self.assertEqual(self.plate.location, self.char1)
        self.assertNotIn(self.plate, self._installed().values())

    def test_get_with_full_hands_leaves_the_plate_in(self):
        # The hands rule rides the door: the plain get path would have
        # shifted a held item to the pack and taken the plate anyway.
        self._slot_it()
        self._fill_hands()
        out = self.call(CmdGet(), "standard plate from plate carrier")
        self.assertIn("hands are full", out or "")
        self.assertEqual(self.plate.location, self.carrier)
        self.assertIs(self._installed().get("front"), self.plate)

    def test_bare_get_cannot_see_into_a_carrier(self):
        # The "further clarification with the from command": without it
        # the plate is not on offer.
        self._slot_it()
        self.call(CmdGet(), "standard plate")
        self.assertEqual(self.plate.location, self.carrier)
        self.assertIs(self._installed().get("front"), self.plate)

    def test_get_from_a_carrier_on_the_floor(self):
        self._slot_it()
        self.carrier.move_to(self.room1, quiet=True)
        out = self.call(CmdGet(), "standard plate from plate carrier")
        self.assertEqual(self.plate.location, self.char1)
        self.assertNotIn(self.plate, self._installed().values())
        self.assertIn("of the plate carrier", out or "")
        self.assertNotIn("your plate carrier", out or "")

    def test_a_loose_item_in_a_carrier_still_comes_out_the_plain_way(self):
        # Only an INSTALLED plate takes the unslot door.
        self.knife.move_to(self.carrier, quiet=True)
        out = self.call(CmdGet(), "knife from plate carrier")
        self.assertEqual(self.knife.location, self.char1)
        self.assertIn("take", out or "")
        self.assertNotIn("pull", out or "")


class PutInACarrierIsSlot(_PlateCase):

    def test_put_plate_in_carrier_installs_it(self):
        self.call(CmdPut(), "standard plate in plate carrier")
        self.assertIn(self.plate, self._installed().values(), self._installed())
        self.assertEqual(self.plate.location, self.carrier)
        self.assertNotIn(self.plate, self.char1.hands.values(), "the hand was not released")

    def test_put_names_a_slot(self):
        self.call(CmdPut(), "standard plate in plate carrier back")
        self.assertIs(self._installed().get("back"), self.plate)

    def test_put_names_a_two_word_slot(self):
        self.call(CmdPut(), "standard plate in plate carrier left side")
        self.assertIs(self._installed().get("left_side"), self.plate)

    def test_put_requires_the_plate_in_a_hand(self):
        self.char1.unwield_item("right")
        assert self.plate not in self.char1.hands.values()
        out = self.call(CmdPut(), "standard plate in plate carrier")
        self.assertIn("holding", out or "")
        self.assertNotIn(self.plate, self._installed().values())
        self.assertEqual(self.plate.location, self.char1)

    def test_put_a_non_plate_in_a_carrier_is_refused(self):
        self.char1.wield_item(self.knife, hand="left")
        out = self.call(CmdPut(), "knife in plate carrier")
        self.assertIn("not an armor plate", out or "")
        self.assertEqual(self.knife.location, self.char1)
        self.assertEqual(self._installed(), {})

    def test_put_into_a_carrier_on_the_floor(self):
        self.carrier.move_to(self.room1, quiet=True)
        out = self.call(CmdPut(), "standard plate in plate carrier front")
        self.assertIs(self._installed().get("front"), self.plate)
        self.assertIn("of the plate carrier", out or "")

    def test_put_and_get_round_trip(self):
        self.call(CmdPut(), "standard plate in plate carrier front")
        assert self._installed().get("front") is self.plate
        self.call(CmdGet(), "standard plate from plate carrier")
        self.assertEqual(self._installed(), {})
        self.assertIn(self.plate, self.char1.hands.values())


class PutRefusesWhatCannotHold(_PlateCase):

    def test_a_plain_item_cannot_hold_anything(self):
        crate = create_object("typeclasses.items.Item", key="crate", location=self.room1)
        self.char1.wield_item(self.knife, hand="left")
        out = self.call(CmdPut(), "knife in crate")
        self.assertIn("can't hold that", out or "")
        self.assertEqual(self.knife.location, self.char1)
        self.assertEqual(list(crate.contents), [])

    def test_a_person_is_not_a_container(self):
        self.char2.location = self.room1
        out = self.call(CmdPut(), f"knife in {self.char2.key}")
        self.assertIn("give", out or "")
        self.assertEqual(self.knife.location, self.char1)

    def test_no_preposition_prints_usage(self):
        out = self.call(CmdPut(), "knife plate carrier")
        self.assertIn("Usage", out or "")
        self.assertEqual(self._installed(), {})

    def test_nothing_named_is_a_plain_miss(self):
        out = self.call(CmdPut(), "knife in the void")
        self.assertIn("don't see", out or "")

    def test_an_article_alone_is_usage_not_an_empty_miss(self):
        out = self.call(CmdPut(), "knife in the")
        self.assertIn("Usage", out or "")
        self.assertNotIn("''", out or "")

    def test_the_room_is_not_a_container(self):
        out = self.call(CmdPut(), "knife in here")
        self.assertIn("drop", out or "")
        self.assertEqual(self.knife.location, self.char1)

    def test_me_as_the_item_is_not_carried(self):
        # `me`/`here` short-circuit Character.search ahead of location=,
        # so a name-taking door got the caller back (review, #3619).
        for name in ("me", "here"):
            out = self.call(CmdPut(), f"{name} in plate carrier")
            self.assertIn("aren't carrying", out or "", name)
        self.assertEqual(self._installed(), {})
        self.assertEqual(self.char1.location, self.room1)

    def test_an_item_on_the_floor_is_not_already_carried(self):
        rock = create_object("typeclasses.items.Item", key="rock", location=self.room1)
        out = self.call(CmdPut(), "rock in me")
        self.assertIn("aren't carrying", out or "")
        self.assertNotIn("already", out or "")
        self.assertEqual(rock.location, self.room1)

    def test_a_hidden_carrier_is_not_on_offer(self):
        # `hide` sets db.hidden; `get` already refuses to see it (#2476).
        self.carrier.move_to(self.room1, quiet=True)
        self.carrier.db.hidden = True
        out = self.call(CmdPut(), "standard plate in plate carrier")
        self.assertIn("don't see", out or "")
        self.assertEqual(self._installed(), {})
        self.assertEqual(self.plate.location, self.char1)


class PutInLockerIsStash(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.bank = create_object("typeclasses.lockers.LockerBank",
                                  key="bank of lockers", location=self.room1)
        self.bank.aliases.add(["lockers", "locker bank", "locker"])
        self.knife = create_object("typeclasses.items.Item", key="knife",
                                   location=self.char1)
        self.char1.wield_item(self.knife, hand="right")

    def _leased_and_open(self):
        return patch.object(type(self.bank), "_can_use", return_value=True)

    def _in_the_bank(self, item):
        return item.location is not None and item.location.location is self.bank

    def test_put_in_locker_stows_it(self):
        with self._leased_and_open():
            self.call(CmdPut(), "knife in locker")
        self.assertTrue(self._in_the_bank(self.knife), self.knife.location)
        self.assertNotIn(self.knife, self.char1.hands.values())

    def test_put_in_my_locker_reads(self):
        with self._leased_and_open():
            self.call(CmdPut(), "knife in my locker")
        self.assertTrue(self._in_the_bank(self.knife), self.knife.location)

    def test_no_lease_is_the_locker_s_own_refusal(self):
        out = self.call(CmdPut(), "knife in locker")
        self.assertIn("rent", out or "")
        self.assertEqual(self.knife.location, self.char1)

    def test_the_bank_no_longer_carries_a_put_alias(self):
        # Two commands answering `put` in one room would have hidden one
        # of them; the game verb hands a locker target to `stash_item`.
        self.assertNotIn("put", CmdLockerStash.aliases)
        self.assertEqual(CmdLockerStash.key, "stash")

    def test_one_put_answers_in_the_locker_room(self):
        # The merged cmdset a player has standing at the bank: the
        # character set plus the bank's own. Exactly one command matches
        # `put`, and it is the game verb. (execute_cmd is inert under
        # `evennia test`, so the merge is built by hand.)
        from commands.default_cmdsets import CharacterCmdSet
        from typeclasses.lockers import LockerCmdSet
        merged = CharacterCmdSet() + LockerCmdSet()
        answering = [c for c in merged.commands
                     if c.key == "put" or "put" in (c.aliases or [])]
        self.assertEqual([type(c) for c in answering], [CmdPut], answering)

    def test_me_cannot_be_stowed(self):
        # `stash me` filed the PLAYER into the compartment, hooks off,
        # with no exits and no verbs; `put me in locker` reached the same
        # door (review, #3619). Both refused: `put` never resolves `me`
        # as an item, and the door itself takes Items only.
        with self._leased_and_open():
            stash_out = self.call(CmdLockerStash(), "me", obj=self.bank)
            put_out = self.call(CmdPut(), "me in locker")
        self.assertIn("can't stow", stash_out or "")
        self.assertIn("aren't carrying", put_out or "")
        self.assertEqual(self.char1.location, self.room1)
        self.assertEqual(list(self.bank.contents), [], "a compartment was created for nothing")

    def test_me_cannot_be_retrieved(self):
        # The sibling door: `retrieve me` handed the caller back and tried
        # to move them into themselves (a location loop), after writing
        # locker_owner onto the player (review, #3619).
        from typeclasses.lockers import CmdLockerRetrieve
        with self._leased_and_open():
            out = self.call(CmdLockerRetrieve(), "me", obj=self.bank)
        self.assertIn("holds no", out or "")
        self.assertEqual(self.char1.location, self.room1)
        self.assertFalse(self.char1.attributes.has("locker_owner"))


class SlotAndUnslotAreHandsWork(_PlateCase):
    """Channeling refuses every hands verb (#3376); `put`/`get` did and
    `slot`/`unslot` did not, so the same act had two answers (#3635)."""

    def _channeling(self):
        from world import channeled as ch
        ok = ch.begin_channel(self.char1, 60, "at the wall", lambda: None,
                              lambda f: None, key="spraying")
        assert ok, "begin_channel refused"

    def test_slot_is_refused_mid_channel(self):
        self._channeling()
        out = self.call(CmdSlot(), "standard plate in plate carrier")
        self.assertEqual(self._installed(), {}, out)
        self.assertEqual(self.plate.location, self.char1)

    def test_unslot_is_refused_mid_channel(self):
        self._slot_it()
        self._channeling()
        self.call(CmdUnslot(), "standard plate from plate carrier")
        self.assertIs(self._installed().get("front"), self.plate)
        self.assertEqual(self.plate.location, self.carrier)


class PeelSlotName(EvenniaCommandTest):

    def test_peels(self):
        self.assertEqual(peel_slot_name(["plate", "carrier", "front"]), ("front", ["plate", "carrier"]))
        self.assertEqual(peel_slot_name(["plate", "carrier", "left", "side"]), ("left_side", ["plate", "carrier"]))
        self.assertEqual(peel_slot_name(["plate", "carrier", "left-side"]), ("left_side", ["plate", "carrier"]))
        self.assertEqual(peel_slot_name(["plate", "carrier"]), (None, ["plate", "carrier"]))
        self.assertEqual(peel_slot_name([]), (None, []))
