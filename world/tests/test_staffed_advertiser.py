"""Some work is a person's to do (#2261).

`maintenance` was advertised nowhere on purpose, because the dwell
step's maintenance branch also CLEARS a logged defect — so ANY
advertiser lets a machine service itself by leaning on a wall fitting,
which deletes the job a person is meant to hold.

But "nowhere" left units faulting weekly with no plan forever. A
STAFFED advertiser is the middle: the bench offers repair only while
somebody is standing their shift at it. Off shift the need has no plan,
and that absence is what a vacancy is supposed to feel like.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import actions


class TestAStaffedAdvertiser(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.bench = self.obj1
        self.bench.location = self.room1
        self.bench.db.advertises = {"maintenance": 0.9}
        self.bench.db.advertise_staffed = True
        # advertisers are found by an INDEXED TAG, not by the attribute
        # (hardening spec law #3 — the attribute join is uncached)
        self.bench.tags.add("advertiser", category="souls")
        actions._ad_cache["at"] = 0
        self.unit = self.char1
        self.unit.location = self.room1

    def _found(self, need="maintenance"):
        actions._ad_cache["at"] = 0          # the cache has a TTL
        return [o for _s, o, _r in actions._advertisers(self.unit, need)]

    def test_an_unstaffed_bench_offers_nothing(self):
        with mock.patch("world.souls.posts.any_keeper_present",
                        return_value=False):
            self.assertEqual(self._found(), [])

    def test_a_staffed_bench_offers_the_repair(self):
        with mock.patch("world.souls.posts.any_keeper_present",
                        return_value=True):
            self.assertIn(self.bench, self._found())

    def test_an_ordinary_advertiser_is_unaffected(self):
        """Only benches opt in — a noodle cart does not need a keeper
        standing at it to smell of noodles."""
        self.bench.db.advertise_staffed = None
        self.bench.db.advertises = {"hunger": 0.9}
        self.assertIn(self.bench, self._found("hunger"))

    def test_an_unreadable_post_reads_as_unstaffed(self):
        """Fail closed: if we cannot tell whether anyone is there, the
        machine does not get to fix itself."""
        with mock.patch("world.souls.posts.any_keeper_present",
                        side_effect=RuntimeError("boom")):
            self.assertEqual(self._found(), [])


class TestTheMechanicsShift(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.mech = self.char1
        self.mech.db.soul_role = "mechanic"
        self.mech.db.soul_post = self.room1
        self.mech.location = self.room1
        self.unit = self.char2
        self.unit.location = self.room1
        self.unit.db.species = "robot"

    def _work(self):
        from world.souls import salience
        return salience.do_post_work(self.mech)

    def test_a_unit_overdue_gets_racked(self):
        with mock.patch("world.souls.needs.pressure", return_value=0.9), \
             mock.patch.object(type(self.mech), "execute_cmd") as ran:
            self._work()
        said = " ".join(str(c) for c in ran.call_args_list)
        self.assertIn("service hatch", said)

    def test_a_healthy_unit_is_left_alone(self):
        with mock.patch("world.souls.needs.pressure", return_value=0.1), \
             mock.patch.object(type(self.mech), "execute_cmd") as ran:
            self._work()
        ran.assert_not_called()

    def test_a_quiet_shift_is_a_fine_shift(self):
        """Nothing to service is normal. Most shifts will be."""
        self.unit.location = self.room2
        with mock.patch.object(type(self.mech), "execute_cmd") as ran:
            self._work()
        ran.assert_not_called()

    def test_it_does_not_re_rack_the_same_unit_every_beat(self):
        with mock.patch("world.souls.needs.pressure", return_value=0.9), \
             mock.patch.object(type(self.mech), "execute_cmd") as ran:
            self._work()
            self._work()
        self.assertEqual(ran.call_count, 1)

    def test_off_post_it_services_nobody(self):
        self.mech.location = self.room2
        with mock.patch("world.souls.needs.pressure", return_value=0.9), \
             mock.patch.object(type(self.mech), "execute_cmd") as ran:
            self._work()
        ran.assert_not_called()
