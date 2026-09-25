"""A deleted mast is a downed mast (#3558).

A base station rides its mast: intact = mast-tier reach, wrecked (the
`sabotage` seam) = handheld reach. Every reader treated "no mast" as the
permissive case, and a DELETED mast reads as no mast (a deleted object
deserializes as None), so deleting a mast gave its station colony-wide
reach while wrecking it cut the station down. `world.radio.mast_down` is
now the one reading, and it tells "linked, then deleted" (the attribute
row survives) from "never linked" (no row: the crane console, which must
keep the reach it was built with).

Real objects throughout: the premise is how Evennia deserializes a
reference to a deleted object, which a mock cannot show.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.radio import (MAST_TX_RANGE, RADIO_TX_RANGE, _effective_tx_range,
                         mast_down)


class _Station(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.station = create_object("typeclasses.items.AnsweringFixture",
                                     key="repeater cabinet", location=self.room1)
        self.station.db.is_base_station = True
        self.mast = create_object("typeclasses.items.Item",
                                  key="repeater mast", location=self.room1)
        self.mast.db.intact = True

    def link(self):
        self.station.db.antenna = self.mast

    def reach(self):
        return _effective_tx_range(self.station, (0, 0, 0))


class TheMastSeam(_Station):

    def test_an_intact_mast_rides_the_mast(self):
        self.link()
        self.assertFalse(mast_down(self.station))
        self.assertEqual(self.reach(), MAST_TX_RANGE)

    def test_a_wrecked_mast_is_down(self):
        self.link()
        self.mast.db.intact = False
        self.assertTrue(mast_down(self.station))
        self.assertEqual(self.reach(), RADIO_TX_RANGE)

    def test_the_premise_a_deleted_mast_reads_as_none_but_the_row_survives(self):
        self.link()
        self.mast.delete()
        self.assertIsNone(self.station.db.antenna)
        self.assertTrue(self.station.attributes.has("antenna"))

    def test_a_deleted_mast_is_down(self):
        self.link()
        self.mast.delete()
        self.assertTrue(mast_down(self.station))
        self.assertEqual(self.reach(), RADIO_TX_RANGE)

    def test_control_a_station_never_linked_keeps_its_reach(self):
        # The crane console's shape: a base station with no mast at all.
        self.assertFalse(self.station.attributes.has("antenna"))
        self.assertFalse(mast_down(self.station))
        self.assertEqual(self.reach(), MAST_TX_RANGE)


class TheStationAnswers(_Station):
    """`_answer` re-checks the mast at send time."""

    def _answered(self):
        with mock.patch("world.radio.is_powered", return_value=True), \
             mock.patch("world.radio.transmit") as tx:
            self.station._answer("copy", speaker=self.char2)
        return tx.called

    def test_a_deleted_mast_is_silence(self):
        self.link()
        self.mast.delete()
        self.assertFalse(self._answered())

    def test_control_an_intact_mast_answers(self):
        self.link()
        self.assertTrue(self._answered())
