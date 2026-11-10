"""Breach: sabotage/repair of breachable structures (masts).

Channel timing is world/channeled.py's tested concern; these tests fire
the captured callbacks directly and pin the state machine — the wreck/
mend round trip, the crime at commission, the shared-verb routing, and
that interruption lands nothing.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import commands.CmdBreach as breach


def _mast(intact=True, key="antenna mast"):
    mast = MagicMock()
    mast.key = key
    mast.aliases.all.return_value = ["mast"]
    mast.db = SimpleNamespace(
        breachable=True, intact=intact,
        desc="authored prose", sensory_contributions={"visual": "authored"},
        intact_desc=None, intact_sensory=None)
    return mast


# #3783: the sabotage/repair tests that drove the verbs with a MagicMock
# caller now run with real objects in
# world/tests/test_breach_names_a_structure_like_any_other.py, which
# pins the same claims through the commands; see that file. That
# includes `test_already_wrecked_refuses`: on a mock caller the search
# hands back a mock, so the old test passed whatever the mast's state.


class TestSabotage(TestCase):
    def test_wreck_round_trip_restores_authored_prose(self):
        mast = _mast()
        breach.wreck_structure(mast)
        self.assertIs(mast.db.intact, False)
        self.assertEqual(mast.db.desc, breach.WRECKED_DESC)
        self.assertEqual(mast.db.intact_desc, "authored prose")
        breach.mend_structure(mast)
        self.assertIs(mast.db.intact, True)
        self.assertEqual(mast.db.desc, "authored prose")
        self.assertEqual(mast.db.sensory_contributions,
                         {"visual": "authored"})


class TestSharedRepairVerb(EvenniaTest):
    """Real objects and a real searcher (#3783): the old MagicMock
    caller had no search, so the verb could not find the mast."""

    def test_wrecked_structure_claims_the_verb_and_mends(self):
        mast = create_object("typeclasses.objects.Object",
                             key="antenna mast", location=self.room1,
                             aliases=["mast"])
        mast.db.breachable = True
        mast.db.intact = True
        mast.db.desc = "authored prose"
        mast.db.sensory_contributions = {"visual": "authored"}
        breach.wreck_structure(mast)
        captured = {}

        def fake_begin(actor, duration, tell, on_complete, on_interrupt, key):
            captured.update(complete=on_complete, key=key)
            return True

        with patch("world.channeled.begin_channel", side_effect=fake_begin):
            handled = breach.try_repair_structure(self.char2, "mast")
        self.assertTrue(handled)
        self.assertEqual(captured["key"], "repairing")
        captured["complete"]()
        self.assertIs(mast.db.intact, True)
        self.assertEqual(mast.db.desc, "authored prose")
        self.assertEqual(mast.db.sensory_contributions,
                         {"visual": "authored"})
