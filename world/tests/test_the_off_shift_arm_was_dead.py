"""The off-shift deflection has two arms, not three (#2606).

`_off_shift_deflection` had a middle arm reached when
`holder == speaker`:

```python
if holder is not None and holder != speaker:
    line = f"I'm off. {holder.key} has the {shift} — they'll be along."
elif holder is not None:
    line = "I'm on in a bit. Come back and I'll serve you."   # dead
else:
    line = f"I'm off, and nobody's got the {shift}. ..."
```

It could never run, and the reason is two lookups with mirror-image
names asking different questions:

* `on_duty_keeper(post)` — who holds the running shift, **wherever they
  are**
* `keeper_on_duty(fixture)` — who holds it **and is standing here**

`speaker` comes from `off_duty_keepers_present`, which returns only
keepers of slots *other* than the current shift. And the whole function
is called under `if not any_keeper_present(self)`, which is
`keeper_on_duty(...) is None`. So if the holder of the running shift
were the person standing here talking, that call would have found them
and this function would never have been entered.

These tests prove the unreachability from the real predicates rather
than asserting the source no longer contains a string — the branch is
gone, so a source check would pass trivially and forever.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.souls.posts import (any_keeper_present, current_shift,
                               keeper_on_duty, off_duty_keepers_present,
                               on_duty_keeper)


class _PostCase(EvenniaTest):
    def counter(self):
        c = create_object("typeclasses.shopkeeper.ShopContainer",
                          key="a counter", location=self.room1)
        return c

    def staff(self, counter, *, on=None, off=None):
        """Put `on` in the running shift and `off` in another one."""
        now = current_shift()
        other = next(s for s in ("day", "swing", "night") if s != now)
        slots = {}
        if on is not None:
            slots[now] = {"keeper": on}
        if off is not None:
            slots[other] = {"keeper": off}
        counter.db.post_slots = slots
        return counter


class TestTheTwoLookupsDiffer(_PostCase):
    """The trap the dead arm fell into."""

    def test_on_duty_keeper_ignores_location(self):
        c = self.staff(self.counter(), on=self.char2)
        self.char2.location = self.room2          # away
        self.assertIs(on_duty_keeper(c), self.char2)

    def test_keeper_on_duty_requires_presence(self):
        c = self.staff(self.counter(), on=self.char2)
        self.char2.location = self.room2
        self.assertIsNone(keeper_on_duty(c))

    def test_and_finds_them_when_they_are_here(self):
        c = self.staff(self.counter(), on=self.char2)
        self.char2.location = self.room1
        self.assertIs(keeper_on_duty(c), self.char2)


class TestTheDeadArmWasUnreachable(_PostCase):
    def test_the_speaker_is_never_the_running_holder(self):
        """`off_duty_keepers_present` only returns non-current slots."""
        c = self.staff(self.counter(), on=self.char2, off=self.char1)
        self.char1.location = self.room1
        self.char2.location = self.room1
        present = off_duty_keepers_present(c)
        self.assertIn(self.char1, present)
        self.assertNotIn(self.char2, present)

    def test_a_present_holder_closes_the_door_entirely(self):
        """If holder == speaker they would be present, so the caller's
        guard would never let the deflection run."""
        c = self.staff(self.counter(), on=self.char2)
        self.char2.location = self.room1
        self.assertTrue(any_keeper_present(c),
                        "the deflection would have been skipped")

    def test_the_deflection_only_runs_with_nobody_on(self):
        c = self.staff(self.counter(), on=self.char2, off=self.char1)
        self.char1.location = self.room1
        self.char2.location = self.room2          # holder away
        self.assertFalse(any_keeper_present(c))
        self.assertTrue(off_duty_keepers_present(c))


class TestTheRemainingArmsStillWork(_PostCase):
    def line(self, counter):
        said = []
        for ch in (self.char1, self.char2):
            ch.execute_cmd = lambda cmd, _s=said: _s.append(cmd)
        counter._off_shift_deflection(self.char1)
        return " ".join(said)

    def test_it_names_whoever_has_the_shift(self):
        c = self.staff(self.counter(), on=self.char2, off=self.char1)
        self.char1.location = self.room1
        self.char2.location = self.room2
        self.assertIn(self.char2.key, self.line(c))

    def test_an_unstaffed_shift_says_the_counter_is_shut(self):
        c = self.staff(self.counter(), off=self.char1)
        self.char1.location = self.room1
        self.assertIn("nobody's got", self.line(c))

    def test_nobody_off_duty_present_returns_nothing(self):
        c = self.staff(self.counter(), on=self.char2)
        self.char2.location = self.room2
        self.assertIsNone(c._off_shift_deflection(self.char1))
