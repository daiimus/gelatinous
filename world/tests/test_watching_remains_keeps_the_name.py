"""Somebody who watches remains being dressed or stripped keeps the
name (#3833).

Owner, 2026-11-15, asked whether they should: "They should. That's just
Scooby-doo but backwards. We already account for that with someone
living, don't we?"

The living case is `test_an_eyewitness_keeps_the_name` (#3811). Half of
this one was already there: remains take their look from what they wear
(`test_identity_is_in_the_face`), and the name after a body is read
through what the observer watched, so somebody who saw a living person
pull a mask on still knows the corpse. What was missing is the writing.
The three doors that dress and strip remains moved the garment and told
nobody's memory:

* ``dress <corpse or head> in <item>``
* ``undress <corpse or head>``
* ``get <item> from <corpse or head>``

Everything here goes through those commands, on a corpse the game's own
factory makes and a head its own sever helper cuts, with people the
test creates. Nobody is a stand-in. People are made AFTER the death, so
nobody here watched anything the living person did.
"""
import time
from types import SimpleNamespace
from unittest import mock
from unittest.mock import MagicMock

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdClothing import CmdDress, CmdUndress
from commands.CmdInventory import CmdGet
from typeclasses.characters import Character
from typeclasses.death_progression import DeathProgressionScript
from typeclasses.items import spawn_severed_part_from_corpse
from world.forensics import carry_forensic_roll
from world.identity import (
    _room_holding,
    apply_remains_change,
    get_apparent_uid,
)

TWO_DAYS = 2 * 86400


class _AtTheBody(EvenniaCommandTest):
    """A body on the floor and the people around it.

    In the room: ``hand``, who does the dressing and stripping, and
    ``friend``, who watches; both know the bare face as Jorge.
    ``fence`` watches too and knows only the masked figure, as Ghost.
    ``stranger`` watches and knows nobody. In another room, seeing
    none of it: ``absent`` (knows the face) and ``absent_fence``
    (knows the mask).
    """

    #: Whether they died with the mask over the face.
    MASKED = False

    def setUp(self):
        super().setUp()
        self.dead = self.body("Jorvik Ansel", "sleeve-dead")
        self.mask = spawn("SKI_MASK")[0]
        self.mask.location = self.dead
        self.bare = get_apparent_uid(self.dead)
        ok, why = self.dead.wear_item(self.mask)
        self.assertTrue(ok, why)
        self.masked = get_apparent_uid(self.dead)
        self.assertNotEqual(self.bare, self.masked)
        if not self.MASKED:
            ok, why = self.dead.remove_item(self.mask)
            self.assertTrue(ok, why)
        self.corpse = DeathProgressionScript._create_corpse_from_character(
            None, self.dead)
        self.dead.location = self.room2

        self.hand = self.body("Asa Brandt", "sleeve-hand")
        self.friend = self.body("Wren Holt", "sleeve-friend")
        self.fence = self.body("Greta Voss", "sleeve-fence")
        self.stranger = self.body("Odile Marsh", "sleeve-stranger")
        self.absent = self.body("Petra Lund", "sleeve-absent", self.room2)
        self.absent_fence = self.body(
            "Tobin Reyes", "sleeve-absent-fence", self.room2)
        for who in (self.hand, self.friend, self.absent):
            who.recognition_memory = {self.bare: {"assigned_name": "Jorge"}}
        for who in (self.fence, self.absent_fence):
            who.recognition_memory = {self.masked: {"assigned_name": "Ghost"}}

    def body(self, key, sleeve, room=None):
        char = create_object(Character, key=key, location=room or self.room1)
        char.sleeve_uid = sleeve
        char.height, char.build, char.sdesc_keyword = "short", "lean", "man"
        char.recognition_memory = {}
        return char

    def shown(self, remains, who):
        return remains.get_display_name(who)

    def named(self, remains, who, name):
        shown = self.shown(remains, who)
        self.assertTrue(shown.endswith(f"({name})"), shown)

    def nameless(self, remains, who):
        self.assertNotIn("(", self.shown(remains, who))

    def dress(self, target="corpse"):
        self.mask.move_to(self.hand, quiet=True)
        return self.call(
            CmdDress(), f"{target} in {self.mask.key}", caller=self.hand)

    def undress(self, target="corpse"):
        return self.call(CmdUndress(), target, caller=self.hand)

    def take(self, target="corpse"):
        return self.call(
            CmdGet(), f"{self.mask.key} from {target}", caller=self.hand)


# ----------------------------------------------------------------------
# A mask goes on
# ----------------------------------------------------------------------

class TestAMaskGoesOnACorpse(_AtTheBody):
    def setUp(self):
        super().setUp()
        self.named(self.corpse, self.hand, "Jorge")      # before
        self.named(self.corpse, self.friend, "Jorge")
        self.said = self.dress()

    def test_the_mask_is_on(self):
        self.assertEqual(self.corpse.get_worn_items(), [self.mask])
        self.assertEqual(get_apparent_uid(self.corpse), self.masked)

    def test_whoever_put_it_on_still_knows_the_body(self):
        self.named(self.corpse, self.hand, "Jorge")

    def test_and_is_told_so_in_their_own_line(self):
        self.assertIn("(Jorge)", self.said)

    def test_somebody_watching_still_knows_it(self):
        self.named(self.corpse, self.friend, "Jorge")

    def test_their_memory_says_what_they_watched_it_come_from(self):
        entry = self.friend.recognition_memory[self.masked]
        self.assertEqual(entry["witnessed_from"], self.bare)
        self.assertEqual(entry["assigned_name"], "")

    def test_the_new_entry_says_what_was_seen(self):
        """Remains have no short description; the record is not blank."""
        entry = self.friend.recognition_memory[self.masked]
        self.assertTrue(entry["sdesc_at_first_encounter"])
        self.assertEqual(entry["sdesc_at_first_encounter"],
                         self.corpse._decay_display_name())

    def test_somebody_who_was_not_there_does_not(self):
        """The control: the mask conceals from whoever did not watch."""
        self.nameless(self.corpse, self.absent)
        self.assertNotIn(self.masked, self.absent.recognition_memory)

    def test_a_stranger_watching_learns_nothing(self):
        self.nameless(self.corpse, self.stranger)
        self.assertEqual(dict(self.stranger.recognition_memory), {})

    def test_somebody_who_knew_the_mask_sees_the_mask(self):
        self.named(self.corpse, self.fence, "Ghost")
        entry = self.fence.recognition_memory[self.masked]
        self.assertIsNone(entry.get("witnessed_from"))

    def test_off_again_and_everybody_keeps_what_they_had(self):
        self.undress()
        self.named(self.corpse, self.hand, "Jorge")
        self.named(self.corpse, self.friend, "Jorge")
        # The fence watched Ghost's mask come off: Ghost still.
        self.named(self.corpse, self.fence, "Ghost")

    def test_on_off_and_on_again(self):
        self.undress()
        self.dress()
        self.named(self.corpse, self.friend, "Jorge")
        self.named(self.corpse, self.hand, "Jorge")


class TestANameAlreadyHeldForTheMaskWins(_AtTheBody):
    def setUp(self):
        super().setUp()
        memory = dict(self.friend.recognition_memory)
        memory[self.masked] = {"assigned_name": "Ghost"}
        self.friend.recognition_memory = memory
        self.dress()

    def test_they_see_the_name_they_gave_that_look(self):
        self.named(self.corpse, self.friend, "Ghost")

    def test_and_nothing_was_pointed_anywhere(self):
        entry = self.friend.recognition_memory[self.masked]
        self.assertIsNone(entry.get("witnessed_from"))


# ----------------------------------------------------------------------
# A mask comes off, by either door
# ----------------------------------------------------------------------

class _AMaskComesOff:
    """The same questions for either door. Not a test case by itself:
    each door below mixes it in ahead of :class:`_AtTheBody` and says
    how it takes the mask off (``strip``)."""

    MASKED = True

    def setUp(self):
        super().setUp()
        self.named(self.corpse, self.fence, "Ghost")     # before
        self.nameless(self.corpse, self.friend)
        self.said = self.strip()

    def test_the_mask_is_off(self):
        self.assertEqual(self.corpse.get_worn_items(), [])
        self.assertEqual(get_apparent_uid(self.corpse), self.bare)
        self.assertIs(self.mask.location, self.hand)

    def test_somebody_who_knew_only_the_mask_still_knows_the_body(self):
        self.named(self.corpse, self.fence, "Ghost")

    def test_their_memory_says_what_they_watched_it_come_from(self):
        entry = self.fence.recognition_memory[self.bare]
        self.assertEqual(entry["witnessed_from"], self.masked)

    def test_somebody_who_knew_the_face_sees_the_face(self):
        """As it always was: the face is there to be known."""
        self.named(self.corpse, self.friend, "Jorge")
        self.named(self.corpse, self.hand, "Jorge")

    def test_somebody_who_was_not_there_does_not(self):
        """The control: they knew the mask, and the mask is gone."""
        self.nameless(self.corpse, self.absent_fence)
        self.assertNotIn(self.bare, self.absent_fence.recognition_memory)

    def test_a_stranger_watching_learns_nothing(self):
        self.nameless(self.corpse, self.stranger)
        self.assertEqual(dict(self.stranger.recognition_memory), {})


class TestUndressingACorpse(_AMaskComesOff, _AtTheBody):
    def strip(self):
        return self.undress()


class TestTakingTheMaskFromACorpse(_AMaskComesOff, _AtTheBody):
    def strip(self):
        return self.take()


class TestTheRoomsLineComesAfter(_AtTheBody):
    """`get <mask> from <corpse>` names the corpse to each reader in
    its own line. The line goes out once memories are settled, so it
    says what the reader will go on seeing."""

    MASKED = True

    def test_the_fence_is_named_the_body_in_the_line(self):
        seen = []

        def record(*args, **kwargs):
            seen.append(self.shown(self.corpse, self.fence))

        with mock.patch("commands.CmdInventory.msg_room_identity",
                        side_effect=record):
            self.take()
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0].endswith("(Ghost)"), seen)


# ----------------------------------------------------------------------
# A head on its own
# ----------------------------------------------------------------------

class TestAMaskGoesOnAHead(_AtTheBody):
    def setUp(self):
        super().setUp()
        self.mask.move_to(self.hand, quiet=True)
        self.head = spawn_severed_part_from_corpse(self.corpse, "head")
        self.assertIsNotNone(self.head)
        self.named(self.head, self.friend, "Jorge")      # before

    def check(self):
        self.assertEqual(self.head.get_worn_items(), [self.mask])
        self.named(self.head, self.hand, "Jorge")
        self.named(self.head, self.friend, "Jorge")
        self.nameless(self.head, self.absent)
        self.nameless(self.head, self.stranger)

    def test_on_the_floor(self):
        self.dress("head")
        self.check()

    def test_in_somebodys_hand(self):
        """The watchers are the people in the room the holder is in."""
        self.head.move_to(self.hand, quiet=True)
        self.assertIs(_room_holding(self.head), self.room1)
        self.dress("head")
        self.check()


class _AMaskComesOffAHead:
    """As :class:`_AMaskComesOff`, for a head cut from a masked body."""

    MASKED = True

    def setUp(self):
        super().setUp()
        self.head = spawn_severed_part_from_corpse(self.corpse, "head")
        self.assertIsNotNone(self.head)
        self.assertEqual(self.head.get_worn_items(), [self.mask])
        self.named(self.head, self.fence, "Ghost")       # before
        self.strip()

    def test_the_mask_is_off(self):
        self.assertEqual(self.head.get_worn_items(), [])
        self.assertIs(self.mask.location, self.hand)

    def test_somebody_who_knew_only_the_mask_still_knows_the_head(self):
        self.named(self.head, self.fence, "Ghost")

    def test_somebody_who_was_not_there_does_not(self):
        self.nameless(self.head, self.absent_fence)


class TestUndressingAHead(_AMaskComesOffAHead, _AtTheBody):
    def strip(self):
        return self.undress("head")


class TestTakingTheMaskFromAHead(_AMaskComesOffAHead, _AtTheBody):
    def strip(self):
        return self.take("head")


# ----------------------------------------------------------------------
# Who did not watch, and what they could not have known
# ----------------------------------------------------------------------

class TestSomebodyWhoCannotSee(_AtTheBody):
    def test_they_did_not_watch(self):
        blind = self.friend
        with mock.patch("world.perception.can_see",
                        side_effect=lambda who: who is not blind):
            self.dress()
        self.assertNotIn(self.masked, blind.recognition_memory)
        self.nameless(self.corpse, blind)
        # ... and the one who could see did.
        self.named(self.corpse, self.hand, "Jorge")


class TestABodyWithoutItsHead(_AtTheBody):
    """Nobody knows a headless body at a glance, so nobody watching a
    mask go onto one learns the masked look as anybody's. Their memory
    of the FACE must not be what decides."""

    def setUp(self):
        super().setUp()
        self.head = spawn_severed_part_from_corpse(self.corpse, "head")
        self.assertTrue(self.corpse._is_headless())
        self.nameless(self.corpse, self.friend)
        self.dress()

    def test_the_look_changed(self):
        """So what follows is not passing because nothing happened."""
        self.assertEqual(get_apparent_uid(self.corpse), self.masked)

    def test_nobody_was_given_the_masked_look(self):
        self.assertNotIn(self.masked, self.friend.recognition_memory)
        self.assertNotIn(self.masked, self.hand.recognition_memory)


class _RollsAreCounted:
    """A body a day or more dead names somebody only to a viewer who
    works out whose it is, on a roll made once. These tests decide
    what that roll comes up and keep count of who made it."""

    def age_the_body(self):
        self.corpse.db.creation_time = time.time() - TWO_DAYS
        self.assertEqual(self.corpse.get_decay_stage(), "moderate")

    def rolling(self, value):
        """Everybody who rolls gets *value*; ``self.rolled`` says who."""
        self.rolled = []

        def roll(who, stat, default=1):
            self.rolled.append(who)
            return value

        return mock.patch("world.combat.dice.roll_stat", side_effect=roll)


class TestAMaskGoesOnABodyTooFarGone(_RollsAreCounted, _AtTheBody):
    def setUp(self):
        super().setUp()
        self.age_the_body()

    def test_somebody_who_had_worked_it_out_keeps_the_name(self):
        with self.rolling(6):
            self.named(self.corpse, self.friend, "Jorge")
        with self.rolling(1):               # a new roll would fail
            self.dress()
            self.named(self.corpse, self.friend, "Jorge")
        self.assertNotIn(self.friend, self.rolled)

    def test_somebody_who_had_not_looked_is_asked_as_a_look_asks(self):
        """Watching is looking: their one roll, made as the mask goes
        on. Whoever puts it on is asked the same way."""
        with self.rolling(6):
            self.dress()
            self.named(self.corpse, self.friend, "Jorge")
            self.named(self.corpse, self.hand, "Jorge")
        self.assertEqual(self.rolled.count(self.friend), 1)
        self.assertEqual(self.rolled.count(self.hand), 1)

    def test_somebody_who_cannot_work_it_out_is_given_nothing(self):
        with self.rolling(1):
            self.dress()
            self.nameless(self.corpse, self.friend)
            self.nameless(self.corpse, self.hand)
        self.assertNotIn(self.masked, self.friend.recognition_memory)
        self.assertNotIn(self.masked, self.hand.recognition_memory)
        # ... and that was their roll: looking again made no other.
        self.assertEqual(self.rolled.count(self.friend), 1)
        self.assertEqual(self.rolled.count(self.hand), 1)

    def test_the_door_beneath_the_command_asks_too(self):
        """`_dress_corpse` on its own names nobody to anybody on the
        way, as `get ... from` does not before it moves the item. The
        rule is asked there all the same."""
        self.mask.move_to(self.hand, quiet=True)
        with self.rolling(6):
            ok, why = CmdDress()._dress_corpse(self.corpse, self.mask)
            self.assertTrue(ok, why)
            self.named(self.corpse, self.friend, "Jorge")
        self.assertEqual(self.rolled.count(self.friend), 1)


class TestLiftingAWalletAsksNobody(_RollsAreCounted, _AtTheBody):
    """A thing that is no part of a disguise changes no look, so nobody
    in the room is asked who the body is, and nobody's one roll is
    spent on it."""

    def setUp(self):
        super().setUp()
        self.age_the_body()
        self.wallet = create_object(
            "typeclasses.items.Item", key="wallet", location=self.corpse)

    def test_the_setup_can_roll(self):
        """The control: a mask going on asks the friend."""
        self.mask.move_to(self.hand, quiet=True)
        with self.rolling(6):
            ok, why = CmdDress()._dress_corpse(self.corpse, self.mask)
            self.assertTrue(ok, why)
        self.assertIn(self.friend, self.rolled)

    def test_taking_the_wallet_does_not(self):
        with self.rolling(6):
            self.call(CmdGet(), "wallet from corpse", caller=self.hand)
        self.assertIs(self.wallet.location, self.hand)
        self.assertNotIn(self.friend, self.rolled)


class TestWithNothingCarriedTheNextLookRolls(_RollsAreCounted, _AtTheBody):
    """The control for what follows. The roll is filed under the look,
    and taking a worn mask off ends the death-time look: the look that
    arrives is an empty slot."""

    MASKED = True

    def test_it_does(self):
        self.age_the_body()
        with self.rolling(6):
            self.named(self.corpse, self.fence, "Ghost")
        memory = dict(self.fence.recognition_memory)
        memory[self.bare] = {"assigned_name": "Ghost"}
        self.fence.recognition_memory = memory
        self.mask.move_to(self.room2, quiet=True)   # no door, no watcher
        with self.rolling(1):
            self.nameless(self.corpse, self.fence)
        self.assertEqual(self.rolled.count(self.fence), 1)


class _AMaskComesOffABodyTooFarGone(_RollsAreCounted):
    """Either door, the same answers: mixed in ahead of
    :class:`_AtTheBody` by each door below."""

    MASKED = True

    def setUp(self):
        super().setUp()
        self.age_the_body()

    def test_somebody_who_had_worked_it_out_keeps_the_name(self):
        """And does not roll again about a body they never took their
        eyes off."""
        with self.rolling(6):
            self.named(self.corpse, self.fence, "Ghost")
        with self.rolling(1):               # a new roll would fail
            self.strip()
            self.assertEqual(get_apparent_uid(self.corpse), self.bare)
            self.named(self.corpse, self.fence, "Ghost")
        self.assertNotIn(self.fence, self.rolled)

    def test_somebody_who_had_not_looked_is_asked_as_a_look_asks(self):
        with self.rolling(6):
            self.strip()
            self.named(self.corpse, self.fence, "Ghost")
        self.assertEqual(self.rolled.count(self.fence), 1)

    def test_somebody_who_cannot_work_it_out_is_given_nothing(self):
        with self.rolling(1):
            self.strip()
            self.nameless(self.corpse, self.fence)
        self.assertNotIn(self.bare, self.fence.recognition_memory)
        # They were asked, and that was their roll.
        self.assertEqual(self.rolled.count(self.fence), 1)


class TestUndressingABodyTooFarGone(
        _AMaskComesOffABodyTooFarGone, _AtTheBody):
    def strip(self):
        return self.undress()


class TestTakingTheMaskFromABodyTooFarGone(
        _AMaskComesOffABodyTooFarGone, _AtTheBody):
    def strip(self):
        return self.take()


# ----------------------------------------------------------------------
# The pieces
# ----------------------------------------------------------------------

class TestCarryingARoll(_AtTheBody):
    def setUp(self):
        super().setUp()
        self.key_old = (self.fence.dbref, "old-look")
        self.key_new = (self.fence.dbref, "new-look")

    def carry(self):
        return carry_forensic_roll(
            self.fence, self.corpse, "old-look", "new-look")

    def test_a_roll_made_is_filed_under_the_new_look_too(self):
        self.corpse.db.forensic_recognition_cache = {self.key_old: 5}
        self.assertTrue(self.carry())
        cache = self.corpse.db.forensic_recognition_cache
        self.assertEqual(cache[self.key_new], 5)
        self.assertEqual(cache[self.key_old], 5)

    def test_a_roll_already_there_is_left_alone(self):
        self.corpse.db.forensic_recognition_cache = {
            self.key_old: 5, self.key_new: 2}
        self.assertFalse(self.carry())
        self.assertEqual(
            self.corpse.db.forensic_recognition_cache[self.key_new], 2)

    def test_nothing_is_made_up_for_somebody_who_never_rolled(self):
        self.assertFalse(self.carry())
        self.assertFalse(self.corpse.db.forensic_recognition_cache)

    def test_the_same_look_is_nothing_to_carry(self):
        self.corpse.db.forensic_recognition_cache = {self.key_old: 5}
        self.assertFalse(carry_forensic_roll(
            self.fence, self.corpse, "old-look", "old-look"))


class TestWhatIsNotRemains(_AtTheBody):
    def test_a_stand_in_is_left_alone(self):
        """A MagicMock answers to every name, so only its type says it
        is not remains: nothing about it is even read."""
        thing = MagicMock()
        with apply_remains_change(thing) as change:
            pass
        self.assertIsNone(change._old_uid)
        thing.recognised_as.assert_not_called()
        self.assertEqual(change._knew, [])

    def test_a_severed_arm_has_no_look_to_know(self):
        arm = spawn_severed_part_from_corpse(self.corpse, "left_arm")
        self.assertIsNotNone(arm)
        self.assertIsNone(get_apparent_uid(arm))
        with apply_remains_change(arm) as change:
            pass
        self.assertEqual(change._knew, [])

    def test_a_change_that_fails_writes_nothing(self):
        self.mask.move_to(self.hand, quiet=True)
        with self.assertRaises(RuntimeError):
            with apply_remains_change(self.corpse):
                self.mask.move_to(self.corpse, quiet=True)
                self.corpse.mark_worn(self.mask)
                raise RuntimeError("the door broke")
        self.assertNotIn(self.masked, self.friend.recognition_memory)

    def test_nothing_changing_writes_nothing(self):
        with apply_remains_change(self.corpse):
            pass
        self.assertEqual(
            dict(self.friend.recognition_memory),
            {self.bare: {"assigned_name": "Jorge"}})


class TestTheRoomAThingIsIn(_AtTheBody):
    def test_on_the_floor(self):
        self.assertIs(_room_holding(self.corpse), self.room1)

    def test_in_a_hand(self):
        head = spawn_severed_part_from_corpse(self.corpse, "head")
        head.move_to(self.hand, quiet=True)
        self.assertIs(_room_holding(head), self.room1)

    def test_nowhere(self):
        self.assertIsNone(_room_holding(SimpleNamespace(location=None)))

    def test_stored_data_that_loops_does_not_hang(self):
        thing = SimpleNamespace()
        thing.location = thing
        self.assertIs(_room_holding(thing), thing)
