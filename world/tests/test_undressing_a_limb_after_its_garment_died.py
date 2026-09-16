"""A severed limb forgets a destroyed garment, so `undress <limb>` never
trips over a dead entry (#3554).

A limb keeps its own wardrobe (`db.worn_items`) for the garments that
travelled with it at severance. Characters got `release_slots` so a
destroyed or departed item leaves no dead entry; the limb never did,
and the generic delete hook that calls `release_slots` on the garment's
location silently no-oped. Looking at the limb was patched read-side
once; bare `undress <limb>` still appended the `None` and crashed on
`move_to`. Now the limb has the same release method, and `undress`
heals what it reads and writes the ledger back.
"""
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest


class _LimbWithGlove(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.limb = create_object("typeclasses.items.Appendage", key="severed left arm", location=self.room1)
        self.glove = create_object("typeclasses.items.Item", key="leather glove", location=self.limb)
        self.glove.db.coverage = ["left_hand"]
        self.limb.db.worn_items = {"left_hand": [self.glove]}
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))

    def undress(self, phrase=""):
        from commands.CmdClothing import CmdUndress
        cmd = CmdUndress(); cmd.caller = self.char1; cmd.args = ("severed left arm " + phrase).strip()
        cmd.cmdstring = "undress"; cmd.switches = []
        cmd.func()
        return " ".join(self.said)


class TestTheLimbForgetsADestroyedGarment(_LimbWithGlove):
    def test_the_ledger_is_clean_after_the_glove_is_destroyed(self):
        self.glove.delete()
        self.assertEqual(dict(self.limb.db.worn_items or {}), {})

    def test_undress_after_the_destroy_does_not_crash(self):
        self.glove.delete()
        said = self.undress()
        self.assertIn("isn't wearing anything", said, said)

    def test_a_garment_that_left_by_another_door_is_forgotten_too(self):
        self.glove.move_to(self.room1, quiet=True)
        self.assertEqual(dict(self.limb.db.worn_items or {}), {})


class TestUndressHealsALegacyLedger(_LimbWithGlove):
    def test_a_dead_entry_written_before_the_fix_is_pruned_not_tripped_over(self):
        # the shape the crash had: a None where a garment used to be
        self.limb.db.worn_items = {"left_hand": [None], "left_arm": [self.glove]}
        said = self.undress()
        self.assertIn("leather glove", said, said)
        self.assertEqual(self.glove.location, self.char1)
        self.assertEqual(dict(self.limb.db.worn_items or {}), {})


class TestAWornGloveStillComesOff(_LimbWithGlove):
    def test_control(self):
        said = self.undress()
        self.assertIn("leather glove", said, said)
        self.assertEqual(self.glove.location, self.char1)
