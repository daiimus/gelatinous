"""`get <x> from <y>` is not a way to strip people (#2456).

Four findings in one command family, all of them the same shape: the
umbrella verb shares a destination with a standalone verb but not its
guards.

**1. A person is not a container.** `_find_container_in_room` built its
candidate list as *every object in the room except the caller* —
characters included — and `Character.search` takes the
`candidates is not None` bypass, so Evennia's key matching resolved a
person the identity pipeline would have refused. Then
`_find_item_in_container` searched their `contents`, which holds worn
garments and wielded weapons alongside pocket lint.

So a plain `get jacket from sable` stripped a fully awake, unwilling
character: no Motorics/Resonance contest, no caught-and-Alerted
consequence, no `crime` event, no trust grant — all of which `steal`,
`wrest` and `undress` enforce. And the two systems then disagreed
forever, because `get_worn_items` only prunes entries whose object was
*deleted*: the victim kept rendering as wearing the jacket now in the
thief's hand, it kept counting toward coverage, and it kept feeding the
disguise signature — a mask lifted off a face left the wearer's Apparent
UID unchanged.

`get x from me` needed no second party at all: `Character.search`
answers the literal `me` before candidates are consulted.

A corpse is safe from this and stays reachable, because `Corpse` derives
"worn" live from its own contents. That is exactly why the bug survived:
the code is correct on the target it was written for.

**2. The severed limb's ledger.** `undress <limb> <item>` prunes
`appendage.db.worn_items`; this door reached the same physical contents
through a resolver that knows nothing about it. The limb went on saying
*"It still wears a bloodstained glove"* — and once the glove was
deleted, the dangling entry crashed `look` on the limb, because
`_build_worn_items_line` had no prune of its own.

**3. `at_drop` had no caller.** This game's `drop` replaced Evennia's,
and Evennia's was the only thing that called `at_drop`. So single-use
issue clothing survived being let go of: press the dispenser, drop the
jumpsuit, repeat, for an unbounded pile of free Thawn-Harrison kit —
precisely what `_perish`'s docstring says it exists to prevent. Its
two-verb signature ("off" / "loose") was written for both doors and only
`remove` was live.

**4. A handless character got silence.** Both hand loops iterate
`caller.hands`; an empty view fell off the end of the method with no
message and no effect. Two real cases reach it — both hands severed, and
a species that declares no grasping containers. `CmdGive` already
answers this state in words.

Finding 2 of the issue (`give` reading a refusal as success) was already
fixed under #2516 and is pinned there.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdInventory import CmdDrop, CmdGet


class _LootCase(EvenniaCommandTest):
    def garment(self, where, key="a jacket"):
        item = create_object("typeclasses.items.Item", key=key,
                             location=where)
        item.db.is_wearable = True
        item.db.coverage = ["chest"]
        item.db.worn_desc = key
        return item


class TestAPersonIsNotAContainer(_LootCase):
    def setUp(self):
        super().setUp()
        self.char2.location = self.room1
        self.char1.location = self.room1
        self.jacket = self.garment(self.char2)

    def test_you_cannot_get_from_a_conscious_character(self):
        self.call(CmdGet(), "jacket from Char2", caller=self.char1)
        self.assertEqual(self.jacket.location, self.char2)

    def test_it_points_at_the_verbs_that_do_have_guards(self):
        out = self.call(CmdGet(), "jacket from Char2", caller=self.char1)
        self.assertTrue(any(verb in out
                            for verb in ("steal", "wrest", "undress")),
                        f"no pointer to a gated verb: {out!r}")

    def test_you_cannot_get_from_yourself_either(self):
        """No second party required: `search` answers `me` before it
        ever looks at candidates. Asserted on the MESSAGE, because the
        hands write-back does not stick on this path anyway, so an
        assertion about hands passes against the bug."""
        self.garment(self.char1, key="a jumpsuit")
        out = self.call(CmdGet(), "jumpsuit from me", caller=self.char1)
        self.assertNotIn("You take a jumpsuit from", out)

    def test_the_self_alias_is_refused_too(self):
        self.garment(self.char1, key="a jumpsuit")
        out = self.call(CmdGet(), "jumpsuit from self", caller=self.char1)
        self.assertNotIn("You take a jumpsuit from", out)

    def test_it_points_you_at_remove(self):
        self.garment(self.char1, key="a jumpsuit")
        out = self.call(CmdGet(), "jumpsuit from me", caller=self.char1)
        self.assertIn("remove", out)

    def test_a_corpse_is_still_lootable(self):
        """The door this path was BUILT for — and safe, because a
        corpse derives worn from its contents."""
        corpse = create_object("typeclasses.corpse.Corpse", key="a corpse",
                               location=self.room1)
        jeans = self.garment(corpse, key="some jeans")
        self.call(CmdGet(), "jeans from corpse", caller=self.char1)
        self.assertEqual(jeans.location, self.char1)

    def test_a_real_container_still_works(self):
        box = create_object("typeclasses.objects.Object", key="a crate",
                            location=self.room1)
        thing = create_object("typeclasses.items.Item", key="a wrench",
                              location=box)
        self.call(CmdGet(), "wrench from crate", caller=self.char1)
        self.assertEqual(thing.location, self.char1)


class TestTheSeveredLimbKeepsAnHonestLedger(_LootCase):
    def limb(self):
        arm = create_object("typeclasses.items.Appendage",
                            key="a severed left arm", location=self.room1)
        glove = self.garment(arm, key="a bloodstained glove")
        arm.db.worn_items = {"left_hand": [glove]}
        return arm, glove

    def test_taking_the_glove_clears_the_entry(self):
        arm, glove = self.limb()
        self.call(CmdGet(), "glove from arm", caller=self.char1)
        self.assertEqual(glove.location, self.char1)
        remaining = [i for entries in (arm.db.worn_items or {}).values()
                     for i in (entries or [])]
        self.assertNotIn(glove, remaining)

    def test_the_limb_stops_advertising_it(self):
        arm, _glove = self.limb()
        self.call(CmdGet(), "glove from arm", caller=self.char1)
        self.assertNotIn("still wears",
                         arm._build_worn_items_line(self.char1))

    def test_a_glove_still_on_the_limb_is_still_described(self):
        arm, _glove = self.limb()
        self.assertIn("glove", arm._build_worn_items_line(self.char1))

    def test_a_deleted_garment_does_not_crash_look(self):
        """The escalation: a dangling entry deserializes to None and
        `None.get_display_name` raised inside `return_appearance`."""
        arm, glove = self.limb()
        glove.delete()
        self.assertEqual(arm._build_worn_items_line(self.char1), "")
        arm.return_appearance(self.char1)      # must not raise


class TestSingleUseClothingPerishesOnTheWayDown(_LootCase):
    def issue(self):
        item = self.garment(self.char1, key="a paper jumpsuit")
        item.db.single_use = True
        hands = dict(self.char1.hands)
        hands[list(hands)[0]] = item
        self.char1.hands = hands
        return item

    def test_dropping_it_destroys_it(self):
        item = self.issue()
        self.call(CmdDrop(), "jumpsuit", caller=self.char1)
        self.assertFalse(item.pk, "the jumpsuit survived the floor")

    def test_it_says_the_seams_tore(self):
        self.issue()
        out = self.call(CmdDrop(), "jumpsuit", caller=self.char1)
        self.assertIn("tears", out)

    def test_it_does_not_also_narrate_a_normal_drop(self):
        """The wielded branch says "You release X from your left hand
        and drop it." — assert on THAT, not on "You drop", which a
        wielded drop never prints and which therefore passes against
        the bug."""
        self.issue()
        out = self.call(CmdDrop(), "jumpsuit", caller=self.char1)
        self.assertNotIn("and drop it", out)

    def test_an_ordinary_garment_still_drops(self):
        item = self.garment(self.char1, key="a leather coat")
        hands = dict(self.char1.hands)
        hands[list(hands)[0]] = item
        self.char1.hands = hands
        self.call(CmdDrop(), "coat", caller=self.char1)
        self.assertTrue(item.pk)
        self.assertEqual(item.location, self.room1)


class TestAHandlessCharacterIsToldWhy(_LootCase):
    """`hands` is a derived view: `{location: ... for location in
    grasping if location not in severed}`. It is empty for a body whose
    grasping containers are all severed, and for a species that declares
    none — a rat surfaces no slots at all. Patched on the CLASS here
    because it is a property; both test characters share the typeclass,
    which is fine since only one of them acts."""

    def handless(self):
        from unittest import mock
        from typeclasses.characters import Character
        return mock.patch.object(Character, "hands",
                                 property(lambda self: {}))

    def test_get_says_something(self):
        item = create_object("typeclasses.items.Item", key="a shiv",
                             location=self.room1)
        with self.handless():
            out = self.call(CmdGet(), "shiv", caller=self.char1)
        self.assertTrue(out.strip(), "the command said nothing at all")

    def test_it_names_the_reason(self):
        create_object("typeclasses.items.Item", key="a shiv",
                      location=self.room1)
        with self.handless():
            out = self.call(CmdGet(), "shiv", caller=self.char1)
        self.assertIn("no hands", out)

    def test_and_the_item_stays_put(self):
        item = create_object("typeclasses.items.Item", key="a shiv",
                             location=self.room1)
        with self.handless():
            self.call(CmdGet(), "shiv", caller=self.char1)
        self.assertEqual(item.location, self.room1)

    def test_taking_from_a_container_says_it_too(self):
        box = create_object("typeclasses.objects.Object", key="a crate",
                            location=self.room1)
        create_object("typeclasses.items.Item", key="a wrench",
                      location=box)
        with self.handless():
            out = self.call(CmdGet(), "wrench from crate",
                            caller=self.char1)
        self.assertIn("no hands", out)

    def test_a_character_with_hands_is_unaffected(self):
        item = create_object("typeclasses.items.Item", key="a shiv",
                             location=self.room1)
        self.call(CmdGet(), "shiv", caller=self.char1)
        self.assertEqual(item.location, self.char1)
