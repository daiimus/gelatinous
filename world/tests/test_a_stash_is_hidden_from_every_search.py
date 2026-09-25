"""What you cannot perceive is not in any search's pool (#3637).

`hide <object>` stashes an item (`db.hidden`, `db.stash_roll`) and only
the active `search` should turn it up. `get <x>` and `put` filtered the
flag by hand; every other command that named the item found it:
`look <x>` described a stashed pack down to its contents, and
`get <x> from <pack>` emptied it with no roll.

The gate is `Character.get_search_candidates`: the presence gate
(`world.perception.can_perceive`) applied to the pool BEFORE Evennia
matches, for people and things alike. The first cut filtered the
RESULTS instead, and review showed why that is wrong: a hidden exact
match stopped Evennia's partial pass, so a stashed "knife" hid the
visible "kitchen knife"; ordinals counted the stash; and with `get`'s
hand filter gone, `get <hidden person>` answered "You can't pick up
<sdesc>". Tests marked (first cut) guard those; master's own filter in
`get` already got them right.

The player-facing tests search as `char2`, who holds no staff
permission (`char1` is a Developer in EvenniaTest, which changes the
dbref and key-match branches). They drive the real commands where one
exists; `held_by_others` is driven directly as the resolver `remember
<papers>` falls back on.
"""
from evennia import create_object
from evennia.commands.default.general import CmdLook
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdInventory import CmdGet
from world.stealth import ALERT, set_awareness

#: `typeclasses.items.Item`'s default desc: proof `look` described it.
ITEM_DESC = "It's a thing. Heavy enough to hurt if used wrong."


class _Stash(EvenniaCommandTest):

    def thing(self, key, *, hidden=False, location=None, aliases=None):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=location or self.room1,
                            aliases=aliases or [])
        if hidden:
            obj.db.hidden = True
            obj.db.stash_roll = 30
        return obj

    def as_player(self, cmd, args):
        return self.call(cmd, args, caller=self.char2) or ""


class TheStashItself(_Stash):

    def test_look_does_not_describe_it(self):
        self.thing("battered tin", hidden=True)
        out = self.as_player(CmdLook(), "battered tin")
        self.assertNotIn(ITEM_DESC, out)
        self.assertIn("Could not find", out)

    def test_control_look_describes_it_in_plain_sight(self):
        self.thing("battered tin")
        out = self.as_player(CmdLook(), "battered tin")
        self.assertIn(ITEM_DESC, out)
        self.assertNotIn("Could not find", out)

    def test_get_from_it_neither_finds_nor_empties_it(self):
        tin = self.thing("battered tin", hidden=True)
        coin = self.thing("brass coin", location=tin)
        out = self.as_player(CmdGet(), "coin from tin")
        self.assertEqual(coin.location, tin, "the stash was emptied")
        self.assertIn("don't see", out)

    def test_control_get_from_it_in_plain_sight(self):
        tin = self.thing("battered tin")
        coin = self.thing("brass coin", location=tin)
        self.as_player(CmdGet(), "coin from tin")
        self.assertEqual(coin.location, self.char2)

    def test_a_location_pool_is_gated_too(self):
        # `jump on <explosive>` and friends search with location=room.
        self.thing("battered tin", hidden=True)
        self.assertFalse(self.char2.search("battered tin", location=self.room1,
                                           quiet=True))


class TheStashCastsNoShadow(_Stash):
    """(first cut) Evennia matches exact before partial, and counts
    ordinals over the pool it matched."""

    def test_a_hidden_exact_match_does_not_hide_a_visible_partial_one(self):
        self.thing("knife", hidden=True)
        visible = self.thing("kitchen knife")
        self.as_player(CmdGet(), "knife")
        self.assertEqual(visible.location, self.char2)

    def test_ordinals_count_only_what_you_can_see(self):
        # "2nd", not "1st": `get` takes the first of a multimatch anyway,
        # so only the second place shows what was counted. Counting the
        # stash would make the 2nd knife `first`.
        stash = self.thing("knife", hidden=True)   # oldest: first by id
        first = self.thing("knife")
        second = self.thing("knife")
        self.as_player(CmdGet(), "2nd knife")
        self.assertEqual(second.location, self.char2)
        self.assertEqual(first.location, self.room1)
        self.assertEqual(stash.location, self.room1)


class AHiddenPerson(_Stash):
    """Same gate, same answer as a stash: awareness decides."""

    def setUp(self):
        super().setUp()
        self.char1.db.hidden = True           # char2 is Unaware of char1

    def test_get_from_them_does_not_name_them(self):
        # Master's real leak: `get <x> from <hidden person>` had no filter
        # and answered "You would have to take that off <name>".
        self.thing("brass coin", location=self.char1)
        out = self.as_player(CmdGet(), f"coin from {self.char1.key}")
        self.assertIn("don't see", out)
        self.assertNotIn("take that off", out)

    def test_get_does_not_confirm_them(self):
        # (first cut) "You can't pick up <sdesc>".
        out = self.as_player(CmdGet(), self.char1.key)
        self.assertIn("don't see", out)
        self.assertNotIn("can't pick up", out)

    def test_control_an_alert_looker_still_places_them(self):
        set_awareness(self.char2, self.char1, ALERT)
        out = self.as_player(CmdGet(), self.char1.key)
        self.assertIn("can't pick up", out)

    def test_a_hidden_searcher_still_finds_themself(self):
        # `obj is self`: can_perceive(self, self) is False while hidden.
        found = self.char1.search(self.char1.key, candidates=[self.char1],
                                  quiet=True)
        self.assertEqual(list(found), [self.char1])


class TheDoorsThatWalkedAroundIt(_Stash):
    """Two resolvers matched names over room contents by hand and never
    reached the search pool. They take the same gate now (#3637)."""

    def live_charge(self, *, hidden):
        charge = self.thing("frag grenade", hidden=hidden)
        charge.db.is_explosive = True
        charge.db.pin_pulled = True
        return charge

    # Both answers come from `find_grenade_in_proximity`, before the
    # fixture's missing countdown stops `validate_grenade_for_defuse`, so
    # `attempt_defuse` is never reached and needs no patch.
    def test_defuse_does_not_find_a_stashed_charge(self):
        from commands.CmdExplosives import CmdDefuse
        self.live_charge(hidden=True)
        out = self.as_player(CmdDefuse(), "grenade")
        self.assertIn("don't see any armed", out)
        self.assertNotIn("frag grenade", out)

    def test_control_defuse_finds_a_charge_in_plain_sight(self):
        from commands.CmdExplosives import CmdDefuse
        self.live_charge(hidden=False)
        out = self.as_player(CmdDefuse(), "grenade")
        self.assertIn("You move closer to the frag grenade", out)

    def _papers_in_char1s_hand(self):
        papers = self.thing("identity papers", location=self.char1)
        papers.db.depicts_uid = "uid-under-test"
        self.char1.hands = {"right_hand": papers}
        return papers

    def test_remember_cannot_reach_a_hidden_persons_hand(self):
        from world.search import held_by_others
        self._papers_in_char1s_hand()
        self.char1.db.hidden = True
        self.assertEqual(held_by_others(self.char2, "papers"), [])

    def test_control_an_alert_looker_sees_what_they_hold(self):
        from world.search import held_by_others
        papers = self._papers_in_char1s_hand()
        self.char1.db.hidden = True
        set_awareness(self.char2, self.char1, ALERT)
        self.assertEqual(held_by_others(self.char2, "papers"), [papers])


class Dbrefs(_Stash):
    """A #dbref search has no pool, so the gate does not apply: that is
    staff tooling. A player's '#N' is not a dbref search at all (Evennia
    allows it only with perm(Builder)), so it reaches nothing."""

    def test_staff_reach_a_stash_by_dbref(self):
        tin = self.thing("battered tin", hidden=True)
        self.assertEqual(list(self.char1.search(f"#{tin.id}", quiet=True)), [tin])

    def test_a_player_does_not(self):
        tin = self.thing("battered tin", hidden=True)
        self.assertFalse(self.char2.search(f"#{tin.id}", quiet=True))


class AimingKeepsAChosenPool(_Stash):
    """Aiming widens the DEFAULT search to room + aimed room. It used to
    swap a pool the command chose for that too (#3637 review), so while
    aiming, `get x from <tin in hand>` lost the tin, a held detonator
    could not be found, and `hide knife` could lift a knife off the aimed
    room's floor."""

    def setUp(self):
        super().setUp()
        self.north = create_object("typeclasses.rooms.Room", key="North Room")
        create_object("typeclasses.exits.Exit", key="north", aliases=["n"],
                      location=self.room1, destination=self.north)
        self.char2.ndb.aiming_direction = "north"

    def test_get_from_a_container_in_hand_while_aiming(self):
        tin = self.thing("battered tin", location=self.char2)
        coin = self.thing("brass coin", location=tin)
        self.as_player(CmdGet(), "coin from tin")
        self.assertEqual(coin.location, self.char2)

    def test_a_location_pool_is_not_widened_into_the_aimed_room(self):
        self.thing("rusty knife", location=self.north)
        self.assertFalse(self.char2.search("rusty knife", location=self.char2,
                                           quiet=True))

    def test_control_the_default_reach_is_still_widened(self):
        far = self.thing("distant crate", location=self.north)
        self.assertEqual(list(self.char2.search("distant crate", quiet=True)), [far])
