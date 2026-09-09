"""Looking at a pack does not mint cigarettes (#2935 follow-up).

Before #2935, `_fill_with_cigarettes()` was called from ONE place --
`at_object_creation`. A pack was filled once, when it was made.

#2935 added `_ensure_correct_fill()` to `return_appearance`, so the
check now runs on EVERY LOOK. It repairs a mis-branded pack, which is
what it was for, and it also does this:

    if not self.contents:
        self._fill_with_cigarettes()      # -> spawns `capacity` more

"Empty" cannot tell "never filled" (the migration case #2935 exists
for) from "a player smoked them all". `at_object_leave` normally
crushes a pack as its last cigarette is drawn, but anything that empties
one without firing that hook -- a `move_hooks=False` path, a deferred
delete that did not land -- leaves a live empty pack that refills itself
the next time anybody looks at it.

Measured in a testbed:

    fresh pack holds: 10 capacity: 10
    after a look, full pack holds: 10       (control: no refill)
    emptied by hand, pack holds: 0  pack alive: True
    AFTER A LOOK, empty pack holds: 10      <- ten more, from nothing

And one is live right now: pack #4667 sits at 0/10, so the next person
to look at it is handed ten cigarettes.

Fixed by remembering that the pack HAS been filled, rather than
inferring it from being non-empty. The migration case still works --
a pack that predates the hook has no marker and gets its one fill --
and mis-branded cigarettes are still replaced, but one-for-one rather
than topped up to capacity.
"""
from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest


class TestAPackDoesNotMintCigarettes(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.looker = create_object("typeclasses.characters.Character",
                                    key="Looker", location=self.room1)
        self.pack = spawn("CIGARETTE_PACK_NOIR")[0]
        self.pack.location = self.room1

    def _empty_by_hand(self):
        """Empty it the way a `move_hooks=False` path would -- without
        firing the crush hook."""
        for cig in list(self.pack.contents):
            cig.location = self.room1

    def test_a_full_pack_does_not_refill_on_a_look(self):
        """Control: without this, 'never refills' would also be true of
        a function that does nothing at all."""
        before = len(self.pack.contents)
        self.assertGreater(before, 0, "the fixture spawned an empty pack")
        self.pack.return_appearance(self.looker)
        self.assertEqual(len(self.pack.contents), before)

    def test_an_emptied_pack_does_not_refill_on_a_look(self):
        self._empty_by_hand()
        self.assertTrue(self.pack.pk, "the fixture crushed the pack")
        self.pack.return_appearance(self.looker)
        self.assertEqual(
            len(self.pack.contents), 0,
            "looking at an emptied pack minted a fresh set of cigarettes")

    def test_a_pack_that_was_never_filled_still_gets_its_one_fill(self):
        """The migration #2935 exists for: a pack from before the hook,
        which has no cigarettes and has never had any."""
        pack = spawn("CIGARETTE_PACK_NOIR")[0]
        pack.location = self.room1
        for cig in list(pack.contents):
            cig.delete()
        pack.attributes.remove("filled_once")   # as if it predates the marker
        pack.return_appearance(self.looker)
        self.assertEqual(len(pack.contents), int(pack.db.capacity))

    def test_misbranded_cigarettes_are_replaced_one_for_one(self):
        """#2935's actual job, and it must not top the pack back up."""
        self._empty_by_hand()
        # NOT the pack itself -- its key is "pack of Noir cigarettes",
        # so a bare "cigarette" match selected the pack and setting
        # `pack.location = pack` raised a location loop.
        for cig in list(self.room1.contents):
            key = (cig.key or "").lower()
            if cig is not self.pack and "cigarette" in key and "pack" not in key:
                cig.location = self.pack
                break
        held = len(self.pack.contents)
        self.assertEqual(held, 1, "fixture put back more than one")
        self.pack.contents[0].db.substance = "not-the-packs-substance"
        self.pack.return_appearance(self.looker)
        self.assertEqual(
            len(self.pack.contents), 1,
            "a mis-branded single cigarette was topped up to capacity")
        self.assertEqual(self.pack.contents[0].db.substance,
                         self.pack.db.substance)
