"""Identity is in the face (#3831, #3832, #3834).

The spec's rule for a body that has been transformed ("Identity Across
Surfaces"): the head carries the face. The owner's words for it,
2026-11-14: "A body without a head is hard to identify. A head on its
own is easy to identify but can also still be concealed by a mask."

Three places did not follow it.

* A CORPSE counted every disguise item inside it as worn (#3831). The
  death transfer moves the whole inventory in, so somebody who died
  bare-faced with a mask in a pocket left a body that presented the
  masked look, while its description showed the face.
* A SEVERED HEAD counted nothing as worn (#3832), from when nothing
  could be worn on one. A head in a balaclava was named to everybody
  who knew the bare face.
* A HEADLESS CORPSE named nobody in its header and still filled the
  ``{name}`` token of its description with the reader's name for the
  dead (#3834).

Everything here is built through the game's own doors: the corpse
factory, `wear_item`, the dress and undress commands' own methods, and
the sever helper. No stand-ins.
"""
from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from commands.CmdClothing import CmdDress, CmdUndress
from typeclasses.characters import Character
from typeclasses.death_progression import DeathProgressionScript
from typeclasses.items import spawn_severed_part_from_corpse
from world.identity import get_apparent_uid

SCAR = "{name} has a scar across {their} chest."


class _TheDead(EvenniaTest):
    """Somebody who is about to die, a friend who knows the bare face
    as Jorge, and somebody who only ever met the masked figure and
    called it Ghost.

    The two of them stand in ANOTHER ROOM throughout. Somebody who
    watches a mask go on keeps the name (#3811), and that carries
    through to the body; whether watching remains being dressed should
    do the same is undecided (#3833). These tests are about people who
    saw none of it.
    """

    def setUp(self):
        super().setUp()
        self.dead = self.body("Jorvik Ansel", "sleeve-dead")
        longdesc = dict(self.dead.longdesc or {})
        longdesc["chest"] = SCAR
        self.dead.longdesc = longdesc
        self.mask = spawn("SKI_MASK")[0]
        self.mask.location = self.dead

        self.bare_look = get_apparent_uid(self.dead)
        ok, why = self.dead.wear_item(self.mask)
        self.assertTrue(ok, why)
        self.masked_look = get_apparent_uid(self.dead)
        self.assertNotEqual(self.bare_look, self.masked_look)
        ok, why = self.dead.remove_item(self.mask)
        self.assertTrue(ok, why)

        self.friend = self.body("Petra Lund", "sleeve-friend", self.room2)
        self.friend.recognition_memory = {
            self.bare_look: {"assigned_name": "Jorge"}}
        self.other = self.body("Odile Marsh", "sleeve-other", self.room2)
        self.other.recognition_memory = {
            self.masked_look: {"assigned_name": "Ghost"}}

    def body(self, key, sleeve, room=None):
        char = create_object(Character, key=key,
                             location=room or self.room1)
        char.sleeve_uid = sleeve
        char.height, char.build, char.sdesc_keyword = "short", "lean", "man"
        char.recognition_memory = {}
        return char

    def dies(self, masked):
        """The corpse the game's own factory makes of them."""
        if masked:
            ok, why = self.dead.wear_item(self.mask)
            self.assertTrue(ok, why)
        return DeathProgressionScript._create_corpse_from_character(
            None, self.dead)

    def names(self, remains):
        """What the friend and the other are shown."""
        return (remains.get_display_name(self.friend),
                remains.get_display_name(self.other))


class TestAMaskInAPocketHidesNobody(_TheDead):
    """#3831: died bare-faced, the mask carried."""

    def setUp(self):
        super().setUp()
        self.corpse = self.dies(masked=False)

    def test_the_setup_is_what_it_says(self):
        self.assertIn(self.mask, self.corpse.contents)
        self.assertEqual(list(self.corpse.db.worn_at_death), [])

    def test_the_corpse_does_not_wear_it(self):
        self.assertEqual(self.corpse.get_worn_items(), [])

    def test_the_body_presents_the_face_it_died_with(self):
        self.assertEqual(get_apparent_uid(self.corpse), self.bare_look)

    def test_the_friend_is_shown_the_name(self):
        friend, _other = self.names(self.corpse)
        self.assertTrue(friend.endswith("(Jorge)"), friend)

    def test_somebody_who_knew_only_the_mask_is_shown_nothing(self):
        _friend, other = self.names(self.corpse)
        self.assertNotIn("(", other)

    def test_identity_and_the_description_agree(self):
        """One question, one answer: what identity counts as worn is
        the disguise part of what the description shows as worn."""
        shown = self.corpse.worn_garments()
        self.assertEqual(
            self.corpse.get_worn_items(),
            [it for it in shown if it.disguise_essential])

    def test_taking_it_leaves_the_death_time_look_alone(self):
        before = self.corpse.db.apparent_uid_at_death
        self.assertIsNotNone(before)
        self.mask.move_to(self.room1, quiet=True)
        self.assertEqual(self.corpse.db.apparent_uid_at_death, before)


class TestAMaskOverTheFaceConceals(_TheDead):
    """The other half, which already held: died wearing it."""

    def setUp(self):
        super().setUp()
        self.corpse = self.dies(masked=True)

    def test_the_corpse_wears_it(self):
        self.assertEqual(self.corpse.get_worn_items(), [self.mask])
        self.assertEqual(get_apparent_uid(self.corpse), self.masked_look)

    def test_who_is_shown_what(self):
        friend, other = self.names(self.corpse)
        self.assertNotIn("(", friend)
        self.assertTrue(other.endswith("(Ghost)"), other)

    def test_taking_it_off_shows_the_face(self):
        self.mask.move_to(self.room1, quiet=True)
        self.assertEqual(get_apparent_uid(self.corpse), self.bare_look)
        friend, other = self.names(self.corpse)
        self.assertTrue(friend.endswith("(Jorge)"), friend)
        self.assertNotIn("(", other)

    def test_taking_it_off_ends_the_death_time_look(self):
        self.assertIsNotNone(self.corpse.db.apparent_uid_at_death)
        self.mask.move_to(self.room1, quiet=True)
        self.assertIsNone(self.corpse.db.apparent_uid_at_death)


class TestACorpseCanBeDressed(_TheDead):
    """Why "worn at death" was the wrong test: `dress` puts a mask on
    a body afterwards, and `undress` takes it off."""

    def setUp(self):
        super().setUp()
        self.corpse = self.dies(masked=False)
        self.mask.move_to(self.char1, quiet=True)

    def dress(self):
        ok, _why = CmdDress()._dress_corpse(self.corpse, self.mask)
        self.assertTrue(ok)

    def test_a_mask_put_on_the_dead_conceals_them(self):
        self.dress()
        self.assertEqual(self.corpse.get_worn_items(), [self.mask])
        friend, other = self.names(self.corpse)
        self.assertNotIn("(", friend)
        self.assertTrue(other.endswith("(Ghost)"), other)

    def test_undressing_shows_the_face_again(self):
        self.dress()
        cmd = CmdUndress()
        cmd.caller = self.char1
        self.assertEqual(cmd._undress_remains(self.corpse, None),
                         [self.mask])
        self.mask.move_to(self.char1, quiet=True)
        friend, _other = self.names(self.corpse)
        self.assertTrue(friend.endswith("(Jorge)"), friend)


class TestAHeadOnItsOwn(_TheDead):
    """#3832: easy to identify, and a mask still conceals it."""

    def head_of(self, masked):
        self.corpse = self.dies(masked=masked)
        head = spawn_severed_part_from_corpse(self.corpse, "head")
        self.assertIsNotNone(head)
        return head

    def test_a_bare_head_is_known_by_the_face(self):
        head = self.head_of(masked=False)
        self.assertEqual(head.get_worn_items(), [])
        friend, other = self.names(head)
        self.assertTrue(friend.endswith("(Jorge)"), friend)
        self.assertNotIn("(", other)

    def test_the_mask_goes_with_the_head(self):
        """The setup the next tests rest on (#3577)."""
        head = self.head_of(masked=True)
        self.assertIs(self.mask.location, head)
        self.assertIn(self.mask, head.worn_garments())

    def test_a_masked_head_wears_its_mask(self):
        head = self.head_of(masked=True)
        self.assertEqual(head.get_worn_items(), [self.mask])
        self.assertEqual(get_apparent_uid(head), self.masked_look)

    def test_a_masked_head_is_concealed(self):
        head = self.head_of(masked=True)
        friend, other = self.names(head)
        self.assertNotIn("(", friend)
        self.assertTrue(other.endswith("(Ghost)"), other)

    def test_taking_the_mask_off_shows_the_face(self):
        head = self.head_of(masked=True)
        self.mask.move_to(self.room1, quiet=True)
        self.assertEqual(head.get_worn_items(), [])
        friend, other = self.names(head)
        self.assertTrue(friend.endswith("(Jorge)"), friend)
        self.assertNotIn("(", other)

    def test_a_mask_put_on_a_head_conceals_it(self):
        head = self.head_of(masked=False)
        self.mask.move_to(self.char1, quiet=True)
        cmd = CmdDress()
        cmd.caller = self.char1
        ok, why = cmd._dress_appendage(head, self.mask)
        self.assertTrue(ok, why)
        friend, _other = self.names(head)
        self.assertNotIn("(", friend)

    def test_a_pocketed_mask_does_not_follow_the_head(self):
        head = self.head_of(masked=False)
        self.assertIs(self.mask.location, self.corpse)
        self.assertEqual(head.get_worn_items(), [])


class TestABodyWithoutItsHead(_TheDead):
    """#3834: hard to identify, in the header and in the prose.

    No mask anywhere near this body: it is left on the floor before the
    death, so the unfixed tree has nothing to mis-count and these tests
    speak about the missing head alone.
    """

    def setUp(self):
        super().setUp()
        self.mask.move_to(self.room1, quiet=True)
        self.corpse = self.dies(masked=False)

    def test_with_its_head_the_prose_names_the_dead_to_a_friend(self):
        """The control: the token works while there is a face."""
        seen = self.corpse.return_appearance(self.friend)
        self.assertIn("Jorge has a scar across", seen)

    def behead(self):
        self.assertIsNotNone(
            spawn_severed_part_from_corpse(self.corpse, "head"))
        self.assertTrue(self.corpse._is_headless())

    def test_the_header_names_nobody(self):
        self.behead()
        friend, other = self.names(self.corpse)
        self.assertNotIn("(", friend)
        self.assertNotIn("(", other)

    def test_the_bearer_answers_nobody(self):
        self.behead()
        self.assertIsNone(self.corpse.recognised_as(self.friend))

    def test_the_prose_names_nobody(self):
        self.behead()
        seen = self.corpse.return_appearance(self.friend)
        self.assertIn("the corpse has a scar across", seen)
        self.assertNotIn("Jorge", seen)
        self.assertNotIn("Jorvik", seen)

    def test_the_head_still_tells_the_friend_who_it_was(self):
        head = spawn_severed_part_from_corpse(self.corpse, "head")
        self.assertTrue(
            head.get_display_name(self.friend).endswith("(Jorge)"))
