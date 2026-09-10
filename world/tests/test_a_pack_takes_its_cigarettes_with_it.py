"""Deleting a cigarette pack deletes its cigarettes (#2635).

`CigarettePack` handled exactly ONE destruction route -- its own
`at_object_leave` self-destruct when a player draws the last cigarette.
Every other route (`@delete`, a room or corpse cleanup, a purge) runs
`DefaultObject.delete()`, which calls `clear_contents()`, which moves
each cigarette to its HOME. A spawned cigarette has none, so home is
`#2` and ten cigarettes fell into Limbo per pack, permanently -- 420 of
them were sitting there when this was found, in exact runs of ten, none
ever smoked.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest


class TestAPackTakesItsCigarettesWithIt(EvenniaTest):

    def _pack(self):
        return create_object("typeclasses.smoke.CigarettePack",
                             key="test pack", location=self.room1)

    def test_the_fixture_actually_holds_cigarettes(self):
        """Control: an empty pack would make every assertion below
        vacuous, and the pack fills from a prototype that may not spawn
        under the test settings."""
        pack = self._pack()
        self.assertEqual(len(pack.contents), 10)

    def test_deleting_the_pack_deletes_them(self):
        pack = self._pack()
        cigs = list(pack.contents)
        pack.delete()
        for cig in cigs:
            self.assertFalse(
                ObjectDB.objects.filter(id=cig.id).exists(),
                "a deleted pack orphaned a cigarette")

    def test_none_of_them_land_in_limbo(self):
        """The observable the live census measured."""
        pack = self._pack()
        cigs = list(pack.contents)
        pack.delete()
        limbo = ObjectDB.objects.filter(id=2).first()
        if limbo:
            for cig in cigs:
                self.assertNotIn(cig, limbo.contents)

    def test_drawing_the_last_one_still_leaves_it_in_your_hand(self):
        """The route that already worked must keep working: the pack
        crushes itself as the last cigarette leaves, and the cigarette
        the player just took must NOT be deleted with it."""
        pack = self._pack()
        for extra in list(pack.contents)[1:]:
            extra.delete()
        cig = pack.contents[0]
        cig.move_to(self.char1, quiet=True)
        pack.delete()           # what the deferred crush does
        self.assertTrue(ObjectDB.objects.filter(id=cig.id).exists(),
                        "the pack took the cigarette out of your hand")
        self.assertIs(cig.location, self.char1)
