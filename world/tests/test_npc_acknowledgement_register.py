"""An NPC acknowledges in its own register, not Sully's (#2584).

`_acknowledge` lives on `LLMNpcMixin` -- every LLM NPC in the colony
reaches it -- and imported `ACK_EMOTES` straight from `world/bar.py`.
That set was written for one taciturn male bartender: one entry hard-coded
`his`, and four of five reached for bar furniture (*the taps*, *the slab*
twice, *wiping down a glass*).

Live census when the issue was filed: **78 LLM NPCs, 40 female, 30 male,
8 ambiguous**. So 48 were misgendered on a 1-in-5 roll, and all 78 could
answer you by knocking on a bar slab that was not there -- a ripper in a
cold room, a noodle vendor at a cart, a secbot on patrol.

The register is now selected by the POST, not by a flag on the body:
`tender_at` naming this NPC is what earns the bar's set. That follows
#2378, which exists to remove role flags from bodies -- and `world/bar.py`
itself records that `is_bartender_npc` was already rejected once for
exactly that reason, so this deliberately does not resurrect it.

`test_bar_register_still_reaches_for_the_taps` is the control: it fails if
a fix "solved" the furniture problem by flattening Sully's voice into the
generic one everywhere.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.llm_npc import LLMNpcMixin
from world import bar as bar_mod

# Bound defensively -- an absent name must surface as a named failure here
# rather than an ImportError that takes every control in this file with it.
BAR_ACK_EMOTES = getattr(bar_mod, "BAR_ACK_EMOTES", None)
GENERIC = getattr(LLMNpcMixin, "ACK_EMOTES", None)

GENDERED = ("his", "her", "hers", "him", "she", "he", "himself", "herself")
BAR_FURNITURE = ("tap", "slab", "glass", "bottle", "pour")


def _words(text):
    return set("".join(c.lower() if c.isalpha() else " " for c in text).split())


class AckRegisterTest(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc",
                                 key="a ripper", location=self.room1)

    def _ack(self, npc=None):
        """Call the selector, reporting its absence as a named failure.

        Without this an unfixed tree raises AttributeError, and an ERROR
        says "this test is broken" where a FAILURE says "the code is".
        """
        npc = npc or self.npc
        self.assertTrue(hasattr(npc, "_ack_emotes"),
                        "LLMNpcMixin._ack_emotes is missing -- nothing "
                        "selects an acknowledgement register")
        return tuple(npc._ack_emotes())

    # --- harness control -------------------------------------------------

    def test_fixture_npc_is_real(self):
        # Passes on the FIXED and the UNFIXED tree alike. That is the point:
        # if every assertion in this file failed, this one proves the cause
        # is the defect and not a fixture that never built an NPC.
        self.assertIsNotNone(self.npc.pk)
        self.assertIsInstance(self.npc, LLMNpcMixin)
        self.assertTrue(callable(getattr(self.npc, "_acknowledge", None)))
        self.assertIs(self.npc.location, self.room1)

    # --- the generic register -------------------------------------------

    def test_generic_register_exists(self):
        self.assertIsNotNone(
            GENERIC, "LLMNpcMixin.ACK_EMOTES is missing -- the generic "
                     "acknowledgement register every non-bar NPC needs")

    def test_generic_register_is_ungendered(self):
        self.assertIsNotNone(GENERIC, "LLMNpcMixin.ACK_EMOTES missing")
        for line in GENERIC:
            leaked = _words(line) & set(GENDERED)
            self.assertFalse(
                leaked, f"gendered pronoun {leaked} in a set fired for all "
                        f"78 NPCs, 48 of whom are not male: {line!r}")

    def test_generic_register_assumes_no_furniture(self):
        self.assertIsNotNone(GENERIC, "LLMNpcMixin.ACK_EMOTES missing")
        for line in GENERIC:
            low = line.lower()
            hit = [f for f in BAR_FURNITURE if f in low]
            self.assertFalse(
                hit, f"bar furniture {hit} in the set a ripper in a cold "
                     f"room also fires: {line!r}")

    def test_npc_away_from_a_counter_uses_the_generic_register(self):
        self.assertEqual(self._ack(), tuple(GENERIC))

    # --- the bar register ------------------------------------------------

    def test_bar_register_still_reaches_for_the_taps(self):
        # Control: Sully's voice must SURVIVE the rescoping. If this fails,
        # the furniture problem was "fixed" by deleting the flavour.
        self.assertIsNotNone(BAR_ACK_EMOTES, "world.bar.BAR_ACK_EMOTES missing")
        joined = " ".join(BAR_ACK_EMOTES).lower()
        self.assertTrue(any(f in joined for f in BAR_FURNITURE),
                        "the bar register lost its own furniture")

    def test_bar_register_is_also_ungendered(self):
        # Bartenders are not all male either -- the post is not a gender.
        self.assertIsNotNone(BAR_ACK_EMOTES, "world.bar.BAR_ACK_EMOTES missing")
        for line in BAR_ACK_EMOTES:
            leaked = _words(line) & set(GENDERED)
            self.assertFalse(leaked, f"gendered pronoun {leaked}: {line!r}")

    def test_the_npc_tending_a_counter_gets_the_bar_register(self):
        counter = create_object("typeclasses.bar.BarCounter",
                                key="the slab", location=self.room1)
        # Scoped by the POST answering with this NPC, which is the whole
        # point -- not by a flag on the body (#2378).
        with patch.object(bar_mod, "tender_at",
                          side_effect=lambda f: self.npc if f is counter else None):
            self.assertEqual(self._ack(), tuple(BAR_ACK_EMOTES))

    def test_a_bystander_at_the_bar_does_not_get_the_bar_register(self):
        # Standing in a bar is not tending it.
        counter = create_object("typeclasses.bar.BarCounter",
                                key="the slab", location=self.room1)
        other = create_object("typeclasses.llm_npc.LLMNpc",
                              key="a drinker", location=self.room1)
        with patch.object(bar_mod, "tender_at",
                          side_effect=lambda f: other if f is counter else None):
            self.assertEqual(self._ack(), tuple(GENERIC))

    # --- per-NPC content override ---------------------------------------

    def test_db_override_wins(self):
        self.npc.db.ack_emotes = ("clicks a mandible once.",)
        self.assertEqual(self._ack(), ("clicks a mandible once.",))
