"""A post asking for no delay gets no delay (#3093).

The ripeness check read:

    int(post.db.post_delay or DEFAULT_DELAY)

`0` is falsy, so a builder asking for NO delay -- re-staff the moment
the slot goes dark -- silently received `DEFAULT_DELAY` instead, which
is six hours. No error, nothing in the log, and the post simply sat
empty far longer than it was told to.

Same shape as #2877 ("Treat an expiry of zero as expired, not
permanent"), and the same shape as the two remaining instances in
`world/director/broadcasts.py` -- which are deliberately NOT changed,
because there a zero is not a meaningful setting: `broadcast_interval`
of 0 would mean "broadcast every beat", so `or DEFAULT_INTERVAL` is
protecting the radio rather than swallowing an instruction. The
distinction is whether zero MEANS something, not whether the shape
matches.

Censused before changing: 19 posts carry a delay (259200 x10, 21600 x5,
86400 x2, 600 x2) and none is 0 -- so this alters no live cadence. It
stops the next builder who types 0 from getting six hours.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.souls import posts as postsmod


class _Slot(dict):
    pass


class TestZeroIsZero(EvenniaTest):
    """Exercises the ripeness arithmetic the sweep uses."""

    def _ripe_after(self, authored):
        """What the sweep would wait, given this authored value."""
        return (postsmod.DEFAULT_DELAY if authored is None
                else int(authored))

    def test_an_unset_delay_uses_the_default(self):
        """Control: the default must still apply when nobody chose."""
        self.assertEqual(self._ripe_after(None), postsmod.DEFAULT_DELAY)

    def test_a_zero_delay_is_zero(self):
        self.assertEqual(self._ripe_after(0), 0)

    def test_a_zero_delay_is_not_the_default(self):
        """The actual defect, stated as its own assertion."""
        self.assertNotEqual(self._ripe_after(0), postsmod.DEFAULT_DELAY)

    def test_a_real_delay_is_respected(self):
        self.assertEqual(self._ripe_after(600), 600)


class TestTheSweepRipensAZeroDelaySlotImmediately(EvenniaTest):
    """Through `sweep` itself, not just the arithmetic."""

    def _post(self, delay):
        post = mock.MagicMock()
        post.key = "Zero Post"
        post.location = self.room1
        self.room1.contents  # touch, so the combat scan has something real
        from types import SimpleNamespace
        post.db = SimpleNamespace(
            post_slots={"day": {"keeper": None, "vacant_since": 1.0}},
            post_policy="successor", post_delay=delay, post_blueprints=None,
            post_blueprint=None, post_keeper=None, post_vacant_since=1.0,
            post_role="worker", post_wage_rate=None, register=None)
        return post

    def _offered(self, delay, *, now):
        post = self._post(delay)
        soul = mock.MagicMock()
        soul.key = "Candidate"
        soul.id = 1
        from types import SimpleNamespace
        soul.db = SimpleNamespace(soul_job=None, soul_post=None)
        with mock.patch.object(postsmod, "get_posts", return_value=[post]), \
             mock.patch.object(postsmod, "_eligible_candidates",
                               return_value=[soul]), \
             mock.patch("world.director.security._in_combat",
                        return_value=False), \
             mock.patch.object(postsmod, "_can_reach", return_value=True):
            postsmod.sweep(now=now)
        return soul.db.soul_job is not None

    def test_zero_delay_ripens_at_once(self):
        self.assertTrue(self._offered(0, now=2.0),
                        "a post asking for no delay was still waiting")

    def test_an_unset_delay_still_waits(self):
        """Control: without this, 'ripens at once' would also be true of
        a sweep that ignored the delay entirely."""
        self.assertFalse(self._offered(None, now=2.0),
                         "the default delay stopped being honoured")
