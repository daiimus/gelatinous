"""`hide <object>` is a drop, and owes what a drop owes (#2561).

`CmdHide._stash` resolved anything in `caller.contents` and moved it out
with a bare `move_to`:

```python
item = caller.search(phrase, location=caller, quiet=True)
item.move_to(caller.location, quiet=True)
item.db.hidden = True
```

`caller.contents` is not "your loose gear" — it holds worn clothing,
held weapons and integrated cyberware alike. So a one-word command
walked around all four guards `drop` spends thirty lines applying:

* **worn** — `hide jacket` took the jacket off you and stashed it, so
  one word did the work of `remove` plus `drop` with neither refusal;
* **integrated** — cyberware bolted to the skeleton could be posted out
  of your own arm;
* **`at_drop`** — single-use issue kit never perished, so `hide` was a
  second unbounded free-jumpsuit loop of exactly the shape #2456 closed
  on `drop`;
* **gravity** — an item stashed in a sky room stayed in mid-air instead
  of falling to the ground room.

**The issue also claimed a fourth PR-H2 hand-slot desync. That part is
stale**, and measuring it is what showed it: the hand tests below pass
against the UNFIXED tree. `Character.at_object_leave` calls
`release_slots`, so anything leaving the body already gives up its hand
and clothing slots — a later fix that reaches this path because
`move_to(..., quiet=True)` suppresses messages, not hooks. The slots
were never left dangling. They are kept here as regression pins, not as
evidence of a defect.

Fixed by giving the two doors one implementation: `release_to_ground`
in `commands/CmdInventory.py`, which `CmdDrop` now calls as well, so
they cannot drift apart again. Prose stays with each caller — you
*drop* a shiv, you *stash* it — which is the same split `drop_to_room`
already makes for the physics.

The tests drive the real `hide` command rather than the helper: a
module-scope import of a function that does not exist in the unfixed
tree is a loader error, not evidence.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdStealth import CmdHide


class _StashCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1

    def wearable(self, key="a jacket"):
        # An Item is only WEARABLE with both `coverage` and `worn_desc`
        # (`Item.is_wearable`); without them `wear_item` refuses and the
        # premise of the worn tests quietly evaporates.
        item = create_object("typeclasses.items.Item", key=key,
                             location=self.char1)
        item.coverage = ["chest", "back"]
        item.worn_desc = key
        assert item.is_wearable(), "fixture is not wearable"
        return item

    def loose(self, key="a shiv"):
        return create_object("typeclasses.items.Item", key=key,
                             location=self.char1)

    def stash(self, phrase):
        return self.call(CmdHide(), phrase)


class TestYouCannotStashWhatYouAreWearing(_StashCase):
    def test_the_jacket_stays_on_your_body(self):
        jacket = self.wearable()
        self.assertTrue(self.char1.wear_item(jacket)[0])
        self.stash("jacket")
        self.assertIs(jacket.location, self.char1)

    def test_it_is_still_worn(self):
        jacket = self.wearable()
        self.assertTrue(self.char1.wear_item(jacket)[0])
        self.stash("jacket")
        self.assertTrue(self.char1.is_item_worn(jacket))

    def test_it_is_not_marked_hidden(self):
        """The old path set `db.hidden` unconditionally, so a garment you
        were still wearing was also flagged as a findable stash."""
        jacket = self.wearable()
        self.assertTrue(self.char1.wear_item(jacket)[0])
        self.stash("jacket")
        self.assertFalse(jacket.db.hidden)

    def test_the_player_is_told_why(self):
        jacket = self.wearable()
        self.assertTrue(self.char1.wear_item(jacket)[0])
        self.assertIn("wearing", self.stash("jacket"))


class TestStashingFromTheHandReleasesTheHand(_StashCase):
    """REGRESSION PINS, not evidence — these already held before the fix
    (see the module docstring). `release_slots` off `at_object_leave`
    covers the slots; routing through the shared helper must not lose
    that."""

    def _wielded(self):
        shiv = self.loose()
        self.char1.wield_item(shiv, "right_hand")
        # `wield_item` returns a player-facing SENTENCE — truthy even
        # when it refused (#2516). Ask the hands.
        self.assertTrue(self.char1.is_wielding(shiv), "fixture never wielded")
        return shiv

    def test_the_hand_no_longer_holds_it(self):
        shiv = self._wielded()
        self.stash("shiv")
        self.assertFalse(self.char1.is_wielding(shiv))

    def test_the_backing_store_agrees(self):
        """`hands` is a DERIVED view — the desync this family keeps
        producing is a hand slot that reads clear while `held_items`
        still points at the item."""
        shiv = self._wielded()
        self.stash("shiv")
        self.assertNotIn(shiv, dict(self.char1.held_items or {}).values())

    def test_it_actually_reached_the_floor(self):
        shiv = self._wielded()
        self.stash("shiv")
        self.assertIs(shiv.location, self.room1)


class TestIntegratedCyberwareStaysInTheArm(_StashCase):
    def test_it_does_not_move(self):
        blade = self.loose("a wrist blade")
        blade.db.integrated = True
        self.stash("wrist blade")
        self.assertIs(blade.location, self.char1)

    def test_the_refusal_names_the_body(self):
        blade = self.loose("a wrist blade")
        blade.db.integrated = True
        self.assertIn("body", self.stash("wrist blade"))


class TestSingleUseKitPerishesOnTheWayDown(_StashCase):
    """`_perish` exists so the colony never accumulates a pile of free
    Thawn-Harrison jumpsuits. `drop` got its `at_drop` call back in
    #2456; `hide` was the same loop through a different door."""

    def test_it_does_not_survive_being_stashed(self):
        suit = self.loose("a jumpsuit")
        suit.db.single_use = True
        self.stash("jumpsuit")
        self.assertFalse(suit.pk, "single-use kit survived a stash")

    def test_the_player_is_told_it_tore(self):
        suit = self.loose("a jumpsuit")
        suit.db.single_use = True
        self.assertIn("tears", self.stash("jumpsuit"))

    def test_an_ordinary_item_is_untouched_by_the_hook(self):
        shiv = self.loose()
        self.stash("shiv")
        self.assertTrue(shiv.pk)


class TestAnOrdinaryStashStillWorks(_StashCase):
    """The guards must not cost the command its actual job."""

    def test_a_loose_item_reaches_the_room(self):
        shiv = self.loose()
        self.stash("shiv")
        self.assertIs(shiv.location, self.room1)

    def test_it_is_marked_hidden(self):
        shiv = self.loose()
        self.stash("shiv")
        self.assertTrue(shiv.db.hidden)

    def test_it_carries_a_difficulty_for_searchers(self):
        shiv = self.loose()
        self.stash("shiv")
        self.assertTrue(shiv.db.stash_roll)

    def test_carrying_nothing_by_that_name_still_says_so(self):
        self.assertIn("aren't carrying", self.stash("a hovercar"))
