"""Spending the last unit of solvent still breaks down the blood (#3378).

`_apply_solvent` consumed the solvent (which DELETES an emptied can) and
then read `solvent_can.db.quality` off the deleted object to decide how
well the blood breaks down. The read either raised -- swallowed by the
channel, so the blood was never touched and the player got no message --
or degraded to "basic". The quality is now read before the can is spent.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.CmdGraffiti import CmdGraffiti


class LastUnitOfSolventStillCleansTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.pool = create_object("typeclasses.objects.BloodPool", key="blood pool", location=self.room1)
        self.pool.db.bleeding_incidents = [{"volume": 40}]     # truthy is all has_blood needs
        self.can = create_object("typeclasses.items.SolventCanItem", key="solvent can", location=self.char1)
        self.can.db.aerosol_level = 1                            # the LAST unit
        self.can.db.quality = "professional"

    def test_last_unit_cleans_with_the_cans_real_quality(self):
        with mock.patch("typeclasses.objects.BloodPool.clean_with_solvent", return_value=(10, "")) as clean:
            CmdGraffiti()._apply_solvent(self.char1, self.can, 1)
        clean.assert_called_once()
        self.assertEqual(clean.call_args.args[1], "professional",
                         "quality read after the can was consumed: %r" % (clean.call_args.args,))

    def test_the_can_is_still_consumed(self):
        with mock.patch("typeclasses.objects.BloodPool.clean_with_solvent", return_value=(10, "")):
            CmdGraffiti()._apply_solvent(self.char1, self.can, 1)
        self.assertIsNone(self.can.pk, "an emptied can was not deleted")

    def test_a_can_with_units_left_is_unchanged_in_behaviour(self):
        self.can.db.aerosol_level = 50
        with mock.patch("typeclasses.objects.BloodPool.clean_with_solvent", return_value=(10, "")) as clean:
            CmdGraffiti()._apply_solvent(self.char1, self.can, 1)
        self.assertEqual(clean.call_args.args[1], "professional")
        self.assertEqual(self.can.db.aerosol_level, 49)
