"""Trust & consent gate (world/consent.py) — TRUST_AND_CONSENT_SPEC Phase 1.

Predicates, grant storage, the gate, and the command surface, on MagicMock
stand-ins (the LLM-test pattern) so no Evennia boot is needed for the pure
logic. The identity key is patched — uid derivation has its own suite.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.consent as consent
from world.consent import (
    ACTION_CLASSES, can_contest, check_consent, get_grants,
    grant_display_name, grant_trust, has_trust, is_conscious, is_restrained,
    revoke_trust, wipe_trust,
)


def _char(dead=False, unconscious=False, furniture=None):
    c = MagicMock()
    c.medical_state.is_dead = lambda: dead
    c.medical_state.is_unconscious = lambda: unconscious
    c.db.furniture = furniture
    c.ndb.combat_handler = None
    c.db.consent_grants = None
    c.recognition_memory = {}
    return c


class TestContestPredicate(TestCase):
    def test_awake_free_target_contests(self):
        self.assertTrue(can_contest(_char()))

    def test_dead_cannot_contest(self):
        self.assertFalse(can_contest(_char(dead=True)))

    def test_unconscious_cannot_contest(self):
        self.assertFalse(can_contest(_char(unconscious=True)))

    def test_no_medical_state_treated_as_conscious(self):
        # conservative polarity: only affirmative helplessness frees the
        # action (matches the old per-command gates)
        c = MagicMock()
        c.medical_state = None
        c.db.furniture = None
        c.ndb.combat_handler = None
        self.assertTrue(is_conscious(c))
        self.assertTrue(can_contest(c))

    def test_restraining_furniture_blocks_contest(self):
        pod = MagicMock()
        pod.db.restraining = True
        self.assertTrue(is_restrained(_char(furniture=pod)))
        self.assertFalse(can_contest(_char(furniture=pod)))

    def test_legacy_autodoc_counts_via_medical_lying_fallback(self):
        # live AutoDocs predate db.restraining — medical lie-in pod restrains
        pod = MagicMock()
        pod.db.restraining = False
        pod.db.is_medical = True
        pod.db.postures = ("lying",)
        self.assertTrue(is_restrained(_char(furniture=pod)))

    def test_ordinary_seat_does_not_restrain(self):
        stool = MagicMock()
        stool.db.restraining = False
        stool.db.is_medical = False
        stool.db.postures = ("sitting",)
        self.assertFalse(is_restrained(_char(furniture=stool)))

    def test_grapple_restrains(self):
        from world.combat.constants import DB_CHAR, DB_GRAPPLED_BY_DBREF
        c = _char()
        handler = MagicMock()
        handler.db.combatants = [{DB_CHAR: c, DB_GRAPPLED_BY_DBREF: "#42"}]
        c.ndb.combat_handler = handler
        self.assertTrue(is_restrained(c))
        self.assertFalse(can_contest(c))

    def test_in_combat_but_ungrappled_still_contests(self):
        from world.combat.constants import DB_CHAR, DB_GRAPPLED_BY_DBREF
        c = _char()
        handler = MagicMock()
        handler.db.combatants = [{DB_CHAR: c, DB_GRAPPLED_BY_DBREF: None}]
        c.ndb.combat_handler = handler
        self.assertFalse(is_restrained(c))


class TestGrants(TestCase):
    def _pair(self):
        grantor = _char()
        actor = MagicMock()
        actor.get_display_name = lambda looker=None, **k: "a lean man"
        return grantor, actor

    def test_grant_revoke_roundtrip(self):
        grantor, actor = self._pair()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            grant_trust(grantor, actor, "heal")
            self.assertTrue(has_trust(grantor, actor, "heal"))
            self.assertFalse(has_trust(grantor, actor, "dress"))
            revoke_trust(grantor, "uid-1", "heal")
            self.assertFalse(has_trust(grantor, actor, "heal"))

    def test_grant_all_is_blanket(self):
        grantor, actor = self._pair()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            classes = grant_trust(grantor, actor, "all")
        self.assertEqual(sorted(classes), sorted(ACTION_CLASSES))

    def test_grant_snapshots_label(self):
        grantor, actor = self._pair()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            grant_trust(grantor, actor, "dress")
        entry = get_grants(grantor)["uid-1"]
        self.assertEqual(entry["label"], "a lean man")

    def test_display_prefers_recognition_name(self):
        grantor, actor = self._pair()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            grant_trust(grantor, actor, "dress")
        grantor.recognition_memory = {"uid-1": {"assigned_name": "Roony"}}
        self.assertEqual(grant_display_name(grantor, "uid-1"), "Roony")
        grantor.recognition_memory = {}
        self.assertEqual(grant_display_name(grantor, "uid-1"), "a lean man")

    def test_revoking_last_class_drops_entry(self):
        grantor, actor = self._pair()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            grant_trust(grantor, actor, "heal")
        revoke_trust(grantor, "uid-1", "heal")
        self.assertEqual(get_grants(grantor), {})

    def test_wipe(self):
        grantor, actor = self._pair()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            grant_trust(grantor, actor, "all")
        self.assertEqual(wipe_trust(grantor), 1)
        self.assertEqual(get_grants(grantor), {})

    def test_identity_shift_lapses_trust(self):
        # the batman/bruce requirement: a new apparent uid stops matching
        grantor, actor = self._pair()
        with patch("world.identity.get_apparent_uid", return_value="uid-bat"):
            grant_trust(grantor, actor, "heal")
            self.assertTrue(has_trust(grantor, actor, "heal"))
        with patch("world.identity.get_apparent_uid",
                   return_value="uid-bruce"):
            self.assertFalse(has_trust(grantor, actor, "heal"))


class TestCheckConsent(TestCase):
    def test_self_action_always_allowed(self):
        c = _char()
        self.assertTrue(check_consent(c, c, "heal"))

    def test_helpless_target_is_free(self):
        actor = MagicMock()
        self.assertTrue(check_consent(actor, _char(unconscious=True), "heal"))
        self.assertTrue(check_consent(actor, _char(dead=True), "dress"))

    def test_conscious_stranger_blocked(self):
        actor = MagicMock()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            self.assertFalse(check_consent(actor, _char(), "dress"))

    def test_trust_opens_the_conscious_path(self):
        actor = MagicMock()
        actor.get_display_name = lambda looker=None, **k: "a medic"
        target = _char()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            grant_trust(target, actor, "heal")
            self.assertTrue(check_consent(actor, target, "heal"))
            self.assertFalse(check_consent(actor, target, "dress"))


class TestClothingGate(TestCase):
    def test_appendage_always_dressable(self):
        from commands.CmdClothing import _can_third_party_clothing
        from typeclasses.items import Appendage
        limb = MagicMock(spec=Appendage)
        self.assertTrue(_can_third_party_clothing(MagicMock(), limb))

    def test_character_rides_consent_gate(self):
        from commands.CmdClothing import _can_third_party_clothing
        caller = MagicMock()
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            self.assertFalse(_can_third_party_clothing(caller, _char()))
            self.assertTrue(
                _can_third_party_clothing(caller, _char(unconscious=True)))


class TestTrustCommand(TestCase):
    def _cmd(self, args, grants=None):
        from commands.CmdTrust import CmdTrust
        cmd = CmdTrust()
        cmd.caller = _char()
        if grants is not None:
            cmd.caller.db.consent_grants = grants
        cmd.args = args
        return cmd

    def test_grant_via_command(self):
        cmd = self._cmd("lean man to dress")
        target = MagicMock()
        target.get_display_name = lambda looker=None, **k: "a lean man"
        cmd.caller.search.return_value = target
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            cmd.func()
        entry = get_grants(cmd.caller)["uid-1"]
        self.assertEqual(entry["classes"], ["dress"])
        self.assertIn("You now trust a lean man to dress",
                      cmd.caller.msg.call_args.args[0])

    def test_unknown_class_refused(self):
        cmd = self._cmd("lean man to tickle")
        cmd.func()
        self.assertIn("isn't a trustable action",
                      cmd.caller.msg.call_args.args[0])
        cmd.caller.search.assert_not_called()

    def test_bare_trust_lists(self):
        grants = {"uid-1": {"classes": ["heal"], "label": "a lean man"}}
        cmd = self._cmd("", grants=grants)
        cmd.func()
        out = cmd.caller.msg.call_args.args[0]
        self.assertIn("a lean man — heal", out)

    def test_trust_no_one_wipes(self):
        grants = {"uid-1": {"classes": ["heal"], "label": "a lean man"}}
        cmd = self._cmd("no one", grants=grants)
        cmd.func()
        self.assertEqual(get_grants(cmd.caller), {})

    def test_cannot_trust_self(self):
        cmd = self._cmd("me to heal")
        cmd.caller.search.return_value = cmd.caller
        cmd.func()
        self.assertIn("don't need to trust yourself",
                      cmd.caller.msg.call_args.args[0])
        self.assertEqual(get_grants(cmd.caller), {})


class TestDistrustCommand(TestCase):
    def _cmd(self, args, grants=None):
        from commands.CmdTrust import CmdDistrust
        cmd = CmdDistrust()
        cmd.caller = _char()
        cmd.caller.db.consent_grants = grants or {}
        cmd.args = args
        return cmd

    def test_revoke_by_remembered_label_absent_person(self):
        grants = {"uid-1": {"classes": ["heal", "dress"],
                            "label": "a lean man"}}
        cmd = self._cmd("lean man to heal", grants=grants)
        cmd.func()
        self.assertEqual(get_grants(cmd.caller)["uid-1"]["classes"],
                         ["dress"])

    def test_revoke_everything_from_person(self):
        grants = {"uid-1": {"classes": ["heal"], "label": "a lean man"}}
        cmd = self._cmd("lean man", grants=grants)
        cmd.func()
        self.assertEqual(get_grants(cmd.caller), {})

    def test_distrust_all(self):
        grants = {"uid-1": {"classes": ["heal"], "label": "a"},
                  "uid-2": {"classes": ["dress"], "label": "b"}}
        cmd = self._cmd("all", grants=grants)
        cmd.func()
        self.assertEqual(get_grants(cmd.caller), {})

    def test_unknown_person_messaged(self):
        cmd = self._cmd("stranger")
        cmd.func()
        self.assertIn("don't have any trust extended",
                      cmd.caller.msg.call_args.args[0])


class TestFriskGate(TestCase):
    """Phase 2: frisk rides the `search` class (spec §3.2) — free on the
    helpless, trust-gated on the conscious, corpse objects always loot."""

    _ROOM = None

    def _cmd(self, target):
        from commands.CmdInventory import CmdFrisk
        room = MagicMock()
        room.contents = []
        type(self)._ROOM = room
        target.location = room
        cmd = CmdFrisk()
        cmd.caller = MagicMock()
        cmd.caller.location = room
        cmd.caller.search.return_value = target
        cmd.args = "someone"
        return cmd

    def _target(self, **kwargs):
        t = _char(**kwargs)
        t.contents = []
        t.db.tokens = None
        t.typeclass_path = "typeclasses.characters.Character"
        t.__class__.__name__ = "MagicMock"
        return t

    def test_conscious_stranger_refused(self):
        target = self._target()
        cmd = self._cmd(target)
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            cmd.func()
        self.assertIn("would resist being searched",
                      cmd.caller.msg.call_args.args[0])

    def test_conscious_with_search_trust_allowed(self):
        from world.consent import grant_trust
        target = self._target()
        cmd = self._cmd(target)
        cmd.caller.get_display_name = lambda looker=None, **k: "a guard"
        with patch("world.identity.get_apparent_uid", return_value="uid-1"), \
                patch("world.identity.get_apparent_gender",
                      return_value="female"):
            grant_trust(target, cmd.caller, "search")
            cmd.func()
        out = " ".join(str(c.args[0]) for c in cmd.caller.msg.call_args_list)
        self.assertIn("patting", out)          # the frisk proceeded
        self.assertNotIn("would resist", out)

    def test_unconscious_target_free(self):
        target = self._target(unconscious=True)
        cmd = self._cmd(target)
        with patch("world.identity.get_apparent_gender",
                   return_value="male"):
            cmd.func()
        out = " ".join(str(c.args[0]) for c in cmd.caller.msg.call_args_list)
        self.assertIn("patting", out)


class TestFriskManifest(TestCase):
    def _run(self, target):
        from commands.CmdInventory import CmdFrisk
        cmd = CmdFrisk()
        caller = MagicMock()
        cmd._show_frisk_results(caller, target, list(target.contents),
                                "them", "a lean man")
        return caller.msg.call_args.args[0]

    def _item(self, name):
        item = MagicMock()
        item.get_display_name = lambda looker=None, **k: name
        item.db.worn = None
        item.db.wear_location = None
        item.worn = None
        return item

    def test_worn_hand_carried_and_tokens_sections(self):
        jacket, shiv, pack = (self._item("a cropped jacket"),
                              self._item("a shiv"),
                              self._item("a pack of cigarettes"))
        target = MagicMock()
        target.contents = [jacket, shiv, pack]
        target.get_worn_items = lambda: [jacket]
        target.hands = {"left": shiv, "right": None}
        target.db.tokens = 240
        out = self._run(target)
        self.assertIn("a cropped jacket", out)
        self.assertIn("(worn)", out)
        self.assertIn("a shiv", out)
        self.assertIn("(in hand)", out)
        self.assertIn("a pack of cigarettes", out)
        self.assertIn("240 tokens", out)

    def test_two_handed_grip_lists_once(self):
        crowbar = self._item("a crowbar")
        target = MagicMock()
        target.contents = [crowbar]
        target.get_worn_items = lambda: []
        target.hands = {"left": crowbar, "right": crowbar}
        target.db.tokens = None
        out = self._run(target)
        self.assertEqual(out.count("a crowbar"), 1)

    def test_tokens_only_target_still_reveals(self):
        target = MagicMock()
        target.contents = []
        target.get_worn_items = lambda: []
        target.hands = {}
        target.db.tokens = 120
        out = self._run(target)
        self.assertIn("120 tokens", out)
