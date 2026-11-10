"""`light`, `smoke` and `snuff` name the smokable through the core matcher (#3783).

The three commands used to compare the typed phrase as a SUBSTRING of the
key and aliases joined together, so a fragment from the middle of a word
("rette") lit the cigarette, and an ordinal ("2nd cig") was read as the
literal text "2nd cig" and found nothing. They now hand the held smokables
to `caller.search(name, candidates=pool, quiet=True)`, the matcher every
other command uses: exact key or alias first, then word-start partials,
then ordinals over the pool.

Every test here drives the real command on real objects held in real hands.
These also carry the command-level pins that `test_smoke.py` held against
duck-typed fakes (lights, already lit, light-other, needs lit, puff count,
last puff, snuff), which cannot run against the core matcher.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdSmoke import CmdLight, CmdSmoke, CmdSnuff
from world import smoke as sm

_KEY = "Longhaul cigarette"
_ALIAS = "durry"          # an alias that is NOT a substring of the key
_FRAGMENT = "rette"       # the middle of a word of the key

_NOT_HOLDING_OWN = "You aren't holding a cigarette matching that."


class _SmokeCase(EvenniaCommandTest):
    def setUp(self) -> None:
        super().setUp()
        for target in ("msg_room_identity", "apply_substance"):
            patcher = patch(f"commands.CmdSmoke.{target}")
            mocked = patcher.start()
            self.addCleanup(patcher.stop)
            if target == "apply_substance":
                mocked.return_value = {"feedback": ()}

    def cigarette(self, holder, hand: str, *, lit: bool = False,
                  uses_left: int = 6):
        cig = create_object("typeclasses.items.Item", key=_KEY,
                            location=holder)
        cig.aliases.add(_ALIAS)
        cig.tags.add(sm.SMOKE_DELIVERY, category=sm.DELIVERY_METHOD_CATEGORY)
        cig.db.substance = sm.SUBSTANCE_TOBACCO_NEUTRAL
        cig.db.uses_left = uses_left
        cig.db.max_uses = 6
        sm.set_lit(cig, lit)
        holder.wield_item(cig, hand=hand)
        self.assertIs(holder.hands[f"{hand}_hand"], cig)
        return cig

    def lighter(self, holder, hand: str):
        lig = create_object("typeclasses.items.Item", key="Zippo lighter",
                            location=holder)
        lig.tags.add(sm.LIGHTER_ROLE, category=sm.ITEM_ROLE_CATEGORY)
        holder.wield_item(lig, hand=hand)
        return lig


# ---------------------------------------------------------------------
# light <cigarette>
# ---------------------------------------------------------------------


class TestLightOwn(_SmokeCase):
    def setUp(self) -> None:
        super().setUp()
        self.lighter(self.char1, "right")
        self.cig = self.cigarette(self.char1, "left")

    def test_lights_by_key_word(self):
        self.call(CmdLight(), "cigarette", caller=self.char1)
        self.assertTrue(sm.is_lit(self.cig))

    def test_already_lit_is_refused(self):
        sm.set_lit(self.cig, True)
        out = self.call(CmdLight(), "cigarette", caller=self.char1)
        self.assertIn("already lit", out)

    def test_an_alias_that_is_not_part_of_the_key(self):
        self.call(CmdLight(), _ALIAS, caller=self.char1)
        self.assertTrue(sm.is_lit(self.cig))

    def test_a_mid_word_fragment_is_refused(self):
        """The control: this lit the cigarette before #3783."""
        out = self.call(CmdLight(), _FRAGMENT, caller=self.char1)
        self.assertIn(_NOT_HOLDING_OWN, out)
        self.assertFalse(sm.is_lit(self.cig))

    def test_the_lighter_is_not_a_smokable(self):
        out = self.call(CmdLight(), "zippo", caller=self.char1)
        self.assertIn(_NOT_HOLDING_OWN, out)

    def test_me_and_here_are_not_in_the_hand(self):
        for word in ("me", "self", "here"):
            out = self.call(CmdLight(), word, caller=self.char1)
            self.assertIn(_NOT_HOLDING_OWN, out)
        self.assertFalse(sm.is_lit(self.char1))
        self.assertFalse(sm.is_lit(self.room1))


# ---------------------------------------------------------------------
# light <person>'s <cigarette>
# ---------------------------------------------------------------------


class TestLightOther(_SmokeCase):
    """The pool is the target's hands; the caller does the searching.
    Identity resolution of the owner is patched: it is not this matcher."""

    def setUp(self) -> None:
        super().setUp()
        self.lighter(self.char1, "right")
        self.first = self.cigarette(self.char2, "left")
        self.second = self.cigarette(self.char2, "right")
        patcher = patch("commands.CmdSmoke.resolve_character_target",
                        return_value=self.char2)
        patcher.start()
        self.addCleanup(patcher.stop)
        # The name before it is the target's display name to the caller.
        self.not_holding = "isn't holding a cigarette matching that."

    def test_lights_the_targets_cigarette(self):
        """Twins without an ordinal: the first match (lowest id) is lit."""
        with patch.object(self.char2, "msg") as target_msg:
            self.call(CmdLight(), "bob's cigarette", caller=self.char1)
        self.assertTrue(sm.is_lit(self.first))
        self.assertFalse(sm.is_lit(self.second))
        told = " ".join(str(c.args[0]) for c in target_msg.call_args_list)
        self.assertIn("cigarette", told)

    def test_an_alias_that_is_not_part_of_the_key(self):
        self.call(CmdLight(), f"bob's {_ALIAS}", caller=self.char1)
        self.assertTrue(sm.is_lit(self.first))

    def test_an_ordinal_picks_the_second_twin(self):
        self.call(CmdLight(), "bob's 2nd cigarette", caller=self.char1)
        self.assertTrue(sm.is_lit(self.second))
        self.assertFalse(sm.is_lit(self.first))

    def test_a_mid_word_fragment_is_refused(self):
        out = self.call(CmdLight(), f"bob's {_FRAGMENT}", caller=self.char1)
        self.assertIn(self.not_holding, out)
        self.assertFalse(sm.is_lit(self.first) or sm.is_lit(self.second))

    def test_me_is_not_in_the_targets_hands(self):
        out = self.call(CmdLight(), "bob's me", caller=self.char1)
        self.assertIn(self.not_holding, out)
        self.assertFalse(sm.is_lit(self.char1))


# ---------------------------------------------------------------------
# smoke <cigarette>
# ---------------------------------------------------------------------


class TestSmoke(_SmokeCase):
    def not_holding(self, args: str) -> str:
        return f"You aren't holding a smokable matching '{args}'."

    def test_requires_lit(self):
        self.cigarette(self.char1, "left")
        out = self.call(CmdSmoke(), "cigarette", caller=self.char1)
        self.assertIn("isn't lit", out)

    def test_a_puff_decrements_uses_left(self):
        cig = self.cigarette(self.char1, "left", lit=True, uses_left=6)
        self.call(CmdSmoke(), "cigarette", caller=self.char1)
        self.assertEqual(cig.attributes.get("uses_left"), 5)
        self.assertTrue(cig.pk)

    def test_the_last_puff_destroys_it(self):
        cig = self.cigarette(self.char1, "left", lit=True, uses_left=1)
        out = self.call(CmdSmoke(), "cigarette", caller=self.char1)
        self.assertIsNone(cig.pk)
        self.assertTrue(any(w in out for w in ("spent", "burns down", "tumbles")),
                        out)

    def test_an_alias_that_is_not_part_of_the_key(self):
        cig = self.cigarette(self.char1, "left", lit=True)
        self.call(CmdSmoke(), _ALIAS, caller=self.char1)
        self.assertEqual(cig.attributes.get("uses_left"), 5)

    def test_an_ordinal_picks_the_second_twin(self):
        first = self.cigarette(self.char1, "left", lit=True)
        second = self.cigarette(self.char1, "right", lit=True)
        self.call(CmdSmoke(), "2nd cigarette", caller=self.char1)
        self.assertEqual(second.attributes.get("uses_left"), 5)
        self.assertEqual(first.attributes.get("uses_left"), 6)

    def test_a_mid_word_fragment_is_refused(self):
        cig = self.cigarette(self.char1, "left", lit=True)
        out = self.call(CmdSmoke(), _FRAGMENT, caller=self.char1)
        self.assertIn(self.not_holding(_FRAGMENT), out)
        self.assertEqual(cig.attributes.get("uses_left"), 6)

    def test_me_and_here_are_not_smoked(self):
        """`consume_use` deletes what it is handed; the caller and the room
        must never reach it."""
        self.cigarette(self.char1, "left", lit=True)
        for word in ("me", "self", "here"):
            out = self.call(CmdSmoke(), word, caller=self.char1)
            self.assertIn(self.not_holding(word), out)
        self.assertTrue(self.char1.pk)
        self.assertTrue(self.room1.pk)


# ---------------------------------------------------------------------
# snuff <cigarette>
# ---------------------------------------------------------------------


class TestSnuff(_SmokeCase):
    def not_holding(self, args: str) -> str:
        return f"You aren't holding a smokable matching '{args}'."

    def test_clears_lit_state(self):
        cig = self.cigarette(self.char1, "left", lit=True)
        self.call(CmdSnuff(), "cigarette", caller=self.char1)
        self.assertFalse(sm.is_lit(cig))

    def test_rejects_unlit(self):
        self.cigarette(self.char1, "left")
        out = self.call(CmdSnuff(), "cigarette", caller=self.char1)
        self.assertIn("isn't lit", out)

    def test_an_alias_that_is_not_part_of_the_key(self):
        cig = self.cigarette(self.char1, "left", lit=True)
        self.call(CmdSnuff(), _ALIAS, caller=self.char1)
        self.assertFalse(sm.is_lit(cig))

    def test_an_ordinal_picks_the_second_twin(self):
        first = self.cigarette(self.char1, "left", lit=True)
        second = self.cigarette(self.char1, "right", lit=True)
        self.call(CmdSnuff(), "second cigarette", caller=self.char1)
        self.assertFalse(sm.is_lit(second))
        self.assertTrue(sm.is_lit(first))

    def test_a_mid_word_fragment_is_refused(self):
        cig = self.cigarette(self.char1, "left", lit=True)
        out = self.call(CmdSnuff(), _FRAGMENT, caller=self.char1)
        self.assertIn(self.not_holding(_FRAGMENT), out)
        self.assertTrue(sm.is_lit(cig))
