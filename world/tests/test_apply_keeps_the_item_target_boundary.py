"""`apply <multi-word item> on <target>` reaches the target (#2454).

`CmdApply.func` splits correctly on " on " — `item_phrase` = "gauze
bandages", `target_phrase` = "stout woman" — and then **threw the
boundary away**:

```python
args = f"{item_phrase.strip()} {target_phrase}"   # "gauze bandages stout woman"
```

`get_item_and_target` re-splits on whitespace and takes `parts[0]` as
the item and `rest[0]` as the target. So the item resolved as "gauze"
and the TARGET resolved as **"bandages"**, which is not a person, and
the command bounced with `Cannot find 'bandages'.`

**NPC field medics could therefore never land a treatment.** The medic
issues `apply {item.key} on {token}`, and `item.key` for its par kit is
the two-word `"gauze bandages"` while `token` is the casualty's sdesc,
usually also multi-word. So every `apply` bounced with a parser error
only the NPC "saw": nothing bandaged, no bleed clamped, `use_item()`
never called so no supply consumed — and the medic still banked a
positive `worked_a_scene` thought, because `used` counts commands
ISSUED rather than treatments landed, while a 300-second per-casualty
debounce blocked any retry.

Players hit the same parse whenever they typed an item's full name.
Their workaround was the single-word alias (`apply gauze on X`), which
the NPC never uses because it passes `item.key`.

The fix hands the already-known halves through instead of round-
tripping them: a parser that splits on whitespace cannot represent a
multi-word name, so the caller that DID work out the boundary should
not have to throw it away and hope.

**Finding 1 of that issue did not survive checking.** `is_grappled` was
being called with one argument against a two-argument signature, so
casualty recovery raised `TypeError` into a bare `except` and answered
"no" forever — but `world/director/medical.py:188` and
`world/souls/jobs.py:818` now both pass `(handler, casualty)`, each
with a comment naming the arity.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdConsumption import CmdApply


class _ApplyCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.char2.height = "average"
        self.char2.build = "stocky"
        self.char2.sdesc_keyword = "woman"

    def kit(self, key="gauze bandages"):
        """A REAL medical item. `is_medical_item` reads a TAG
        (`medical_item` / `item_type`), not an attribute — a `db.
        is_medical_item = True` fixture sails past creation and then
        bails at the medical check with the target still defaulted to
        the caller, which reads exactly like the parser bug under test.
        Mirrors the GAUZE_BANDAGES prototype."""
        item = create_object("typeclasses.items.Item", key=key,
                             location=self.char1)
        item.tags.add("medical_item", category="item_type")
        item.tags.add("apply", category="delivery_method")
        item.tags.add("bandage", category="delivery_method")
        item.attributes.add("medical_type", "wound_care")
        return item

    def parse(self, phrase):
        """Drive the real parser the way CmdApply does."""
        cmd = CmdApply()
        cmd.caller = self.char1
        cmd.args = phrase
        raw = phrase.replace(" to ", " on ")
        if " on " in raw:
            item_phrase, _, target_phrase = raw.partition(" on ")
            return cmd.get_item_and_target(
                None, item_phrase=item_phrase,
                target_phrase=target_phrase.strip())
        return cmd.get_item_and_target(raw)


class TestTheBoundarySurvives(_ApplyCase):
    def test_a_multi_word_item_resolves_to_the_item(self):
        kit = self.kit()
        self.assertIs(self.parse("gauze bandages on woman")["item"], kit)

    def test_and_the_target_is_the_person_not_the_second_word(self):
        self.kit()
        self.assertIs(self.parse("gauze bandages on woman")["target"],
                      self.char2)

    def test_it_does_not_error(self):
        self.kit()
        self.assertEqual(self.parse("gauze bandages on woman")["errors"], [])

    def test_a_multi_word_target_works_too(self):
        """The NPC passes the casualty's sdesc, usually multi-word."""
        self.kit()
        result = self.parse("gauze bandages on stocky woman")
        self.assertIs(result["target"], self.char2)

    def test_the_to_preposition_behaves_the_same(self):
        self.kit()
        self.assertIs(self.parse("gauze bandages to woman")["target"],
                      self.char2)


class TestTheSingleWordFormStillWorks(_ApplyCase):
    """The player workaround must not regress."""

    def test_a_single_word_item_and_target(self):
        kit = self.kit("gauze")
        result = self.parse("gauze on woman")
        self.assertIs(result["item"], kit)
        self.assertIs(result["target"], self.char2)

    def test_no_target_defaults_to_self(self):
        self.kit("gauze")
        self.assertIs(self.parse("gauze")["target"], self.char1)

    def test_an_unknown_item_still_errors(self):
        self.kit()
        self.assertTrue(self.parse("hovercar on woman")["errors"])

    def test_an_unknown_target_still_errors(self):
        self.kit()
        self.assertTrue(self.parse("gauze bandages on zephyr")["errors"])


class TestTheRealCommandLandsIt(_ApplyCase):
    """These drive the COMMAND, so they run against the unfixed tree
    too — the `parse()` helper above passes the new keyword arguments
    and merely errors there, which is a harness artifact rather than
    evidence."""

    def test_the_command_does_not_bounce_on_a_two_word_kit(self):
        self.kit()
        out = self.call(CmdApply(), "gauze bandages on woman")
        self.assertNotIn("Cannot find 'bandages'", out)

    def test_it_does_not_mistake_the_second_word_for_a_person(self):
        self.kit()
        out = self.call(CmdApply(), "gauze bandages on woman")
        self.assertNotIn("bandages'", out)

    def test_a_multi_word_target_does_not_bounce_either(self):
        self.kit()
        out = self.call(CmdApply(), "gauze bandages on stocky woman")
        self.assertNotIn("Cannot find", out)

    def test_the_to_form_does_not_bounce(self):
        self.kit()
        out = self.call(CmdApply(), "gauze bandages to woman")
        self.assertNotIn("Cannot find", out)

    def test_the_single_word_alias_still_does_not_bounce(self):
        """The player workaround — must not regress."""
        self.kit("gauze")
        out = self.call(CmdApply(), "gauze on woman")
        self.assertNotIn("Cannot find", out)

    def test_a_genuinely_missing_target_still_reports_it(self):
        self.kit()
        out = self.call(CmdApply(), "gauze bandages on zephyr")
        self.assertIn("Cannot find", out)

    def test_the_npc_form_is_exactly_this(self):
        """`npc.execute_cmd(f"apply {item.key} on {token}")` — the key
        is two words, which is what made it unreachable."""
        from world.prototypes import GAUZE_BANDAGES
        self.assertIn(" ", GAUZE_BANDAGES["key"])


class TestTheRecoveryArityStaysFixed(_ApplyCase):
    """Finding 1, already closed — pinned, not counted as evidence."""

    def test_is_grappled_is_called_with_both_arguments(self):
        import inspect
        from world.director import medical
        from world.souls import jobs
        for module in (medical, jobs):
            source = inspect.getsource(module)
            self.assertNotIn("is_grappled(casualty)", source)
            self.assertNotIn("is_grappled(body)", source)
