"""A beheading is a death, not a dying (#3835, and the beheading half
of #330).

Owner, 2026-11-14: "A body without a head is hard to identify", and
then, asked what a headless body should be called while it is still
dying: "is someone really dying if there head is missing? They should
be a corpse."

Two things were wrong.

* A beheaded body stayed a character for the whole death window, with
  the revival check and the dying messages of somebody who might yet
  be saved, and the corpse was built at the end of it.
* For as long as it was a character it was NAMED like any living
  person. What is worn on the head leaves with the head, so the
  headless body of a masked person presented their bare look: somebody
  who knew the face and could not tell who the masked figure was read
  the name off the body.

Built through the game's own doors: `spawn_severed_head_for_living`,
the death-progression script, the corpse factory.
"""
import inspect
from types import SimpleNamespace
from unittest import mock

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from typeclasses import death_progression
from typeclasses.characters import Character
from typeclasses.corpse import Corpse
from typeclasses.curtain_of_death import DeathCurtain
from typeclasses.items import spawn_severed_head_for_living
from world import identity
from world.identity import get_apparent_uid
from world.search import is_identity_match


def _fixed(name):
    """A function the fix adds, fetched late so this module still LOADS
    against the unfixed tree: a loader error is not evidence."""
    for module in (identity, death_progression):
        if hasattr(module, name):
            return getattr(module, name)
    raise AssertionError(f"{name} does not exist: the fix is not here")


class _TheBlow(EvenniaTest):
    """Somebody about to lose their head, a friend who knows the bare
    face as Jorge, and somebody who only knows the masked figure, as
    Ghost. Both stand in another room and watch nothing (#3811)."""

    def setUp(self):
        super().setUp()
        self.dead = self.body("Jorvik Ansel", "sleeve-dead", self.room1)
        self.mask = spawn("SKI_MASK")[0]
        self.mask.location = self.dead
        self.bare_look = get_apparent_uid(self.dead)
        ok, why = self.dead.wear_item(self.mask)
        self.assertTrue(ok, why)
        self.masked_look = get_apparent_uid(self.dead)
        ok, why = self.dead.remove_item(self.mask)
        self.assertTrue(ok, why)
        self.friend = self.body("Petra Lund", "sleeve-friend", self.room2)
        self.friend.recognition_memory = {
            self.bare_look: {"assigned_name": "Jorge"}}
        self.other = self.body("Odile Marsh", "sleeve-other", self.room2)
        self.other.recognition_memory = {
            self.masked_look: {"assigned_name": "Ghost"}}

    def body(self, key, sleeve, room):
        char = create_object(Character, key=key, location=room)
        char.sleeve_uid = sleeve
        char.height, char.build, char.sdesc_keyword = "short", "lean", "man"
        char.recognition_memory = {}
        return char

    def behead(self, masked=False):
        if masked:
            ok, why = self.dead.wear_item(self.mask)
            self.assertTrue(ok, why)
        head = spawn_severed_head_for_living(self.dead, injury_type="cut")
        self.assertIsNotNone(head)
        return head

    def corpses(self):
        return [o for o in self.room1.contents if isinstance(o, Corpse)]


class TestABodyWithItsHeadOffNamesNobody(_TheBlow):

    def test_before_the_blow_the_friend_is_shown_the_name(self):
        """The control."""
        self.assertEqual(self.dead.get_display_name(self.friend), "Jorge")
        self.assertTrue(is_identity_match(self.friend, self.dead, "jorge"))

    def test_the_line_that_takes_the_head_off_still_names_them(self):
        """Combat sets `decapitation_pending` and tells the room BEFORE
        the head exists as its own object. The face is still there."""
        self.dead.db.decapitation_pending = True
        self.assertEqual(self.dead.get_display_name(self.friend), "Jorge")

    def test_after_the_blow_the_friend_is_shown_no_name(self):
        self.behead()
        shown = self.dead.get_display_name(self.friend)
        self.assertNotIn("Jorge", shown)
        self.assertNotIn("Jorvik", shown)
        self.assertIn("man", shown)

    def test_the_name_cannot_be_typed_and_the_description_can(self):
        self.behead()
        self.assertFalse(is_identity_match(self.friend, self.dead, "jorge"))
        self.assertTrue(is_identity_match(self.friend, self.dead, "man"))

    def test_nothing_is_known_and_nothing_is_rolled(self):
        self.behead()
        self.assertIsNone(identity.get_known_name(self.friend, self.dead))
        self.assertEqual(
            identity.known_name_source(self.friend, self.dead), (None, None))
        with mock.patch.object(identity, "attempt_disguise_pierce") as roll:
            self.assertIsNone(identity.attempt_display_pierce(
                self.friend, self.dead, get_apparent_uid(self.dead)))
        roll.assert_not_called()

    def test_it_cannot_be_given_a_name(self):
        """A name for the headless body would be a name for the bare
        face, and the severed head would answer to it."""
        self.behead()
        self.assertIsNone(_fixed("get_recognisable_uid")(self.dead))

    def test_the_masked_dead_are_not_named_by_their_bare_body(self):
        """The leak: the mask goes with the head, so the body is the
        bare look, which the friend knows."""
        head = self.behead(masked=True)
        self.assertIs(self.mask.location, head)
        self.assertEqual(get_apparent_uid(self.dead), self.bare_look)
        for who in (self.friend, self.other):
            with self.subTest(who=who.key):
                shown = self.dead.get_display_name(who)
                self.assertNotIn("Jorge", shown)
                self.assertNotIn("Ghost", shown)

    def test_the_head_is_where_the_face_went(self):
        head = self.behead()
        self.assertTrue(
            head.get_display_name(self.friend).endswith("(Jorge)"))

    def test_an_autopsy_can_still_find_out_who_it_was(self):
        """Hard to identify, not impossible: the record keeps the look."""
        self.behead()
        self.assertEqual(get_apparent_uid(self.dead), self.bare_look)
        corpse = death_progression.DeathProgressionScript \
            ._create_corpse_from_character(None, self.dead)
        self.assertEqual(corpse.db.apparent_uid_at_death, self.bare_look)
        self.assertNotIn("(", corpse.get_display_name(self.friend))


class TestWhatReviewFound(_TheBlow):

    def recall(self):
        """What `recall man` prints for somebody standing at the body,
        who knows the bare face as Jorge."""
        self.char1.recognition_memory = {
            self.bare_look: {"assigned_name": "Jorge"}}
        from commands.CmdCharacter import CmdRecall
        cmd = CmdRecall()
        cmd.caller, cmd.args, cmd.cmdstring = self.char1, "man", "recall"
        out = []
        with mock.patch.object(
                type(self.char1), "msg",
                lambda _self, text=None, **kw: out.append(str(text))):
            cmd.func()
        return "\n".join(out)

    def test_recall_reads_the_name_off_a_living_body(self):
        """The control: the command runs here and finds the entry."""
        self.assertIn("Jorge", self.recall())

    def test_recall_reads_nothing_off_a_beheaded_body(self):
        self.behead()
        said = self.recall()
        self.assertNotIn("Jorge", said)
        self.assertIn("can't recall", said)

    def test_a_body_given_its_head_back_has_a_face_again(self):
        """An essential NPC is resleeved in the same body: flesh reset,
        then out of the death state (`world.souls.posts`)."""
        from world.medical.procedures import reset_body_preserving_augments
        self.behead()
        self.assertTrue(_fixed("has_no_face")(self.dead))
        reset_body_preserving_augments(self.dead)
        self.assertFalse(_fixed("has_no_face")(self.dead),
                         "a flag nobody cleared must not outvote the anatomy")
        self.dead.remove_death_state()
        self.assertFalse(self.dead.db.head_severed_at_decap)
        self.assertEqual(self.dead.get_display_name(self.friend), "Jorge")

    def test_a_fresh_sleeve_has_a_head_whatever_chrome_it_carries(self):
        """Round two. Severing marks the chrome in the head as severed
        too, and a resleeve carries chrome across as it was, so the
        anatomy still said "head" for a keeper with a chrome jaw. The
        door that gives the body its flesh back clears the flag."""
        from world.medical.procedures import reset_body_preserving_augments
        self.behead()
        reset_body_preserving_augments(self.dead)
        self.assertFalse(self.dead.db.head_severed_at_decap)
        with mock.patch("world.medical.severance.compute_severed_containers",
                        return_value={"head"}):
            self.assertFalse(_fixed("has_no_face")(self.dead))
            self.assertEqual(self.dead.get_display_name(self.friend), "Jorge")

    def sighting(self):
        """The friend walks in on the body; what their entry for the
        bare look then says about where they last saw Jorge."""
        self.friend.location = self.room1
        self.friend._refresh_recognition_recency()
        entry = dict(self.friend.recognition_memory[self.bare_look])
        return entry.get("location_last_seen"), entry.get("last_seen")

    def test_walking_in_on_a_living_face_is_a_sighting(self):
        """The control."""
        where, when = self.sighting()
        self.assertEqual(where, self.room1.key)
        self.assertTrue(when)

    def test_walking_in_on_a_beheaded_body_is_not(self):
        """Round two: `memory` would have read "Jorge, here, just now"
        beside a body the room shows by description."""
        self.behead()
        self.assertEqual(self.sighting(), (None, None))

    def test_a_revived_body_whose_head_is_still_off_keeps_the_flag(self):
        self.behead()
        self.dead.remove_death_state()
        self.assertTrue(self.dead.db.head_severed_at_decap)
        self.assertTrue(_fixed("has_no_face")(self.dead))


class TestABeheadingHasNoDeathWindow(_TheBlow):

    def start(self):
        return death_progression.start_death_progression(self.dead)

    def test_the_corpse_is_built_when_the_curtain_says_so(self):
        self.behead()
        script = self.start()
        self.assertIsNotNone(script)
        self.assertEqual(self.corpses(), [], "built before the room was told")
        self.assertTrue(_fixed("complete_a_beheading")(self.dead))
        self.assertEqual(len(self.corpses()), 1)
        self.assertIsNone(
            death_progression.get_death_progression_script(self.dead))

    def test_the_corpse_it_leaves_is_headless_and_names_nobody(self):
        self.behead()
        self.start()
        _fixed("complete_a_beheading")(self.dead)
        corpse = self.corpses()[0]
        self.assertTrue(corpse._is_headless())
        self.assertNotIn("(", corpse.get_display_name(self.friend))

    def test_the_curtain_asks_for_it_after_telling_the_room(self):
        self.behead()
        self.start()
        DeathCurtain._finish_a_beheading(SimpleNamespace(character=self.dead))
        self.assertEqual(len(self.corpses()), 1)
        source = inspect.getsource(DeathCurtain._on_animation_complete)
        self.assertLess(source.index("get_death_cause_template"),
                        source.rindex("_finish_a_beheading"))

    def test_nobody_checks_whether_they_can_be_revived(self):
        self.behead()
        script = self.start()
        with mock.patch.object(
                type(script), "_check_medical_revival_conditions",
                side_effect=AssertionError("a beheading is not revived")):
            script.at_repeat()

    def test_no_dying_messages_are_sent(self):
        self.behead()
        script = self.start()
        script.db.start_time -= 30    # three dying messages are due
        with mock.patch.object(
                type(script), "_send_progression_message") as said:
            script.at_repeat()
        said.assert_not_called()

    def test_a_tick_completes_it_if_the_curtain_never_did(self):
        """The backstop: a reload, or a raise on the curtain's side."""
        self.behead()
        script = self.start()
        script.db.start_time -= script.interval + 1
        script.at_repeat()
        self.assertEqual(len(self.corpses()), 1)

    def test_the_first_dying_message_is_not_sent_either(self):
        """It says there may still be time for intervention."""
        self.behead()
        with mock.patch.object(
                death_progression.DeathProgressionScript,
                "_send_initial_message") as said:
            self.start()
        said.assert_not_called()

    def test_any_other_death_still_opens_with_it(self):
        """The control."""
        with mock.patch.object(
                death_progression.DeathProgressionScript,
                "_send_initial_message") as said, mock.patch.object(
                death_progression.DeathProgressionScript,
                "_check_medical_revival_conditions", return_value=False):
            self.start()
        self.assertTrue(said.called)

    def test_any_other_death_keeps_its_window(self):
        """The control, true before the fix and after it: not beheaded,
        so nothing completes at once and the revival check is asked."""
        at_once = getattr(death_progression, "complete_a_beheading",
                          lambda character: False)
        with mock.patch.object(
                death_progression.DeathProgressionScript,
                "_check_medical_revival_conditions",
                return_value=False) as asked:
            script = self.start()
            self.assertFalse(at_once(self.dead))
            script.at_repeat()
        self.assertTrue(asked.called)
        self.assertEqual(self.corpses(), [])
        self.assertIsNotNone(
            death_progression.get_death_progression_script(self.dead))
