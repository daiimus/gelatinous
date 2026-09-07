"""A corpse is not conscious, and does not resist (#2517, #2519).

## #2519 — three sources, two answers

`CmdDress`'s help offers **`dress corpse in burial shroud`** as an
example, and the command's header comment lists *"Dead characters /
corpses"* as supported. The gate refused it and told the player the
corpse **"is conscious and would resist"**.

`world.consent.is_conscious` read `target.medical_state`, and a `Corpse`
has none — it stores `medical_state_at_death` and
`get_medical_snapshot()` instead. So it fell through the
no-readable-state branch, which returns True on the conservative
principle that helplessness must be *affirmative*. A corpse's
helplessness **is** affirmative; it is simply recorded under a different
name.

Fixed in `consent.py`, not at the call site: all six consumers read it,
and `frisk` already carried a local carve-out for exactly this case. One
answer to "can this thing resist" rather than two.

**The latent half the issue warned about.** Opening the gate would have
turned `undress <corpse>` into an `AttributeError` — `_undress_character`
calls `target.remove_item`, which `Corpse` does not have, and
`_dress_character` calls `wear_item`, which it also does not have. Both
now have corpse branches.

A corpse's clothing model is its **contents**:
`_build_corpse_clothing_coverage_map` renders every item there that
declares `coverage` as covering the body. So dressing is a move in and
undressing is a move out — the existing model, not a new one. Note
`get_worn_items` is deliberately narrower (disguise-essential only,
because that is all the identity signature consumes), which makes it the
wrong list to undress from.

## #2517 — two defects in twenty lines

**The spurious error.** `undress bob jacket` resolves greedily on the
whole phrase first, which is *guaranteed* to fail because the phrase
contains the item word. Stage 3 of the resolver was the only stage that
spoke, so every use of the documented two-argument form printed:

```
Could not find "bob jacket".
You undress Bob, taking: a jacket.
```

The greedy pass is now silent, and a genuine failure still speaks once.

**The item filter.** `[it for it in worn if phrase in it.key.lower()]`
kept **every** substring hit and ignored aliases, so `undress bob shirt`
stripped every garment whose name contained "shirt". `pick_worn` takes
the one item named, exact key or alias first.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


def is_corpse(target):
    from commands.CmdClothing import _is_corpse
    return _is_corpse(target)


def pick_worn(phrase, worn):
    from commands.CmdClothing import pick_worn as real
    return real(phrase, worn)


class _ClothCase(EvenniaTest):
    def garment(self, key, aliases=(), where=None):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=where or self.char1)
        obj.coverage = ["chest"]
        obj.worn_desc = key
        for alias in aliases:
            obj.aliases.add(alias)
        return obj

    def corpse(self):
        return create_object("typeclasses.corpse.Corpse",
                             key="a corpse", location=self.room1)


class TestACorpseCannotResist(_ClothCase):
    def test_a_corpse_is_not_conscious(self):
        from world.consent import is_conscious
        self.assertFalse(is_conscious(self.corpse()))

    def test_a_living_character_still_is(self):
        from world.consent import is_conscious
        self.assertTrue(is_conscious(self.char2))

    def test_the_dress_gate_lets_a_corpse_through(self):
        from commands.CmdClothing import _can_third_party_clothing
        self.assertTrue(
            _can_third_party_clothing(self.char1, self.corpse()))

    def test_a_conscious_stranger_is_still_refused(self):
        """The gate must open for the dead, not for everyone."""
        from commands.CmdClothing import _can_third_party_clothing
        self.assertFalse(
            _can_third_party_clothing(self.char1, self.char2))

    def test_an_object_with_no_medical_surface_is_unchanged(self):
        from world.consent import is_conscious
        plain = create_object("typeclasses.items.Item", key="a crate",
                              location=self.room1)
        self.assertTrue(is_conscious(plain))


class TestDressingAndUndressingACorpse(_ClothCase):
    def test_a_corpse_is_recognised(self):
        self.assertTrue(is_corpse(self.corpse()))

    def test_a_character_is_not(self):
        self.assertFalse(is_corpse(self.char2))

    def test_dressing_moves_the_garment_onto_the_corpse(self):
        from commands.CmdClothing import CmdDress
        body, shroud = self.corpse(), self.garment("a burial shroud")
        cmd = CmdDress()
        cmd.caller = self.char1
        ok, _msg = cmd._dress_corpse(body, shroud)
        self.assertTrue(ok)
        self.assertEqual(shroud.location, body)

    def test_the_corpse_then_reads_as_covered(self):
        """The corpse's own model: contents with coverage are worn."""
        body, shroud = self.corpse(), self.garment("a burial shroud")
        shroud.move_to(body, quiet=True)
        covered = body._build_corpse_clothing_coverage_map()
        self.assertEqual(covered.get("chest"), shroud)

    def test_undressing_takes_it_back(self):
        from commands.CmdClothing import CmdUndress
        body, shroud = self.corpse(), self.garment("a burial shroud")
        shroud.move_to(body, quiet=True)
        cmd = CmdUndress()
        cmd.caller = self.char1
        removed = cmd._undress_corpse(body, None)
        self.assertEqual(removed, [shroud])
        self.assertEqual(shroud.location, self.char1)

    def test_undressing_a_named_garment(self):
        from commands.CmdClothing import CmdUndress
        body = self.corpse()
        shroud = self.garment("a burial shroud", where=body)
        boots = self.garment("black leather combat boots", where=body)
        cmd = CmdUndress()
        cmd.caller = self.char1
        removed = cmd._undress_corpse(body, "shroud")
        self.assertEqual(removed, [shroud])
        self.assertEqual(boots.location, body, "an unnamed garment moved")

    def test_undressing_a_bare_corpse_removes_nothing(self):
        from commands.CmdClothing import CmdUndress
        cmd = CmdUndress()
        cmd.caller = self.char1
        self.assertEqual(cmd._undress_corpse(self.corpse(), None), [])

    def test_loose_loot_is_not_clothing(self):
        """Only items declaring coverage count — a corpse's pockets are
        not a wardrobe."""
        from commands.CmdClothing import CmdUndress
        body = self.corpse()
        create_object("typeclasses.items.Item", key="a credstick",
                      location=body)
        cmd = CmdUndress()
        cmd.caller = self.char1
        self.assertEqual(cmd._undress_corpse(body, None), [])


class TestThePickerTakesWhatWasNamed(_ClothCase):
    def test_it_takes_one_item_not_every_match(self):
        shirt = self.garment("a work shirt")
        dress_shirt = self.garment("a dress shirt")
        picked = pick_worn("shirt", [shirt, dress_shirt])
        self.assertIn(picked, (shirt, dress_shirt))
        self.assertIsNot(picked, None)

    def test_an_exact_key_beats_a_longer_match(self):
        shirt = self.garment("shirt")
        dress_shirt = self.garment("a dress shirt")
        self.assertIs(pick_worn("shirt", [dress_shirt, shirt]), shirt)

    def test_an_alias_is_found(self):
        coat = self.garment("Vantage all-weather greatcoat", ["coat"])
        self.assertIs(pick_worn("coat", [coat]), coat)

    def test_an_unmatched_phrase_finds_nothing(self):
        self.assertIsNone(pick_worn("hat", [self.garment("a shirt")]))

    def test_an_empty_phrase_finds_nothing(self):
        self.assertIsNone(pick_worn("", [self.garment("a shirt")]))


class TestTheGreedyPassIsSilent(EvenniaTest):
    """#2517's first defect was an error message, so it is pinned at
    the source: the greedy resolve must pass `quiet=True`."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdClothing.py").read_text(
            errors="ignore")

    def test_the_greedy_resolve_is_quiet(self):
        self.assertIn("_resolve_clothing_target(caller, args, quiet=True)",
                      self._source())

    def test_the_resolver_accepts_quiet(self):
        self.assertIn(
            "def _resolve_clothing_target(caller, target_phrase, quiet=False)",
            self._source())

    def test_a_genuine_failure_still_speaks(self):
        """Silencing the greedy pass must not make a real miss silent."""
        body = self._source()
        idx = body.index("if target is None:\n            # Nothing resolved")
        self.assertIn("_resolve_clothing_target(caller, args)",
                      body[idx:idx + 400])

    def test_no_substring_only_filter_survives(self):
        self.assertNotIn("phrase in it.key.lower()", self._source())
