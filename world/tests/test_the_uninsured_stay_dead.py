"""The player gate (#3667, Slice C): a flash clone is paid by the dead
body's own policy or it does not happen, at both doors.

What is pinned here, each with a control that shows the opposite:

* `create_flash_clone` refuses an uninsured death, a shelved body, and a
  body still on the table; the record is taken BEFORE the body is built
  and put back when the build fails, with no half-built body left behind.
* A standing (perpetual) record is re-issued in the clone's name.
* The telnet menu refuses choice [4] at the goto-callable and the node's
  own refusal keeps the menu open (a bare string would close it).
* A fresh start after an insured death forfeits the dead body's record.
* `archive_character` finds the owning account without a live puppet, so
  `last_character` and the tombstone are written at a death the player
  was not online for.
* The web door renders the refusal instead of the card, the POST is told
  why, and a sleeve cannot be shelved twice or while dying.
* `@insure` grants, reads and revokes a standing policy.

Harness notes (see `reference_gelatinous_running_tests`): a room
broadcast never reaches a test observer; `Character.is_archived` is a
property; the Django test Client works against the game's URLconf.
"""
from unittest import mock

from django.test import Client
from django.urls import reverse
from django.utils.text import slugify
from evennia import create_object, create_script
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaCommandTest

from commands import charcreate
from commands.CmdInsure import CmdInsure
from world.insurance import (NO_POLICY, NOT_A_DEATH, STILL_ON_THE_TABLE,
                             PolicyRefused, _row_for, covers, flash_clone_refusal,
                             forfeit_policy, grant_perpetual, policy_for,
                             renew_perpetual, restore_policy, revoke_perpetual,
                             take_policy, void_policy)


class _Caller:
    """A telnet menu caller: the ndb the nodes read, the lines they send."""
    class _NDB:
        def __init__(self):
            self.charcreate_data = {}
    def __init__(self):
        self.ndb = _Caller._NDB(); self.seen = []
    def msg(self, text=None, **kw):
        if text is not None: self.seen.append(str(text))


class _Gate(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        # A body the account owns but is not puppeting: the shape of every
        # dead player character by the time the death path archives it.
        self.old = create_object("typeclasses.characters.Character",
                                 key="Jorge Jackson I", location=self.room1)
        self.account.characters.add(self.old)
        self.addCleanup(void_policy, self.old.sleeve_uid)

    def insure(self, body=None):
        body = body or self.old
        restore_policy({"uid": body.sleeve_uid, "buyer_dbref": body.id,
                        "bought_at": 0, "buyer_key": body.key,
                        "blueprint_key": None, "account_id": None})

    def die(self, body=None):
        (body or self.old).archive_character(reason="death")

    def clone(self):
        with mock.patch("commands.charcreate.get_start_location",
                        return_value=self.room2):
            return charcreate.create_flash_clone(self.account, self.old)

    def bodies_named(self, key):
        return ObjectDB.objects.filter(db_key=key).count()


class TheGate(_Gate):

    def test_control_an_insured_death_clones(self):
        self.insure(); self.die()
        clone = self.clone()
        self.assertEqual(clone.key, "Jorge Jackson II")
        self.assertEqual(clone.sleeve_uid, self.old.sleeve_uid)
        self.assertIsNone(policy_for(self.old.sleeve_uid), "the record was not spent")

    def test_no_policy_no_clone(self):
        self.die()
        before = len(self.account.characters.all())
        with self.assertRaises(PolicyRefused) as cm:
            self.clone()
        self.assertEqual(str(cm.exception), NO_POLICY)
        self.assertEqual(len(self.account.characters.all()), before)
        self.assertEqual(self.bodies_named("Jorge Jackson II"), 0)

    def test_a_shelved_body_is_not_a_death(self):
        self.insure()
        self.old.archive_character(reason="manual")
        with self.assertRaises(PolicyRefused) as cm:
            self.clone()
        self.assertEqual(str(cm.exception), NOT_A_DEATH)
        self.assertTrue(covers(self.old), "a refused shelve spent the record")

    def test_a_body_still_on_the_table_waits(self):
        self.insure(); self.die()
        create_script("evennia.scripts.scripts.DefaultScript",
                      key="death_progression", obj=self.old, autostart=False)
        with self.assertRaises(PolicyRefused) as cm:
            self.clone()
        self.assertEqual(str(cm.exception), STILL_ON_THE_TABLE)
        self.assertTrue(covers(self.old))

    def test_a_failed_create_puts_the_record_back(self):
        self.insure(); self.die()
        with mock.patch.object(type(self.account), "create_character",
                               return_value=(None, ["no vats free"])):
            with self.assertRaises(Exception):
                self.clone()
        self.assertTrue(covers(self.old), "the record was not restored")
        self.assertEqual(self.bodies_named("Jorge Jackson II"), 0)

    def test_a_failure_after_the_body_exists_removes_it(self):
        self.insure(); self.die()
        before = len(self.account.characters.all())
        with mock.patch("world.manifest.ensure_manifest",
                        side_effect=RuntimeError("manifest office closed")):
            with self.assertRaises(RuntimeError):
                self.clone()
        self.assertTrue(covers(self.old), "the record was not restored")
        self.assertEqual(self.bodies_named("Jorge Jackson II"), 0,
                         "a half-built body was left behind")
        self.assertEqual(len(self.account.characters.all()), before)

    def test_the_record_is_taken_before_the_body_is_built(self):
        # The one-record-one-body guarantee under two doors rests on the
        # ORDER: take, then build. Spy on the build and look at the store.
        self.insure(); self.die()
        seen = {}
        real = type(self.account).create_character
        def spy(*a, **k):
            seen["record_during_build"] = policy_for(self.old.sleeve_uid)
            return real(self.account, *a, **k)
        with mock.patch.object(type(self.account), "create_character", side_effect=spy):
            self.clone()
        self.assertIn("record_during_build", seen, "the build never ran")
        self.assertIsNone(seen["record_during_build"], "the body was built before the take")

    def test_a_door_that_passed_the_check_but_lost_the_race_is_refused(self):
        # Blind the pre-check: the record is gone, the check says fine.
        self.die()
        # (charcreate imports the name inside the function, so the module
        # attribute is the one place to blind it.)
        with mock.patch("world.insurance.flash_clone_refusal", return_value=None):
            with self.assertRaises(PolicyRefused) as cm:
                self.clone()
        self.assertEqual(str(cm.exception), NO_POLICY)
        self.assertEqual(self.bodies_named("Jorge Jackson II"), 0)

    def test_a_stale_read_cannot_take_a_reissued_record(self):
        # Door X read the row; door Y took it, built, and re-issued the
        # standing record under the SAME key for the clone. X's delete must
        # miss: it is a compare-and-delete on the row X read, not the key.
        grant_perpetual(self.old); self.die()
        stale_row, stale_rec = _row_for(self.old.sleeve_uid)
        clone = self.clone()                       # Y: take + build + renew
        self.assertTrue(covers(clone))
        with mock.patch("world.insurance._row_for", return_value=(stale_row, stale_rec)):
            self.assertIsNone(take_policy(self.old.sleeve_uid, self.old.id))
            self.assertFalse(forfeit_policy(self.old))
        self.assertTrue(covers(clone), "a stale door consumed the clone's standing record")

    def test_a_standing_record_follows_the_person_into_the_clone(self):
        grant_perpetual(self.old); self.die()
        clone = self.clone()
        self.assertTrue(covers(clone), "the clone is not covered")
        self.assertTrue(policy_for(clone.sleeve_uid)["perpetual"])
        self.assertFalse(covers(self.old))
        self.assertIsNone(take_policy(self.old.sleeve_uid, self.old.id),
                          "the dead body can still redeem")


class TheTelnetDoor(_Gate):

    def _caller(self):
        c = _Caller(); c.ndb.charcreate_old_character = self.old
        c.ndb.charcreate_data['templates'] = [charcreate.generate_random_template()
                                              for _ in range(3)]
        return c

    def test_choice_four_is_refused_where_the_menu_redisplays(self):
        self.die()
        c = self._caller()
        self.assertIsNone(charcreate._respawn_process_choice(c, "4"))
        self.assertTrue(any(NO_POLICY in line for line in c.seen), c.seen)

    def test_control_choice_four_routes_when_the_record_pays(self):
        self.insure(); self.die()
        c = self._caller()
        self.assertEqual(charcreate._respawn_process_choice(c, "4"),
                         "respawn_flash_clone")

    def test_the_doors_ignore_the_script_at_a_live_death(self):
        # At a live death the menu's first render happens while the
        # death_progression script is still attached; the card must show
        # and [4] must route. Only the gate inside create_flash_clone waits.
        self.insure(); self.die()
        create_script("evennia.scripts.scripts.DefaultScript",
                      key="death_progression", obj=self.old, autostart=False)
        self.assertIsNone(flash_clone_refusal(self.old))
        c = self._caller()
        text, _ = charcreate.respawn_welcome(c, "")
        self.assertIn("[4]", text)
        self.assertEqual(charcreate._respawn_process_choice(c, "4"), "respawn_flash_clone")

    def test_the_nodes_own_refusal_keeps_the_menu_open(self):
        # The web door and the telnet menu can both reach the function; if
        # the record is gone by the time the node runs, the node must show
        # the menu again, not return a bare string (which closes it).
        self.die()
        c = self._caller()
        ret = charcreate.respawn_flash_clone(c, "")
        self.assertIsInstance(ret, tuple, "the node closed the menu")
        text, options = ret
        self.assertIn("SLEEVE", text)
        self.assertTrue(options)
        self.assertTrue(any(NO_POLICY in line for line in c.seen), c.seen)

    def test_a_fresh_start_forfeits_the_dead_bodys_record(self):
        self.insure(); self.die()
        self.account.ndb.charcreate_old_character = self.old
        self.account.ndb.charcreate_data = {
            'selected_template': charcreate.generate_random_template()}
        self.addCleanup(charcreate._cleanup_charcreate_ndb, self.account)
        with mock.patch("commands.charcreate.get_start_location",
                        return_value=self.room2):
            charcreate.respawn_finalize_template(self.account, "")
        self.assertIsNone(policy_for(self.old.sleeve_uid), "the forfeit did not happen")

    def test_a_forfeit_takes_a_standing_record_too_but_not_anothers(self):
        grant_perpetual(self.old)
        self.assertTrue(forfeit_policy(self.old))
        self.assertIsNone(policy_for(self.old.sleeve_uid))
        # a record another body of the lineage holds is not this body's to forfeit
        twin = create_object("typeclasses.characters.Character", key="twin",
                             location=None)
        twin.sleeve_uid = self.old.sleeve_uid
        self.insure(twin)
        self.assertFalse(forfeit_policy(self.old))
        self.assertTrue(covers(twin))


class TheOwnerIsFoundWithoutAPuppet(_Gate):

    def test_a_death_the_player_was_offline_for_still_sets_last_character(self):
        from world.death_records import get_records
        from world.ownership import owning_account
        self.assertIsNone(self.old.account, "fixture: the body must not be puppeted")
        self.assertIs(owning_account(self.old), self.account)
        self.account.db.last_character = None
        self.die()
        self.assertEqual(self.account.db.last_character, self.old)
        self.assertEqual(len(get_records(self.account)), 1, "no tombstone was engraved")

    def test_control_a_body_nobody_owns_writes_nowhere(self):
        from world.ownership import owning_account
        stray = create_object("typeclasses.characters.Character", key="stray",
                              location=self.room1)
        self.assertIsNone(owning_account(stray))
        self.account.db.last_character = None
        stray.archive_character(reason="death")
        self.assertIsNone(self.account.db.last_character)


class TheWebDoor(_Gate):

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.account)

    def messages_of(self, response):
        return [str(m) for m in response.wsgi_request._messages]

    def test_the_card_gives_way_to_the_refusal(self):
        self.die()
        response = self.client.get(reverse('character-create'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn('id="flash_clone"', html)
        self.assertIn(NO_POLICY, html)
        self.assertIn("Jorge Jackson II", html)

    def test_control_an_insured_death_shows_the_card(self):
        self.insure(); self.die()
        html = self.client.get(reverse('character-create')).content.decode()
        self.assertIn('id="flash_clone"', html)
        self.assertNotIn(NO_POLICY, html)
        # The REAL template names who you become, not who you lost (#3364).
        self.assertIn("Jorge Jackson II", html)
        self.assertNotIn("Jorge Jackson I<", html)

    def test_the_post_is_told_why(self):
        self.die()
        response = self.client.post(reverse('character-create'),
                                    {'sleeve_choice': 'flash_clone'})
        self.assertEqual(response.status_code, 302)
        self.assertIn(NO_POLICY, self.messages_of(response))
        self.assertEqual(self.bodies_named("Jorge Jackson II"), 0)

    def test_a_template_pick_forfeits_the_record(self):
        self.insure(); self.die()
        self.client.get(reverse('character-create'))       # seeds the templates
        with mock.patch("commands.charcreate.get_start_location",
                        return_value=self.room2):
            response = self.client.post(reverse('character-create'),
                                        {'sleeve_choice': 'template_0'})
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(policy_for(self.old.sleeve_uid))


class TheShelf(_Gate):

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.account)

    def shelve(self, body):
        url = reverse('character-delete',
                      kwargs={'slug': slugify(body.name), 'pk': body.pk})
        return self.client.post(url)

    def messages_of(self, response):
        return [str(m) for m in response.wsgi_request._messages]

    def test_control_a_living_sleeve_is_shelved_and_told_the_truth(self):
        response = self.shelve(self.old)
        self.assertTrue(self.old.is_archived)
        self.assertEqual(self.old.db.archived_reason, "manual")
        self.assertEqual(self.account.db.last_character, self.old)
        text = " ".join(self.messages_of(response))
        self.assertIn("not a death", text)
        self.assertNotIn("preserved for future respawn", text)

    def test_a_dead_body_is_not_shelved_again(self):
        self.die()
        count, reason = self.old.death_count, self.old.db.archived_reason
        response = self.shelve(self.old)
        self.assertEqual(self.old.death_count, count)
        self.assertEqual(self.old.db.archived_reason, reason)
        self.assertIn("already shelved", " ".join(self.messages_of(response)))

    def test_a_dying_body_is_not_shelved(self):
        create_script("evennia.scripts.scripts.DefaultScript",
                      key="death_progression", obj=self.old, autostart=False)
        response = self.shelve(self.old)
        self.assertFalse(self.old.is_archived)
        self.assertIn("on the table", " ".join(self.messages_of(response)))


class TheStaffVerb(_Gate):

    def test_grant_read_revoke(self):
        out = self.call(CmdInsure(), "Jorge Jackson I", caller=self.char1) or ""
        self.assertIn("standing", out)
        self.assertTrue(covers(self.old))
        out = self.call(CmdInsure(), "/status Jorge Jackson I", caller=self.char1) or ""
        self.assertIn("standing", out)
        out = self.call(CmdInsure(), "/revoke Jorge Jackson I", caller=self.char1) or ""
        self.assertIn("revoked", out)
        self.assertFalse(covers(self.old))

    def test_a_shelved_body_cannot_be_granted(self):
        self.old.archive_character(reason="manual")
        out = self.call(CmdInsure(), "Jorge Jackson I", caller=self.char1) or ""
        self.assertIn("shelved", out)
        self.assertFalse(covers(self.old))

    def test_an_old_husk_cannot_take_the_living_clones_cover(self):
        grant_perpetual(self.old); self.die()
        clone = self.clone()                       # the record is the clone's now
        ok, msg = grant_perpetual(self.old, granted_by=self.char1)
        self.assertFalse(ok, msg)
        self.assertIn(clone.key, msg)
        self.assertTrue(covers(clone), "the grant stripped the living body's cover")
        ok, msg = revoke_perpetual(self.old)
        self.assertFalse(ok, msg)
        self.assertIn(clone.key, msg)
        self.assertTrue(covers(clone), "the revoke through the husk took the living body's cover")
        ok, _ = revoke_perpetual(clone)
        self.assertTrue(ok)
        self.assertFalse(covers(clone))

    def test_a_granted_dead_body_can_be_cloned_back(self):
        # The playtest use: died uninsured, staff grants, the player respawns.
        self.die()
        self.call(CmdInsure(), "Jorge Jackson I", caller=self.char1)
        clone = self.clone()
        self.assertTrue(covers(clone))
