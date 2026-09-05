"""An advertiser attribute without the tag is a build error, not
invisibility (#2697).

The tag is the INDEX -- hardening spec law 3, never an attribute-key
query on a hot path -- and nothing reconciled the two. So a fixture with
`db.advertises` and no tag was SILENTLY INVISIBLE to the planner rather
than merely slow to find.

A purpose-built charging rack sat dead from the day it was built:
`scripts/builds/121_the_charging_rack.py` sets the attribute and is the
one advertiser build that never calls `tags.add`, and the backfill
migration ran BEFORE it, so it could not have caught it.

It survived because the loss is a LOCATION, not a behaviour. A second
charge advertiser is reachable from every unit, so nothing faulted and
no alarm sounded -- which is exactly why nobody noticed for as long as
the rack has existed.
"""
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import actions


class TestStraysAreAdopted(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        actions._ad_cache["at"] = 0.0
        actions._ad_cache["objs"] = []
        self.addCleanup(lambda: actions._ad_cache.update({"at": 0.0,
                                                          "objs": []}))

    def _fixture(self, key, tagged):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=self.room1)
        obj.db.advertises = {"charge": 0.9}
        if tagged:
            obj.tags.add("advertiser", category="souls")
        return obj

    def test_an_untagged_advertiser_is_adopted(self):
        stray = self._fixture("a charging rack", tagged=False)
        with mock.patch("evennia.utils.logger.log_warn"):
            objs = actions._advertiser_objs()
        self.assertIn(stray, objs)
        self.assertTrue(stray.tags.get("advertiser", category="souls"))

    def test_the_adoption_is_logged(self):
        """It is a build error, so it should be findable in the log —
        silence is what let this survive."""
        self._fixture("a charging rack", tagged=False)
        with mock.patch("evennia.utils.logger.log_warn") as warned:
            actions._advertiser_objs()
        self.assertTrue(warned.called)
        self.assertIn("advertiser tag missing", warned.call_args.args[0])

    def test_a_correctly_tagged_advertiser_is_not_re_logged(self):
        """The pin: this must be quiet in the normal case, or it becomes
        noise on every cache expiry."""
        self._fixture("a fleet cradle", tagged=True)
        with mock.patch("evennia.utils.logger.log_warn") as warned:
            actions._advertiser_objs()
        self.assertFalse(warned.called)

    def test_an_object_with_no_advertises_is_left_alone(self):
        plain = create_object("typeclasses.items.Item", key="a crate",
                              location=self.room1)
        with mock.patch("evennia.utils.logger.log_warn"):
            objs = actions._advertiser_objs()
        self.assertNotIn(plain, objs)
        self.assertFalse(plain.tags.get("advertiser", category="souls"))

    def test_a_tagged_advertiser_still_appears(self):
        cradle = self._fixture("a fleet cradle", tagged=True)
        with mock.patch("evennia.utils.logger.log_warn"):
            self.assertIn(cradle, actions._advertiser_objs())

    def test_a_broken_sweep_never_raises(self):
        """Planning matters more than the reconciliation, so a failure
        here is swallowed.

        Tested on the reconcile directly. My first version patched
        `ObjectDB.objects.filter`, which `search_tag` also goes through
        — so it broke the index lookup rather than the sweep and proved
        nothing about either.
        """
        tagged = []
        with mock.patch("evennia.objects.models.ObjectDB.objects.filter",
                        side_effect=RuntimeError("db down")):
            actions._reconcile_advertiser_tags(tagged)   # must not raise
        self.assertEqual(tagged, [])
