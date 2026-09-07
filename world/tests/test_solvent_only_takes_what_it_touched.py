"""Cleaning one tag does not destroy the one beside it (#2444).

`GraffitiObject.remove_random_characters` collected **indices** in a
list, and the same index could land in it more than once: once a tag was
scrubbed blank, a later iteration that re-picked it took the
`non_space_indices`-empty branch and marked it again. The reverse-sorted
pop loop then popped that index twice — and the second pop took a
different, intact tag off the wall.

Measured across 400 seeded applications on a wall holding one short tag
and one 46-character tag that **cannot** be scrubbed blank inside a
single application:

```
no short neighbour:     0 / 400   the long tag never vanishes
one short neighbour:  178 / 400   the long tag is destroyed
two short neighbours: 298 / 400
```

The control matters: the long tag can only be leaving because of the
double pop, not because the solvent legitimately erased it.

The same branch had a second defect. `new_message` was bound only inside
`if non_space_indices:`, so on the empty branch it either

* held the **previous iteration's** value — rewriting this entry's
  display text with a neighbouring tag's letters, leaving `message` and
  `entry` describing different things — or
* was never bound at all, raising `UnboundLocalError`, after which the
  room's graffiti could not be cleaned again. Reachable in **107 of 200**
  seeded runs on a wall holding a whitespace-only tag.

A whitespace-only tag was storable because `CmdGraffiti` strips quotes
but not the space inside them: `spray "   " with can` produced a
three-space message, which is truthy and passed the `if not message`
guard. Fixed at both ends — the loop no longer trusts a stale local, and
the command no longer creates the tag.

Spec: `GRAFFITI_SYSTEM_SPEC.md` specifies character-level removal,
progressive degradation, and multiple applications. Losing an untouched
entry wholesale is none of those.
"""
import random

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

# Long enough that ten character removals spread over a whole wall
# cannot blank it. If it leaves the wall, something else took it.
KEEP = "KEEP THIS ONE INTACT PLEASE AND DO NOT ERASE IT"


class _WallCase(EvenniaTest):
    def wall(self, pairs):
        """`pairs` is (author, message) — the author is the tracking
        handle, because the solvent rewrites `message` by design."""
        obj = create_object("typeclasses.objects.GraffitiObject",
                            key="graffiti", location=self.room1)
        obj.db.graffiti_entries = [
            {"message": m, "color": "white", "color_code": "w",
             "author": a, "timestamp": "now",
             "entry": f"Scrawled in white paint: {m}"} for a, m in pairs]
        obj.db.max_entries = 10
        return obj

    def authors(self, obj):
        if not obj.pk:
            return set()
        return {e["author"] for e in (obj.db.graffiti_entries or [])}

    def survivals(self, pairs, amount=10, runs=200):
        """How many of `runs` seeded applications leave "keeper" up."""
        kept = 0
        for seed in range(runs):
            random.seed(seed)
            obj = self.wall(pairs)
            obj.remove_random_characters(amount=amount)
            if "keeper" in self.authors(obj):
                kept += 1
            if obj.pk:
                obj.delete()
        return kept


class TestAnUntouchedTagSurvives(_WallCase):
    def test_with_one_short_neighbour(self):
        self.assertEqual(
            self.survivals([("other", "A"), ("keeper", KEEP)]), 200)

    def test_with_two_short_neighbours(self):
        self.assertEqual(
            self.survivals([("a", "A"), ("b", "B"), ("keeper", KEEP)]), 200)

    def test_with_a_blank_neighbour(self):
        self.assertEqual(
            self.survivals([("blank", "   "), ("keeper", KEEP)]), 200)

    def test_the_control_still_holds(self):
        """It never vanished in this arrangement before the fix either —
        which is what makes the others attributable."""
        self.assertEqual(
            self.survivals([("other", "A LONGER TAG HERE"),
                            ("keeper", KEEP)]), 200)


class TestABlankTagDoesNotJamTheWall(_WallCase):
    def test_cleaning_does_not_raise(self):
        for seed in range(50):
            random.seed(seed)
            obj = self.wall([("blank", "   "), ("keeper", KEEP)])
            obj.remove_random_characters(amount=10)
            if obj.pk:
                obj.delete()

    def test_the_blank_tag_is_retired(self):
        random.seed(0)
        obj = self.wall([("blank", "   "), ("keeper", KEEP)])
        obj.remove_random_characters(amount=10)
        self.assertNotIn("blank", self.authors(obj))


class TestDisplayMatchesTheInk(_WallCase):
    """`message` and `entry` are two views of one tag and must agree —
    the stale local made a blank tag display its neighbour's letters."""

    def test_no_entry_displays_another_tags_text(self):
        for seed in range(100):
            random.seed(seed)
            obj = self.wall([("blank", "   "), ("keeper", KEEP)])
            obj.remove_random_characters(amount=6)
            if not obj.pk:
                continue
            for entry in (obj.db.graffiti_entries or []):
                self.assertIn(entry["message"], entry["entry"],
                              f"seed {seed}: display and ink disagree")
            obj.delete()


class TestTheSolventStillWorks(_WallCase):
    def test_it_still_takes_characters(self):
        random.seed(1)
        obj = self.wall([("keeper", KEEP)])
        before = obj.db.graffiti_entries[0]["message"]
        obj.remove_random_characters(amount=5)
        self.assertNotEqual(obj.db.graffiti_entries[0]["message"], before)

    def test_it_reports_what_it_took(self):
        random.seed(1)
        obj = self.wall([("keeper", KEEP)])
        self.assertEqual(obj.remove_random_characters(amount=5), 5)

    def test_a_fully_scrubbed_tag_is_removed(self):
        random.seed(1)
        obj = self.wall([("short", "AB")])
        obj.remove_random_characters(amount=10)
        self.assertNotIn("short", self.authors(obj))

    def test_an_empty_wall_is_a_no_op(self):
        obj = self.wall([("keeper", KEEP)])
        obj.db.graffiti_entries = []
        self.assertEqual(obj.remove_random_characters(amount=5), 0)

    def test_a_blank_tag_costs_no_scrubbing(self):
        """Wiping nothing off a blank tag is not a character removed."""
        random.seed(2)
        obj = self.wall([("blank", "   ")])
        self.assertEqual(obj.remove_random_characters(amount=5), 0)


class TestTheBlankTagCannotBeCreated(EvenniaTest):
    def test_a_whitespace_message_is_refused(self):
        from commands.CmdGraffiti import CmdGraffiti
        cmd = CmdGraffiti()
        cmd.caller = self.char1
        said = []
        self.char1.msg = lambda *a, **k: said.append(a[0] if a else "")
        cmd._handle_spray_paint_with_spraypaint(None, "   ")
        self.assertTrue(any("specify a message" in str(s) for s in said))

    def test_a_real_message_is_not_refused(self):
        from commands.CmdGraffiti import CmdGraffiti
        cmd = CmdGraffiti()
        cmd.caller = self.char1
        said = []
        self.char1.msg = lambda *a, **k: said.append(a[0] if a else "")
        try:
            cmd._handle_spray_paint_with_spraypaint(None, "  REAL TAG  ")
        except Exception:      # noqa: BLE001 — it gets past the guard
            pass               # and fails later on the None can, fine
        self.assertFalse(any("specify a message" in str(s) for s in said))
