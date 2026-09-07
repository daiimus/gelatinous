"""You cannot give away the coat you have on (#2516).

`CmdGive` validated that it had successfully picked an item up by
**sniffing the returned status message for the substring `"wield"`**:

```python
wield_result = caller.wield_item(item, caller_free_hand)
if "wield" not in wield_result.lower():
```

`wield_item` returns a player-facing sentence, and **two of its refusals
contain that word**:

* *"You can't wield something you're wearing. Remove it first."*
* *"You're already wielding X in your left hand."*

So the guard passed on precisely the cases it existed to catch. The worn
refusal returns *before* any `held_items` write, so `from_hand` was set
to a slot that was still empty and the transfer ran from it — `give
jacket to bob` while wearing the jacket succeeded.

The fix asks the hands, not the sentence. `Character.is_wielding` is the
ground truth; `wield_item`'s return stays a message for the player,
which is all it was ever good for.

**The same check was in `wrest`**, including in the repair I shipped for
#2489 — I moved that function's restore path onto `wield_item` and left
its success test sniffing a substring. Both call sites are converted
here; there are no others.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


def is_wielding(char, item, hand=None):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree — a module-scope import of a method that does not exist
    yet errors every test and proves nothing."""
    if hasattr(char, "is_wielding"):
        return char.is_wielding(item, hand)
    current = char.hands or {}
    if hand is None:
        return any(held is item for held in current.values())
    return any(held is item for slot, held in current.items()
               if slot.startswith(hand.rstrip("_hand")))


class _GiveCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        # An Item is only WEARABLE with both `coverage` and
        # `worn_desc` (`Item.is_wearable`). Without them `wear_item`
        # refuses, `is_item_worn` stays False, and the whole premise of
        # these tests quietly evaporates.
        self.coat = create_object("typeclasses.items.Item", key="a coat",
                                  location=self.char1)
        self.coat.coverage = ["chest", "back"]
        self.coat.worn_desc = "a coat"
        assert self.coat.is_wearable(), "fixture is not wearable"

    def held(self, char):
        return dict(char.held_items or {})


class TestTheMessageIsNotTheAnswer(_GiveCase):
    """Pinning the trap itself: both refusals contain "wield"."""

    def test_the_worn_refusal_contains_the_word(self):
        self.assertTrue(self.char1.wear_item(self.coat)[0])
        result = self.char1.wield_item(self.coat, "right_hand")
        self.assertIn("wield", result.lower())

    def test_but_nothing_was_wielded(self):
        self.assertTrue(self.char1.wear_item(self.coat)[0])
        self.char1.wield_item(self.coat, "right_hand")
        self.assertFalse(is_wielding(self.char1, self.coat))

    def test_the_already_wielding_refusal_contains_it_too(self):
        self.char1.wield_item(self.coat, "right_hand")
        result = self.char1.wield_item(self.coat, "left_hand")
        self.assertIn("wield", result.lower())
        self.assertFalse(is_wielding(self.char1, self.coat, "left_hand"))


class TestIsWieldingIsGroundTruth(_GiveCase):
    def test_it_sees_a_real_wield(self):
        self.char1.wield_item(self.coat, "right_hand")
        self.assertTrue(is_wielding(self.char1, self.coat, "right_hand"))

    def test_it_answers_for_any_hand(self):
        self.char1.wield_item(self.coat, "left_hand")
        self.assertTrue(is_wielding(self.char1, self.coat))

    def test_it_is_false_for_the_wrong_hand(self):
        self.char1.wield_item(self.coat, "left_hand")
        self.assertFalse(is_wielding(self.char1, self.coat, "right_hand"))

    def test_it_is_false_for_an_item_in_inventory(self):
        self.assertFalse(is_wielding(self.char1, self.coat))

    def test_it_accepts_a_shorthand_hand(self):
        self.char1.wield_item(self.coat, "right_hand")
        self.assertTrue(is_wielding(self.char1, self.coat, "right"))


class TestGivingAWornGarmentIsRefused(_GiveCase):
    def give(self):
        """Runs the real command. Deliberately NOT wrapped in a bare
        `except` — my first version swallowed every failure, so the
        command never ran, the coat naturally stayed put, and the test
        passed against the unfixed tree while proving nothing."""
        from commands.CmdInventory import CmdGive
        cmd = CmdGive()
        cmd.caller = self.char1
        cmd.obj = self.char1
        cmd.session = None
        cmd.args = f"{self.coat.key} to {self.char2.key}"
        cmd.raw_string = f"give {cmd.args}"
        cmd.cmdstring = "give"
        cmd.parse()          # func() reads item_name/target_name from here
        said = []
        self.char1.msg = lambda *a, **k: said.append(str(a[0] if a else ""))
        cmd.func()
        return " ".join(said)

    def test_the_command_actually_runs(self):
        """Guards the three below: if `give` silently does nothing they
        all pass for the wrong reason."""
        self.assertTrue(self.char1.wear_item(self.coat)[0])
        self.assertTrue(self.give().strip(), "give said nothing at all")

    def test_the_coat_does_not_change_hands(self):
        self.assertTrue(self.char1.wear_item(self.coat)[0])
        self.give()
        self.assertNotIn(self.coat, self.held(self.char2).values())

    def test_it_stays_on_the_wearer(self):
        self.assertTrue(self.char1.wear_item(self.coat)[0])
        self.give()
        self.assertEqual(self.coat.location, self.char1)

    def test_an_unworn_item_still_gives(self):
        """The fix must refuse the worn case, not every case."""
        self.give()
        self.assertEqual(self.coat.location, self.char2)


class TestNoSubstringCheckSurvives(EvenniaTest):
    """The bug is a check that looks like a check. A future edit
    reintroducing one is the regression."""

    def _source(self, relpath):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / relpath).read_text(errors="ignore")

    def test_give_and_wrest_both_ask_the_hands(self):
        body = self._source("commands/CmdInventory.py")
        self.assertNotIn('"wield" not in', body)
        self.assertEqual(body.count("is_wielding("), 2)

    def test_wield_item_still_returns_a_message_for_the_player(self):
        """It is not being turned into a boolean — the sentence is what
        the player reads."""
        body = self._source("typeclasses/characters.py")
        self.assertIn("You can't wield something you're wearing", body)
