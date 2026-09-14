"""An organic harvest knows when it came out; chrome does not (#3498).

Owner ruling 2026-09-14: chrome doesn't rot; organic harvested organs
get a harvest timestamp, refrigeration later. `_configure_harvested_item`
-- the one stamping site behind both harvest doors and `strip_organ` --
stamps `harvested_at` with `world.gametime.stamp()` (real POSIX seconds)
on organic organs only. No consumer is wired yet (balance pass pending).
"""
import time

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical import procedures as P


class AnOrganicHarvestKnowsWhenItCameOutTest(EvenniaTest):

    def _item(self):
        return create_object("typeclasses.items.Organ", key="harvested", location=self.room1)

    def test_a_liver_is_stamped_with_now(self):
        before = time.time()
        item = self._item()
        P._configure_harvested_item(item, organ_name="liver", condition="pristine", source=self.char1,
                                    organ_data={"container": "abdomen", "data": {"container": "abdomen"}, "current_hp": 20, "max_hp": 20, "conditions": []})
        self.assertIsNotNone(item.db.harvested_at, "no harvest timestamp on an organic organ")
        self.assertGreaterEqual(item.db.harvested_at, before)
        self.assertLessEqual(item.db.harvested_at, time.time())

    def test_the_stamp_is_a_plain_number_for_subtraction(self):
        from world.gametime import since
        item = self._item()
        P._configure_harvested_item(item, organ_name="heart", condition="damaged", source=self.char1,
                                    organ_data={"container": "chest", "data": {"container": "chest"}, "current_hp": 10, "max_hp": 20, "conditions": []})
        self.assertIsInstance(item.db.harvested_at, float)
        self.assertGreaterEqual(since(item.db.harvested_at), 0.0)

    def test_strip_goes_through_the_same_stamp(self):
        harvested = P.strip_organ(self.char1, "liver", into=self.room1)
        self.assertIsNotNone(harvested, "fixture: strip_organ produced nothing")
        self.assertIsNotNone(harvested.db.harvested_at)

    # --- control ---------------------------------------------------------

    def test_chrome_is_not_stamped(self):
        item = self._item()
        P._configure_harvested_item(item, organ_name="left_forearm_hardpoint", condition="pristine", source=self.char1,
                                    organ_data={"container": "left_arm", "data": {"inorganic": True, "hardpoint": "forearm"}, "current_hp": 30, "max_hp": 30, "conditions": []})
        self.assertIsNone(item.db.harvested_at, "chrome got a rot clock")

    def test_a_fresh_organ_item_declares_the_field(self):
        self.assertIsNone(self._item().db.harvested_at)
