"""`trust <x> to grab` makes a grapple a hold, not a fight (#3363).

`grab` sat in ACTION_CLASSES and the `trust` help as one of five action
classes, and no code path consulted it -- granting it gave nothing away,
withholding it protected nothing. TRUST_AND_CONSENT_SPEC §3 defined it
as "consensual restraint: let them grab/restrain you uncontested".

Owner ruling 2026-09-13: grapple doubles as holding someone; the
difference from an attack is whether anyone chose violence. A trusted
grab (or a target who cannot contest -- the consent free path) is held
uncontested: no roll, both yielding, no retaliation target. Untrusted
is the contested grapple, unchanged.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat import grappling
from world.combat.constants import (DB_CHAR, DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF,
                                    DB_IS_YIELDING, DB_TARGET_DBREF)
from world.combat.handler import get_or_create_combat
from world.combat.utils import add_combatant, get_character_dbref
from world.consent import grant_trust


class TrustedGrabIsAHoldTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.holder = create_object("typeclasses.characters.Character", key="Holder", location=self.room1)
        self.held = create_object("typeclasses.characters.Character", key="Held", location=self.room1)
        self.handler = get_or_create_combat(self.room1)
        add_combatant(self.handler, self.holder, target=self.held)
        add_combatant(self.handler, self.held, target=None)

    def _entries(self):
        lst = self.handler.db.combatants
        h = next(e for e in lst if e.get(DB_CHAR) == self.holder)
        v = next(e for e in lst if e.get(DB_CHAR) == self.held)
        return lst, h, v

    def _initiate(self, rolls):
        # rolls: (attacker, defender) forced -- proves whether a contest happened.
        lst, h, v = self._entries()
        with mock.patch("random.randint", side_effect=list(rolls) * 4):
            grappling.resolve_grapple_initiate(h, lst, self.handler)
        self.handler.db.combatants = lst
        return self._entries()

    # --- the defect: trust made no difference ---------------------------

    def test_trusted_grab_holds_without_a_contest(self):
        grant_trust(self.held, self.holder, "grab")
        _, h, v = self._initiate(rolls=(1, 100))        # a LOSING roll -- must not matter
        self.assertEqual(h.get(DB_GRAPPLING_DBREF), get_character_dbref(self.held), "trusted grab did not hold")
        self.assertEqual(v.get(DB_GRAPPLED_BY_DBREF), get_character_dbref(self.holder))

    def test_trusted_hold_leaves_both_yielding_and_sets_no_retaliation_target(self):
        grant_trust(self.held, self.holder, "grab")
        _, h, v = self._initiate(rolls=(1, 100))
        self.assertTrue(h.get(DB_IS_YIELDING), "holder is not yielding")
        self.assertTrue(v.get(DB_IS_YIELDING), "held person would auto-struggle against a hold they allowed")
        self.assertIsNone(v.get(DB_TARGET_DBREF), "held person was pointed at their holder as a retaliation target")

    def test_uncontestable_target_is_held_uncontested(self):
        # The consent free path: unconscious / restrained cannot contest.
        with mock.patch("world.consent.can_contest", return_value=False):
            _, h, v = self._initiate(rolls=(1, 100))
        self.assertEqual(h.get(DB_GRAPPLING_DBREF), get_character_dbref(self.held))

    # --- controls: untrusted is the contested grapple, unchanged ---------

    def test_untrusted_grab_is_contested_and_can_fail(self):
        _, h, v = self._initiate(rolls=(1, 100))        # losing roll -> no hold
        self.assertIsNone(h.get(DB_GRAPPLING_DBREF), "untrusted grab succeeded despite losing the roll")

    def test_untrusted_grab_that_wins_is_a_fight(self):
        _, h, v = self._initiate(rolls=(100, 1))        # winning roll -> hostile hold
        self.assertEqual(h.get(DB_GRAPPLING_DBREF), get_character_dbref(self.held))
        self.assertFalse(v.get(DB_IS_YIELDING), "hostile victim must stay non-yielding to auto-resist")
        self.assertEqual(v.get(DB_TARGET_DBREF), get_character_dbref(self.holder))

    def test_trust_for_another_class_does_not_count(self):
        grant_trust(self.held, self.holder, "heal")
        _, h, v = self._initiate(rolls=(1, 100))
        self.assertIsNone(h.get(DB_GRAPPLING_DBREF), "a 'heal' grant was read as 'grab'")
