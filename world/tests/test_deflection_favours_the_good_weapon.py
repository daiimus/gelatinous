"""A tennis racket beats a chainsaw at batting grenades (#2493).

## The sign was inverted

Success is `motorics_roll >= final_threshold`, so a **higher** threshold
is harder — and `deflection_bonus` was **added** to it. Every weapon in
the table therefore behaved as the opposite of its own prototype
comment. Measured across all twelve prototypes carrying a bonus:

```
weapon                       bonus   was    now
tennis racket "BEST!"        +0.50    20     0
baseball bat                 +0.30    16     4
katana                       +0.25    15     5
staff                        +0.10    12     8
dagger                       -0.05     9    11
chainsaw "terrible"          -0.50     0    20
```

`roll_stat` is `randint(1, motorics)`, so a threshold of 20 is
unreachable for anyone below motorics 20 and a threshold of 0 always
succeeds. The weapon the prototypes call *"BEST deflection weapon!"*
could never deflect anything; the one they call *"terrible for
defense"* deflected everything.

## And anything in your hand counted as a weapon

`is_melee_weapon` was `not obj.db.is_ranged` — and **every** item
defaults to melee (the brawl-with-anything design), so a lit cigarette
deflected grenades exactly as well as a baseline weapon.

The discriminator is the `("weapon", "type")` tag carried by
`MELEE_WEAPON_BASE`. That is the same one `get_wielded_weapon` settled
on in #516, for the same stated reason — `db.weapon_type` is useless
because every item carries "melee" at creation. Reused rather than
re-derived, so "is this a weapon" has one answer.

## What this does NOT do

**It does not tune the numbers**, and they are not tuned. With the sign
corrected, a +0.50 weapon sits at threshold 0 and deflects *every*
grenade with certainty, while the base threshold of 10 against
`randint(1, motorics)` means an unarmed-of-good-gear character below
motorics 10 can never deflect at all. That curve is a balance question,
not a correctness one, and no system in this game is tuned yet — so the
gap is recorded rather than guessed at. Filed separately.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.throwing import is_melee_weapon


def threshold(bonus):
    """The arithmetic under test, as the code now does it."""
    return 10 - int(bonus * 20)


class TestTheGoodWeaponIsEasier(EvenniaTest):
    def test_the_best_weapon_has_the_lowest_threshold(self):
        self.assertLess(threshold(0.50), threshold(0.0))

    def test_the_worst_weapon_has_the_highest(self):
        self.assertGreater(threshold(-0.50), threshold(0.0))

    def test_the_table_is_ordered_by_quality(self):
        bonuses = [0.50, 0.30, 0.25, 0.15, 0.10, 0.05, 0.0,
                   -0.05, -0.15, -0.50]
        thresholds = [threshold(b) for b in bonuses]
        self.assertEqual(thresholds, sorted(thresholds),
                         "a better weapon is not easier")

    def test_a_plain_weapon_is_unchanged(self):
        self.assertEqual(threshold(0.0), 10)

    def test_the_source_subtracts(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "world" / "combat" / "throwing.py").read_text(
            errors="ignore")
        self.assertIn("final_threshold = base_threshold - threshold_modifier",
                      body)
        self.assertNotIn(
            "final_threshold = base_threshold + threshold_modifier", body)


class TestEveryPrototypeMatchesItsOwnComment(EvenniaTest):
    """The prototypes state the intent in prose; the code should agree
    with them. This is the check nobody had run."""

    def _bonuses(self):
        """Both shapes: melee weapons declare `deflection_bonus` as a
        top-level prototype key, armour declares it inside `attrs`.
        Scanning only `attrs` finds 5 of the 12 and quietly misses every
        weapon the issue is actually about."""
        import world.prototypes as protos
        out = {}
        for value in vars(protos).values():
            if not isinstance(value, dict):
                continue
            key = str(value.get("key", "?"))
            top = value.get("deflection_bonus")
            if isinstance(top, (int, float)):
                out[key] = float(top)
            for attr in (value.get("attrs") or []):
                if (isinstance(attr, (list, tuple)) and len(attr) >= 2
                        and attr[0] == "deflection_bonus"):
                    out[key] = float(attr[1])
        return out

    def test_the_table_is_still_populated(self):
        self.assertGreaterEqual(len(self._bonuses()), 10)

    def test_the_best_named_weapon_beats_the_worst(self):
        bonuses = self._bonuses()
        self.assertIn("tennis racket", bonuses)
        self.assertIn("chainsaw", bonuses)
        self.assertLess(threshold(bonuses["tennis racket"]),
                        threshold(bonuses["chainsaw"]))

    def test_no_positive_bonus_raises_the_threshold(self):
        for key, bonus in self._bonuses().items():
            if bonus > 0:
                self.assertLess(threshold(bonus), 10, f"{key} got harder")

    def test_no_negative_bonus_lowers_it(self):
        for key, bonus in self._bonuses().items():
            if bonus < 0:
                self.assertGreater(threshold(bonus), 10, f"{key} got easier")


class TestOnlyAWeaponDeflects(EvenniaTest):
    def _thing(self, key, weapon=False, ranged=False):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=self.room1)
        if weapon:
            obj.tags.add("weapon", category="type")
        obj.db.is_ranged = ranged
        return obj

    def test_a_melee_weapon_deflects(self):
        self.assertTrue(is_melee_weapon(self._thing("a katana", weapon=True)))

    def test_a_cigarette_does_not(self):
        self.assertFalse(is_melee_weapon(self._thing("a lit cigarette")))

    def test_a_random_item_does_not(self):
        self.assertFalse(is_melee_weapon(self._thing("a crate")))

    def test_a_ranged_weapon_does_not(self):
        self.assertFalse(is_melee_weapon(
            self._thing("a pistol", weapon=True, ranged=True)))

    def test_it_uses_the_same_tag_as_get_wielded_weapon(self):
        """One answer to "is this a weapon", not two (#516)."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        utils = (root / "world" / "combat" / "utils.py").read_text(
            errors="ignore")
        throwing = (root / "world" / "combat" / "throwing.py").read_text(
            errors="ignore")
        needle = 'tags.has("weapon", category="type")'
        self.assertIn(needle, utils)
        self.assertIn(needle, throwing)
