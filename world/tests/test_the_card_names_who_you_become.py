"""The flash-clone card names who you will wake up as (#3364).

`archive_character` bumps death_count before the respawn menu renders, and
both doors then labelled the flash-clone option with the OUTGOING key. A
card reading "Jorge Jackson I" delivered "Jorge Jackson II" -- always one
numeral behind. Owner ruling 2026-09-13: the card says who you become.

One helper, `flash_clone_name`, feeds the telnet label, the web context and
`create_flash_clone` itself, so the promise and the result cannot drift.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands import charcreate

_flash_clone_name = getattr(charcreate, "flash_clone_name", None)


class _NDB:
    def __init__(self):
        self.charcreate_data = {}
        self.charcreate_old_character = None
        self.charcreate_is_respawn = True


class _Caller:
    def __init__(self):
        self.ndb = _NDB(); self.seen = []
    def msg(self, text=None, **kw):
        if text is not None: self.seen.append(text)


class CardNamesWhoYouBecomeTest(EvenniaTest):

    def _dead_sleeve(self, insured=True):
        # Jorge died once already (key "I"); archiving bumps death_count to 2.
        # Archived as a DEATH and, unless the test says otherwise, holding
        # his own policy: since #3667 the card is offered on no other body.
        old = create_object("typeclasses.characters.Character", key="Jorge Jackson I")
        old.death_count = 1
        old.archive_character(reason="death")           # death_count -> 2
        if insured:
            from world.insurance import restore_policy, void_policy
            restore_policy({"uid": old.sleeve_uid, "buyer_dbref": old.id,
                            "bought_at": 0, "buyer_key": old.key,
                            "blueprint_key": None, "account_id": None})
            self.addCleanup(void_policy, old.sleeve_uid)
        return old

    def test_helper_gives_the_incoming_name(self):
        if _flash_clone_name is None: self.skipTest("helper absent (unfixed tree)")
        self.assertEqual(_flash_clone_name(self._dead_sleeve()), "Jorge Jackson II")

    def test_telnet_card_names_the_incoming_sleeve(self):
        old = self._dead_sleeve()
        c = _Caller(); c.ndb.charcreate_old_character = old
        c.ndb.charcreate_data['templates'] = [charcreate.generate_random_template() for _ in range(3)]
        text, _ = charcreate.respawn_welcome(c, "")
        self.assertIn("[4]", text)
        self.assertIn("FLASH CLONE", text)
        self.assertIn("Jorge Jackson II", text, "card does not name who you become")
        self.assertNotIn("Jorge Jackson I|n", text, "card still names the outgoing sleeve")

    def test_an_uninsured_sleeve_gets_the_refusal_not_the_card(self):
        # Control for the gate (#3667): same body, no policy, no [4].
        from world.insurance import NO_POLICY
        old = self._dead_sleeve(insured=False)
        c = _Caller(); c.ndb.charcreate_old_character = old
        c.ndb.charcreate_data['templates'] = [charcreate.generate_random_template() for _ in range(3)]
        text, _ = charcreate.respawn_welcome(c, "")
        self.assertNotIn("[4]", text)
        self.assertIn(NO_POLICY, text)
        self.assertIn("Jorge Jackson II", text, "the refusal should still name who you would become")

    def test_label_and_result_agree(self):
        # Control for the whole point: what the card promises is what
        # create_flash_clone delivers.
        if _flash_clone_name is None: self.skipTest("helper absent (unfixed tree)")
        old = self._dead_sleeve()
        promised = _flash_clone_name(old)
        delivered = charcreate.build_name_from_death_count(old.key, old.death_count)
        self.assertEqual(promised, delivered)


    def test_create_flash_clone_runs_and_agrees_with_the_card(self):
        # Drive the REAL creator to completion (the label tests alone let a
        # NameError in create_flash_clone survive -- #3364 follow-up). The
        # decanted sleeve's key and its own death_count must match the card.
        old = self._dead_sleeve()   # key "Jorge Jackson I", death_count 2
        promised = charcreate.flash_clone_name(old)
        clone = charcreate.create_flash_clone(self.account, old)
        self.assertIsNotNone(clone, "create_flash_clone returned nothing")
        self.assertEqual(clone.key, promised, "clone key does not match the card")
        self.assertEqual(clone.key, "Jorge Jackson II")
        self.assertEqual(clone.death_count, 2,
                         "clone counter %r disagrees with its numeral" % clone.death_count)
