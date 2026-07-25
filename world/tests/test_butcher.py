"""The Butcher gig (GIG_PROTOTYPE_BUTCHER_SPEC): the deterministic
buy → break-down → pay transaction, condition-gated yields, species guard,
and the butcher archetype's tool scoping.

Methods bound to MagicMock stand-ins (the test_llm_npc pattern) with a fake
medical snapshot — no Evennia boot for the yield logic; routing tests patch
delay/create_object at the module seam.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import typeclasses.butcher as butchmod
from typeclasses.butcher import (
    ACCEPTED_BUTCHER_SPECIES, BUTCHER_DECAY_REFUSAL, RAT_PRODUCTS,
)


def _organ(container, hp=10, max_hp=10):
    return {"current_hp": hp, "max_hp": max_hp, "data": {"container": container}}


def _rat_snapshot(**overrides):
    """A full healthy rat snapshot; override per-organ to model damage."""
    organs = {
        "tail_vertebrae": _organ("tail"),
        "heart": _organ("chest"), "left_lung": _organ("chest"),
        "right_lung": _organ("chest"), "liver": _organ("abdomen"),
        "stomach": _organ("abdomen"), "left_kidney": _organ("abdomen"),
        "right_kidney": _organ("abdomen"),
        "left_hindleg_bone": _organ("left_hindleg"),
        "right_hindleg_bone": _organ("right_hindleg"),
        "brain": _organ("head"),
    }
    organs.update(overrides)
    return {"organs": organs}


def _corpse(snapshot=None, species="rat", severed=(), removed=(), decay=0.0):
    c = MagicMock()
    c.pk = 1
    c.db.species = species
    c.db.severed_locations = list(severed)
    c.db.removed_organs = list(removed)
    c.get_medical_snapshot = lambda: snapshot
    c.get_decay_factor = lambda: decay
    return c


def _butcher():
    b = MagicMock()
    b.location = "room"
    for name in ("_butcher_yields", "_process_corpse", "_refuse",
                 "_drop_from_hands"):
        setattr(b, name,
                getattr(butchmod.Butcher, name).__get__(b, butchmod.Butcher))
    # staticmethods: already plain functions off the class — do NOT re-bind
    # (a __get__ would inject a spurious self argument)
    b._refusal_line = butchmod.Butcher._refusal_line
    b._render_cuts = butchmod.Butcher._render_cuts
    b.hands = {}
    return b


class TestButcherYields(TestCase):
    """The condition-gated butchery table."""

    def _yields(self, corpse, decay=0.0):
        return dict(_butcher()._butcher_yields(corpse, decay))

    def test_clean_fresh_rat_full_cuts(self):
        y = self._yields(_corpse(_rat_snapshot()))
        self.assertEqual(y["rat tail"], 1)
        self.assertEqual(y["rat chops"], 3)
        self.assertEqual(y["rat haunch"], 2)
        self.assertEqual(y["rat offal"], 1)
        self.assertEqual(y["ground mystery meat"], 3)

    def test_severed_tail_no_tail(self):
        y = self._yields(_corpse(_rat_snapshot(), severed=["tail"]))
        self.assertNotIn("rat tail", y)

    def test_shredded_trunk_no_chops(self):
        snap = _rat_snapshot(
            heart=_organ("chest", hp=0), left_lung=_organ("chest", hp=0),
            right_lung=_organ("chest", hp=0), liver=_organ("abdomen", hp=0),
            stomach=_organ("abdomen", hp=0), left_kidney=_organ("abdomen", hp=0),
            right_kidney=_organ("abdomen", hp=0))
        y = self._yields(_corpse(snap))
        self.assertNotIn("rat chops", y)
        self.assertNotIn("rat offal", y)   # shredded organs are no delicacy
        self.assertEqual(y["rat haunch"], 2)  # legs untouched

    def test_harvested_organs_no_offal(self):
        y = self._yields(_corpse(_rat_snapshot(),
                                 removed=["heart", "liver", "left_kidney"]))
        self.assertNotIn("rat offal", y)

    def test_decay_scales_meat_mass(self):
        fresh = self._yields(_corpse(_rat_snapshot()), decay=0.0)
        stale = self._yields(_corpse(_rat_snapshot()), decay=0.5)
        self.assertLess(stale["rat chops"], fresh["rat chops"])
        self.assertGreaterEqual(stale["ground mystery meat"], 1)

    def test_empty_snapshot_still_minces_something(self):
        y = self._yields(_corpse(None))
        self.assertEqual(list(y), ["ground mystery meat"])


class TestProcessCorpse(TestCase):
    """Guards + the transaction: species, decay, till, pay, destroy."""

    def _run(self, corpse, till=500):
        b = _butcher()
        block = MagicMock()
        block.db.register = till
        b._find_block = lambda: block
        giver = MagicMock()
        giver.pk = 1
        giver.tokens = 0
        with patch.object(butchmod, "create_object") as co:
            co.return_value = MagicMock()
            b._process_corpse(corpse, giver)
        return b, block, giver

    def test_human_corpse_refused_not_destroyed(self):
        corpse = _corpse(_rat_snapshot(), species="human")
        b, block, giver = self._run(corpse)
        corpse.delete.assert_not_called()
        corpse.move_to.assert_called()          # handed back to the floor
        self.assertEqual(giver.tokens, 0)
        say = b.execute_cmd.call_args.args[0]
        self.assertIn("say I don't grind people", say)

    def test_robot_corpse_refused(self):
        corpse = _corpse(_rat_snapshot(), species="robot")
        b, _, _ = self._run(corpse)
        corpse.delete.assert_not_called()
        self.assertIn("chrome and coolant", b.execute_cmd.call_args.args[0])

    def test_rotted_corpse_refused(self):
        corpse = _corpse(_rat_snapshot(), decay=BUTCHER_DECAY_REFUSAL + 0.1)
        b, _, giver = self._run(corpse)
        corpse.delete.assert_not_called()
        self.assertEqual(giver.tokens, 0)

    def test_dry_till_refuses_before_grinding(self):
        corpse = _corpse(_rat_snapshot())
        b, block, giver = self._run(corpse, till=2)
        corpse.delete.assert_not_called()
        self.assertEqual(block.db.register, 2)
        self.assertIn("Till's dry", b.execute_cmd.call_args.args[0])

    def test_clean_rat_pays_and_destroys(self):
        corpse = _corpse(_rat_snapshot())
        b, block, giver = self._run(corpse, till=500)
        corpse.delete.assert_called_once()
        # tail5 + 3 chops*3 + 2 haunch*3 + offal3 + 3 meat*1 = 26
        self.assertEqual(giver.tokens, 26)
        self.assertEqual(block.db.register, 500 - 26)
        emote = b.execute_cmd.call_args.args[0]
        self.assertTrue(emote.startswith("emote breaks the carcass down"))
        self.assertIn("counts 26 across the steel", emote)

    def test_payout_capped_by_till(self):
        corpse = _corpse(_rat_snapshot())
        b, block, giver = self._run(corpse, till=10)
        self.assertEqual(giver.tokens, 10)
        self.assertEqual(block.db.register, 0)


class TestButcherArchetype(TestCase):
    """Tool scoping + the few-shot demonstrates the memory tools
    (tuning lesson: a 12B copies the few-shot, not the tool prose)."""

    def test_registered_and_scoped(self):
        from world.llm.prompt import ARCHETYPES, tool_names
        self.assertIn("butcher", ARCHETYPES)
        persona = {"persona_seed": {"archetype": "butcher"}}
        self.assertEqual(tool_names(persona),
                         ["look", "remember", "feel", "release"])

    def test_fewshot_demonstrates_memory_tools(self):
        from world.llm.prompt import ARCHETYPES
        tools = [e["assistant"]["tool"]
                 for e in ARCHETYPES["butcher"]["fewshot"]]
        self.assertIn("remember", tools)
        self.assertIn("feel", tools)
        self.assertEqual(tools[-1], "none")   # ends on restraint

    def test_duties_draw_the_ripper_line(self):
        from world.llm.prompt import ARCHETYPES
        duties = ARCHETYPES["butcher"]["duties"]
        self.assertIn("ripper", duties.lower())
        self.assertIn("chrome isn't food", duties)


class TestRatAccepted(TestCase):
    def test_species_set(self):
        self.assertIn("rat", ACCEPTED_BUTCHER_SPECIES)
        for banned in ("human", "synthetic_humanoid", "robot"):
            self.assertNotIn(banned, ACCEPTED_BUTCHER_SPECIES)

    def test_products_have_flavour(self):
        for key, spec in RAT_PRODUCTS.items():
            self.assertTrue(spec["desc"]), key
            self.assertTrue(spec["taste"]), key
            self.assertGreater(spec["value"], 0)
