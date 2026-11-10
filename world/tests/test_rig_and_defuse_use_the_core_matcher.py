"""`rig` and `defuse` name a charge the way every other command does (#3783).

Both matched the typed text as a substring of the key, so an alias
never worked: `rig dx-15 to out` with a held "HDG DX15 demolition
charge" (alias `dx-15`) said "You must be wielding 'dx-15'", and the
same charge, armed, could not be defused by that name. Twins were a
dead end: "Be more specific" with no ordinal to be more specific with.

They now hand their own pool to `Character.search`: the held items for
`rig`; the explosives already in reach, then the live ones, for
`defuse`. The pool is filtered by state before matching, so "2nd
grenade" counts only charges the command could act on.

The player-facing tests act as `char2`, who holds no staff permission.
`attempt_defuse` is patched out: it rolls dice and can detonate, and
what is pinned here is which charge reaches it.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdExplosives import CmdDefuse, CmdRig
from world.combat.constants import (
    MSG_RIG_OBJECT_NOT_FOUND,
    NDB_COUNTDOWN_REMAINING,
    NDB_PROXIMITY_UNIVERSAL,
)

DX15_KEY = "HDG DX15 demolition charge"
DX15_ALIAS = "dx-15"


class _Explosives(EvenniaCommandTest):

    def charge(self, key, *, location, aliases=()):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=location, aliases=list(aliases))
        obj.db.is_explosive = True
        return obj

    def as_player(self, cmd, args: str) -> str:
        return self.call(cmd, args, caller=self.char2) or ""


class RigNamesTheChargeInHand(_Explosives):
    """`self.exit` ("out") leads from room1 to room2."""

    def hold(self, *items) -> None:
        self.char2.hands = dict(zip(("right_hand", "left_hand"), items))

    def test_an_alias_that_is_not_part_of_the_key(self):
        dx15 = self.charge(DX15_KEY, location=self.char2, aliases=[DX15_ALIAS])
        self.hold(dx15)
        out = self.as_player(CmdRig(), f"{DX15_ALIAS} to out")
        self.assertNotIn("must be wielding", out)
        self.assertIs(self.exit.db.rigged_grenade, dx15)
        self.assertEqual(dx15.location, self.room1)

    def test_an_ordinal_picks_the_second_of_two_twins(self):
        first = self.charge("frag grenade", location=self.char2)
        second = self.charge("frag grenade", location=self.char2)
        self.hold(first, second)
        self.as_player(CmdRig(), "2nd grenade to out")
        self.assertIs(self.exit.db.rigged_grenade, second)
        self.assertEqual(first.location, self.char2)

    def test_a_fragment_from_inside_a_word_is_refused(self):
        grenade = self.charge("frag grenade", location=self.char2)
        self.hold(grenade)
        out = self.as_player(CmdRig(), "nade to out")
        self.assertIn(MSG_RIG_OBJECT_NOT_FOUND.format(object="nade"), out)
        self.assertIsNone(self.exit.db.rigged_grenade)
        self.assertEqual(grenade.location, self.char2)

    def test_me_is_not_a_held_item(self):
        # "me" sits inside "demolition": the substring loop rigged the
        # charge; a pool-scoped search must not answer with the caller.
        dx15 = self.charge(DX15_KEY, location=self.char2, aliases=[DX15_ALIAS])
        self.hold(dx15)
        out = self.as_player(CmdRig(), "me to out")
        self.assertNotIn("cannot be rigged", out)
        self.assertIsNone(self.exit.db.rigged_grenade)
        self.assertEqual(dx15.location, self.char2)


@patch.object(CmdDefuse, "attempt_defuse")
class DefuseNamesTheArmedCharge(_Explosives):

    def armed(self, key, *, aliases=(), in_reach=False):
        obj = self.charge(key, location=self.room1, aliases=aliases)
        obj.db.pin_pulled = True
        setattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 5)
        if in_reach:
            setattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, [self.char2])
        return obj

    def defused(self, attempt):
        attempt.assert_called_once()
        return attempt.call_args.args[0]

    def test_an_alias_that_is_not_part_of_the_key(self, attempt):
        dx15 = self.armed(DX15_KEY, aliases=[DX15_ALIAS])
        out = self.as_player(CmdDefuse(), DX15_ALIAS)
        self.assertIn(f"You move closer to the {DX15_KEY}", out)
        self.assertIs(self.defused(attempt), dx15)

    def test_an_alias_for_a_charge_already_in_reach(self, attempt):
        dx15 = self.armed(DX15_KEY, aliases=[DX15_ALIAS], in_reach=True)
        out = self.as_player(CmdDefuse(), DX15_ALIAS)
        self.assertNotIn("move closer", out)
        self.assertIs(self.defused(attempt), dx15)

    def test_an_ordinal_counts_only_live_charges(self, attempt):
        # The dud is oldest, so counting it would make the 2nd the first.
        dud = self.charge("frag grenade", location=self.room1)
        first = self.armed("frag grenade")
        second = self.armed("frag grenade")
        self.as_player(CmdDefuse(), "2nd grenade")
        self.assertIs(self.defused(attempt), second)
        self.assertNotIn(self.char2, getattr(first.ndb, NDB_PROXIMITY_UNIVERSAL,
                                             None) or [])
        self.assertIsNone(getattr(dud.ndb, NDB_PROXIMITY_UNIVERSAL, None))

    def test_twins_without_an_ordinal_still_ask(self, attempt):
        self.armed("frag grenade")
        self.armed("frag grenade")
        out = self.as_player(CmdDefuse(), "grenade")
        self.assertIn("Multiple grenades are nearby. Be more specific.", out)
        attempt.assert_not_called()

    def test_an_ordinal_picks_the_second_twin_in_reach(self, attempt):
        self.armed("frag grenade", in_reach=True)
        second = self.armed("frag grenade", in_reach=True)
        self.as_player(CmdDefuse(), "2nd grenade")
        self.assertIs(self.defused(attempt), second)

    def test_twins_in_reach_without_an_ordinal_still_ask(self, attempt):
        self.armed("frag grenade", in_reach=True)
        self.armed("frag grenade", in_reach=True)
        out = self.as_player(CmdDefuse(), "grenade")
        self.assertIn("Multiple grenades are within reach. Be more specific.", out)
        attempt.assert_not_called()

    def test_a_fragment_from_inside_a_word_is_refused(self, attempt):
        self.armed("frag grenade")
        out = self.as_player(CmdDefuse(), "nade")
        self.assertIn("You don't see any armed 'nade' within reach to defuse.",
                      out)
        attempt.assert_not_called()

    def test_a_blank_name_is_refused_before_searching(self, attempt):
        self.armed("frag grenade")
        out = self.as_player(CmdDefuse(), "   ")
        self.assertIn("Defuse what?", out)
        attempt.assert_not_called()
