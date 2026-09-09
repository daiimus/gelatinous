"""A call cannot record a unit it cannot name (#2893).

`record_dispatch` wrote whatever id it could get and then judged the
list by length alone:

    call["units"] = [getattr(u, "id", None) for u in (units or ())]
    call["status"] = "rolling" if call["units"] else "no units"

`[None]` is a non-empty list, so a call whose only "unit" had no id was
recorded as **rolling**. That is worse than a cosmetic null: `close_call`
matches on unit ids, so the desk believed a unit was en route to an
incident it could never close against.

Measured when this was filed: 8 of 12 live calls recorded `units=[None]`
in a single 18.9h burst, all reading `rolling`. Contrast ids 3 and 4,
which correctly recorded `"no units"` with an empty list -- the same
ledger, doing it right, two rows apart.

Those eight have since aged out of the ledger (5 calls today, none
null), but the code that wrote them is unchanged, so the mechanism is
still live. The fix is the one the issue asked for: drop ids that are
not real, and let the status follow what actually got recorded rather
than how long the list is.

Deliberately NOT filtering on "is this object alive" -- that is a
different question and a heavier one. The claim here is only that a
call must be able to NAME what it sent.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.director import calls as callsmod


class _Ledger(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.store = [{"id": 7, "type": "assault", "units": [], "status": "open"}]
        self.load = mock.patch.object(callsmod, "_load",
                                      side_effect=lambda: self.store)
        self.save = mock.patch.object(
            callsmod, "_save",
            side_effect=lambda rows: self.store.__setitem__(slice(None), rows))
        self.load.start(); self.save.start()
        self.addCleanup(self.load.stop); self.addCleanup(self.save.stop)

    def call_row(self):
        return self.store[0]

    def _unit(self, key="Unit"):
        return create_object("typeclasses.characters.Character",
                             key=key, location=self.room1)


class TestARecordedCallCanBeClosedAgainst(_Ledger):

    def test_real_units_are_recorded_and_roll(self):
        """Control: without this, 'never records a null' would also be
        true of code that records nothing at all."""
        a, b = self._unit("A"), self._unit("B")
        callsmod.record_dispatch(7, [a, b])
        self.assertEqual(self.call_row()["units"], [a.id, b.id])
        self.assertEqual(self.call_row()["status"], "rolling")

    def test_a_unit_with_no_id_is_not_recorded(self):
        nameless = mock.MagicMock()
        nameless.id = None
        callsmod.record_dispatch(7, [nameless])
        self.assertEqual(self.call_row()["units"], [])

    def test_and_the_call_does_not_read_as_rolling(self):
        """The half that made it more than cosmetic: `[None]` is truthy,
        so the desk believed a unit was en route."""
        nameless = mock.MagicMock()
        nameless.id = None
        callsmod.record_dispatch(7, [nameless])
        self.assertEqual(self.call_row()["status"], "no units")

    def test_a_real_unit_beside_a_nameless_one_still_rolls(self):
        real = self._unit("Real")
        nameless = mock.MagicMock()
        nameless.id = None
        callsmod.record_dispatch(7, [real, nameless])
        self.assertEqual(self.call_row()["units"], [real.id])
        self.assertEqual(self.call_row()["status"], "rolling")

    def test_dispatching_nobody_reads_as_no_units(self):
        callsmod.record_dispatch(7, [])
        self.assertEqual(self.call_row()["units"], [])
        self.assertEqual(self.call_row()["status"], "no units")
