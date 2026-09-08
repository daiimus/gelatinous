"""You can't force pharmacology on the unwilling (#2458).

The trust gate lived inside `check_medical_requirements`, and the
consumption verbs only call that helper `if is_medical_item(item)`.
When #487/#498 made the delivery TAG the gate for non-medical
consumables, that `if` took the consent check with it.

So `inject guttervenom bob` landed 3 pain and a sedative on a
conscious, unrestrained, untrusting Bob with **no refusal message and
no grant** — while the identical act with a MEDICAL item was correctly
refused with *"...would resist treatment — they'd need to trust you to
heal them (or be restrained)."* `chug` and `devour` were worse still:
they REJECT medical items outright, so their third-party path had no
gate at any point.

`TRUST_AND_CONSENT_SPEC` is marked shipped and live, names `inject`
explicitly in the `heal` class, and says the whole point is that "you
can't grief someone who is awake, free, and unwilling".

The gate is hoisted to `get_item_and_target` — the funnel every
consumption verb resolves its target through — so no verb added later
can forget it. The medical path still runs its own check; asking twice
costs one lookup and answers the same.

**Multi-word names are the second half.** The parser took `parts[0]` as
the entire item name, so every multi-word name or authored alias was
read as item + target and answered with the item's OWN second word as a
missing person: `drink fortified wine` → *"Cannot find 'wine'."*,
`eat bowl of noodles` → *"Cannot find 'of'."* It now scans
longest-first, and the target takes the whole remainder rather than one
token, because sdescs are usually multi-word too.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.consent import grant_trust


class _DoseCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        for char in (self.char1, self.char2):
            char.location = self.room1
        self.char2.height, self.char2.build = "average", "stocky"
        self.char2.sdesc_keyword = "woman"

    def street_drug(self, key="guttervenom syringe"):
        """NOT a medical item — only a delivery tag, like the real
        GUTTERVENOM_SYRINGE prototype."""
        item = create_object("typeclasses.items.Item", key=key,
                             location=self.char1)
        item.tags.add("inject", category="delivery_method")
        return item

    def parse(self, phrase):
        from commands.CmdConsumption import CmdInject
        cmd = CmdInject()
        cmd.caller = self.char1
        return cmd.get_item_and_target(phrase, require_medical=False)


class TestAStreetDrugNeedsConsentToo(_DoseCase):
    def test_an_untrusting_target_is_refused(self):
        self.street_drug()
        self.assertTrue(self.parse("guttervenom woman")["errors"])

    def test_the_refusal_says_why(self):
        self.street_drug()
        errors = " ".join(self.parse("guttervenom woman")["errors"])
        self.assertIn("trust", errors)

    def test_a_granted_target_is_allowed(self):
        self.street_drug()
        grant_trust(self.char2, self.char1, "heal")
        self.assertEqual(self.parse("guttervenom woman")["errors"], [])

    def test_dosing_yourself_never_needs_a_grant(self):
        self.street_drug()
        result = self.parse("guttervenom")
        self.assertIs(result["target"], self.char1)
        self.assertEqual(result["errors"], [])


class TestTheGateIsAtTheFunnel(_DoseCase):
    """Hoisted so a verb added later cannot forget it — `chug` and
    `devour` reject medical items outright, so they never touched the
    old medical-only helper at all."""

    def _refused(self, cmd_cls, phrase):
        cmd = cmd_cls()
        cmd.caller = self.char1
        return bool(cmd.get_item_and_target(
            phrase, require_medical=False)["errors"])

    def test_inject_is_gated(self):
        self.street_drug()
        from commands.CmdConsumption import CmdInject
        self.assertTrue(self._refused(CmdInject, "guttervenom woman"))

    def test_chug_is_gated(self):
        self.street_drug("bottle of rotgut")
        from commands.CmdConsumption import CmdChug
        self.assertTrue(self._refused(CmdChug, "rotgut woman"))

    def test_devour_is_gated(self):
        self.street_drug("ration bar")
        from commands.CmdConsumption import CmdDevour
        self.assertTrue(self._refused(CmdDevour, "ration woman"))


class TestMultiWordNamesResolve(_DoseCase):
    def test_a_two_word_item_is_not_split(self):
        item = self.street_drug("fortified wine")
        result = self.parse("fortified wine")
        self.assertIs(result["item"], item)
        self.assertEqual(result["errors"], [])

    def test_a_four_word_item_is_not_split(self):
        item = self.street_drug("bowl of rat noodles")
        self.assertIs(self.parse("bowl of rat noodles")["item"], item)

    def test_a_two_word_item_plus_a_target(self):
        item = self.street_drug("fortified wine")
        grant_trust(self.char2, self.char1, "heal")
        result = self.parse("fortified wine woman")
        self.assertIs(result["item"], item)
        self.assertIs(result["target"], self.char2)

    def test_a_multi_word_target_resolves(self):
        self.street_drug("guttervenom syringe")
        grant_trust(self.char2, self.char1, "heal")
        result = self.parse("guttervenom stocky woman")
        self.assertIs(result["target"], self.char2)

    def test_the_longest_name_wins_over_a_shorter_one(self):
        """Both are carried; the player typed the longer phrase on
        purpose."""
        self.street_drug("wine")
        longer = self.street_drug("fortified wine")
        self.assertIs(self.parse("fortified wine")["item"], longer)

    def test_an_unknown_item_still_reports_the_item(self):
        self.street_drug()
        errors = " ".join(self.parse("hovercar woman")["errors"])
        self.assertIn("hovercar", errors)
