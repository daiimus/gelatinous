"""A name given to a mask tells nothing (#3813).

The owner, asked whether naming someone should stop connecting that name
to other names held for the same real person: "Your version is correct
and was the original intent. Either something broke, was done
incorrectly, or you've misread the code."

It was done incorrectly. The spec linked a newly named look to the bare
face "the looker matched against" when they ran `remember <pierced
name>`: a look they had SEEN THROUGH. The code that wrote the link
(2026-05-15) linked every newly named look to another entry for the same
true body. So a player whose see-through had failed could name the
masked figure anything and read who it was off `recall`.

Real commands (`remember`, `wear`, `remove`, `recall`, `memory`, `look`)
on fresh bodies with the real ski mask; the dice are stood in for only
to choose a branch.
"""
from world.identity import get_apparent_uid, linked_family
from world.tests.test_an_eyewitness_keeps_the_name import (
    LOST, WON, _MaskCase,
)


class _TheMaskWentOnOutOfSight(_MaskCase):
    """The viewer calls the bare face Tamsin. The mask goes on in another
    room, and Tamsin walks back in under it."""

    RESULT = LOST

    def setUp(self):
        super().setUp()
        self.bare = get_apparent_uid(self.them)
        self.them.move_to(self.room2, quiet=True, move_hooks=False)
        self.them.execute_cmd("wear ski mask")
        self.them.move_to(self.room1, quiet=True, move_hooks=False)
        self.masked = get_apparent_uid(self.them)
        self.dice(self.RESULT)
        self.seen = self.roster()

    def memory(self):
        return dict(self.viewer.recognition_memory)


class TestTheDisguiseHeld(_TheMaskWentOnOutOfSight):
    RESULT = LOST

    def setUp(self):
        super().setUp()
        self.do("remember masked man as Ghost")

    def test_the_setup_is_what_it_says(self):
        self.assertIn("masked man", self.seen)
        self.assertNotIn("Tamsin", self.seen)
        self.assertEqual(self.memory()[self.masked]["assigned_name"], "Ghost")

    def test_recall_of_the_mask_does_not_say_who_it_is(self):
        told = self.do("recall ghost")
        self.assertIn("Ghost", told)
        self.assertNotIn("Tamsin", told)
        self.assertNotIn("Also known as", told)

    def test_nor_does_recall_of_the_face_name_the_mask(self):
        told = self.do("recall tamsin")
        self.assertIn("Tamsin", told)
        self.assertNotIn("Ghost", told)

    def test_nor_does_the_memory_table(self):
        self.assertNotIn("aka", self.do("memory"))

    def test_the_two_entries_are_not_one_family(self):
        """What an AI-driven NPC's prompt and memory retrieval read."""
        self.assertIsNone(self.memory()[self.masked].get("linked_to"))
        self.assertEqual(linked_family(self.memory(), self.masked),
                         [self.masked])

    def test_until_the_mask_comes_off_in_front_of_them(self):
        """The earned route, as it always was: they watch it happen and
        are told so."""
        told = self.they("remove ski mask")
        self.assertEqual(
            told, "Ghost removes a wool ski mask, revealing they are "
                  "none other than Tamsin.")
        recalled = self.do("recall tamsin")
        self.assertIn("Also known as", recalled)
        self.assertIn("Ghost", recalled)


class TestTheDisguiseWasSeenThrough(_TheMaskWentOnOutOfSight):
    RESULT = WON

    def setUp(self):
        super().setUp()
        self.do("remember tamsin as Ghost")

    def test_the_setup_is_what_it_says(self):
        self.assertIn("Tamsin", self.seen)
        self.assertEqual(self.memory()[self.masked]["assigned_name"], "Ghost")

    def test_the_name_given_to_the_mask_is_joined_to_the_face(self):
        self.assertEqual(self.memory()[self.masked]["linked_to"], self.bare)
        told = self.do("recall ghost")
        self.assertIn("Also known as", told)
        self.assertIn("Tamsin", told)
