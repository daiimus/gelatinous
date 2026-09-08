"""Stripping a corpse works, and does not crash (#2475).

The reported symptom is real and current: `undress corpse` answers

    the rotting corpse is conscious and would resist — they'd need to
    trust you to dress them (or be restrained).

The reported CAUSE is stale. `is_conscious` was taught to recognise a
`Corpse` under #2519 and does. What reaches it is not a corpse.

`_resolve_clothing_target` stage 3 returned `caller.search(...)` raw.
`search(quiet=True)` returns a **list**; only the loud form returns an
object. Stage 2 unwraps, stage 3 did not — and the greedy first pass in
`undress` and `dress` is always quiet, so every room-resolved target
came back as a one-element list.

A list is not a `Corpse`. `is_conscious` fell through to its
conservative "no readable medical state, assume awake" branch, the
caller was told the corpse would resist, and composing that very message
raised:

    AttributeError: 'list' object has no attribute 'get_display_name'

so the command did not even finish saying no.

Reproduced end to end before fixing, which is what the issue asked for:
it warned the fix might be moot if target resolution rejected corpses
earlier. It did not reject them — it mangled them.

Related: `get <garment> from <corpse>` reaches the same fiction through
`CmdGet` with no consent gate at all (#2456). Not touched here.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdClothing import CmdDress, CmdUndress, _resolve_clothing_target


class _CorpseCase(EvenniaCommandTest):
    def corpse(self, key="a rotting corpse"):
        return create_object("typeclasses.corpse.Corpse", key=key,
                             location=self.room1)

    def garment(self, where, key="a shirt"):
        item = create_object("typeclasses.items.Item", key=key,
                             location=where)
        item.db.is_wearable = True
        item.db.coverage = ["chest"]
        item.db.worn_desc = "a shirt"
        return item


class TestTheTargetResolvesToAnObject(_CorpseCase):
    """The defect, at the seam it actually lives at."""

    def test_the_quiet_pass_returns_an_object_not_a_list(self):
        corpse = self.corpse()
        found = _resolve_clothing_target(self.char1, "corpse", quiet=True)
        self.assertNotIsInstance(found, (list, tuple))
        self.assertEqual(found, corpse)

    def test_the_loud_pass_agrees(self):
        corpse = self.corpse()
        self.assertEqual(
            _resolve_clothing_target(self.char1, "corpse", quiet=False),
            corpse)

    def test_no_match_is_still_none(self):
        self.assertIsNone(
            _resolve_clothing_target(self.char1, "a nonexistent thing",
                                     quiet=True))

    def test_the_consent_gate_can_now_see_a_corpse(self):
        from world.consent import is_conscious
        corpse = self.corpse()
        found = _resolve_clothing_target(self.char1, "corpse", quiet=True)
        self.assertFalse(is_conscious(found))
        self.assertFalse(is_conscious(corpse))


class TestUndressingACorpse(_CorpseCase):
    def test_it_does_not_refuse(self):
        corpse = self.corpse()
        self.garment(corpse)
        out = self.call(CmdUndress(), "corpse", caller=self.char1)
        self.assertNotIn("would resist", out)

    def test_the_garment_ends_up_with_the_looter(self):
        corpse = self.corpse()
        shirt = self.garment(corpse)
        self.call(CmdUndress(), "corpse", caller=self.char1)
        self.assertEqual(shirt.location, self.char1)

    def test_it_says_what_was_taken(self):
        corpse = self.corpse()
        self.garment(corpse)
        out = self.call(CmdUndress(), "corpse", caller=self.char1)
        self.assertIn("shirt", out)

    def test_a_named_garment_works_too(self):
        corpse = self.corpse()
        shirt = self.garment(corpse, key="a shirt")
        boots = self.garment(corpse, key="some boots")
        self.call(CmdUndress(), "corpse boots", caller=self.char1)
        self.assertEqual(boots.location, self.char1)
        self.assertEqual(shirt.location, corpse)

    def test_a_bare_corpse_says_so_without_crashing(self):
        self.corpse()
        out = self.call(CmdUndress(), "corpse", caller=self.char1)
        self.assertIn("isn't wearing", out)


class TestDressingACorpse(_CorpseCase):
    """The mirror door — same resolver, so it had the same defect."""

    def test_a_shroud_goes_onto_the_body(self):
        corpse = self.corpse()
        shroud = self.garment(self.char1, key="a burial shroud")
        self.call(CmdDress(), "corpse in shroud", caller=self.char1)
        self.assertEqual(shroud.location, corpse)

    def test_it_does_not_refuse(self):
        self.corpse()
        self.garment(self.char1, key="a burial shroud")
        out = self.call(CmdDress(), "corpse in shroud", caller=self.char1)
        self.assertNotIn("would resist", out)


class TestTheLivingStillGetToRefuse(_CorpseCase):
    """The gate must still hold for someone who can contest — a fix
    that resolved corpses by opening the gate would be worse than the
    bug."""

    def test_a_conscious_character_is_still_refused(self):
        self.garment(self.char2, key="a jacket")
        out = self.call(CmdUndress(), "Char2", caller=self.char1)
        self.assertIn("resist", out)
