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
visible "kitchen knife"; and ordinals counted the stash, so `get 1st
knife` reached for it. Both told the searcher a stash was there.

These drive the real commands, not the helper.
"""
from evennia import create_object
from evennia.commands.default.general import CmdLook
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdInventory import CmdGet
from world.stealth import ALERT, set_awareness


class _Stash(EvenniaCommandTest):

    def thing(self, key, *, hidden=False, location=None, aliases=None):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=location or self.room1,
                            aliases=aliases or [])
        if hidden:
            obj.db.hidden = True
            obj.db.stash_roll = 30
        return obj


class TheStashItself(_Stash):

    def test_look_does_not_describe_it(self):
        self.thing("battered tin", hidden=True)
        out = self.call(CmdLook(), "battered tin") or ""
        self.assertNotIn("battered tin", out.replace("'battered tin'", ""))
        self.assertIn("Could not find", out)

    def test_get_from_it_neither_finds_nor_empties_it(self):
        tin = self.thing("battered tin", hidden=True)
        coin = self.thing("brass coin", location=tin)
        out = self.call(CmdGet(), "coin from tin") or ""
        self.assertEqual(coin.location, tin, "the stash was emptied")
        self.assertIn("don't see", out)

    def test_control_once_found_both_work(self):
        tin = self.thing("battered tin")          # not hidden: the control
        coin = self.thing("brass coin", location=tin)
        self.assertIn("battered tin", self.call(CmdLook(), "battered tin") or "")
        self.call(CmdGet(), "coin from tin")
        self.assertNotEqual(coin.location, tin)


class TheStashCastsNoShadow(_Stash):

    def test_a_hidden_exact_match_does_not_hide_a_visible_partial_one(self):
        # Evennia tries EXACT before partial. With the stash in the pool,
        # "knife" matched it exactly, the partial pass never ran, and the
        # searcher learned something called exactly that was here.
        self.thing("knife", hidden=True)
        visible = self.thing("kitchen knife")
        self.call(CmdGet(), "knife")
        self.assertEqual(visible.location, self.char1)

    def test_ordinals_count_only_what_you_can_see(self):
        stash = self.thing("knife", hidden=True)   # oldest: first by id
        first = self.thing("knife")
        second = self.thing("knife")
        self.call(CmdGet(), "1st knife")
        self.assertEqual(first.location, self.char1)
        self.assertEqual(stash.location, self.room1)
        self.assertEqual(second.location, self.room1)


class AHiddenPerson(_Stash):
    """Same gate, same answer. `get <name>` passes its own candidates,
    which skipped the identity pipeline's gate; the hand filter it had
    was the only thing keeping a hidden person out (#3637 review)."""

    def setUp(self):
        super().setUp()
        self.char2.db.hidden = True

    def test_get_does_not_confirm_them(self):
        out = self.call(CmdGet(), self.char2.key) or ""
        self.assertIn("don't see", out)
        self.assertNotIn("can't pick up", out)

    def test_an_alert_looker_still_places_them(self):
        # Control: awareness, not the flag alone, is the gate.
        set_awareness(self.char1, self.char2, ALERT)
        out = self.call(CmdGet(), self.char2.key) or ""
        self.assertIn("can't pick up", out)


class StaffTooling(_Stash):

    def test_a_dbref_still_resolves(self):
        tin = self.thing("battered tin", hidden=True)
        self.assertEqual(list(self.char1.search(f"#{tin.id}", quiet=True)), [tin])


class TheDoorsThatWalkedAroundIt(_Stash):
    """Two resolvers matched names over room contents by hand and never
    reached the search pool. They take the same gate now (#3637)."""

    def live_charge(self, *, hidden):
        charge = self.thing("frag grenade", hidden=hidden)
        charge.db.is_explosive = True
        charge.db.pin_pulled = True
        return charge

    def test_defuse_does_not_find_a_stashed_charge(self):
        from commands.CmdExplosives import CmdDefuse
        self.live_charge(hidden=True)
        out = self.call(CmdDefuse(), "grenade") or ""
        self.assertIn("don't see any armed", out)
        self.assertNotIn("frag grenade", out.replace("'grenade'", ""))

    def test_control_defuse_finds_a_charge_in_plain_sight(self):
        from unittest import mock
        from commands.CmdExplosives import CmdDefuse
        self.live_charge(hidden=False)
        with mock.patch.object(CmdDefuse, "attempt_defuse"):
            out = self.call(CmdDefuse(), "grenade") or ""
        self.assertIn("You move closer to the frag grenade", out)

    def _papers_in_char2s_hand(self):
        papers = self.thing("identity papers", location=self.char2)
        papers.db.depicts_uid = "uid-under-test"
        self.char2.hands = {"right_hand": papers}
        return papers

    def test_remember_cannot_reach_a_hidden_persons_hand(self):
        from world.search import held_by_others
        self._papers_in_char2s_hand()
        self.char2.db.hidden = True
        self.assertEqual(held_by_others(self.char1, "papers"), [])

    def test_control_an_alert_looker_sees_what_they_hold(self):
        from world.search import held_by_others
        papers = self._papers_in_char2s_hand()
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, ALERT)
        self.assertEqual(held_by_others(self.char1, "papers"), [papers])
