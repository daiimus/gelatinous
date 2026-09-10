"""One unroutable neighbour must not starve every other dark post.

#2332 taught `_offer` to REFUSE a post the soul cannot walk to -- the
Rook was being offered the Helix Lounge from inside his sealed basement
studio and re-took it every three minutes forever. That fix is right.

What it did not do is tell the CALLER. `sweep()` hires at most one
keeper per beat, and it spends that budget like this:

    _offer(candidates[0], post, room, shift)
    if dirty:
        post.db.post_slots = slots
    return                                   # one per sweep

Before #2332 `_offer` always set the job, so consuming the sweep was a
fair trade. Now it can silently do nothing -- and the `return` fires
anyway. Both orderings are deterministic (`_eligible_candidates` sorts
on `(distance, id)`, `get_posts()` is a tag search), so the next sweep
picks the same post and the same unreachable candidate and burns
itself again, forever.

Measured against the live colony before this was written: 3 of 19 posts
had a nearest candidate who could not reach them --

    Colonial Constabulary Dispatch  <- Ethel Kaufman, Spillane Corridor
    The Brackett Arms - Lobby       <- the Rook, Utility Room (sealed)
    a Boiler Run service bench      <- Ethel Kaufman, Spillane Corridor

-- so the moment any one of those goes dark, hiring stops colony-wide.
The Rook is the same soul #2332 was written about; he is unemployed, so
he is an eligible candidate, and he cannot leave.

Two rules here, and the second is the one that bites:
  * offer down the list, not only to the nearest;
  * a refusal is not a hire, so it must not end the sweep.
"""
from types import SimpleNamespace
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.souls import posts as postsmod


class _Room(SimpleNamespace):
    """A room the sweep can look into; `contents` is read for the
    never-hire-over-a-fight check."""


def _post(key, room, shift="day"):
    post = mock.MagicMock()
    post.key = key
    post.location = room
    post.db = SimpleNamespace(
        # `post_delay=1` here for historical reasons: the ripeness
        # check used to read `int(post.db.post_delay or DEFAULT_DELAY)`,
        # so 0 was falsy and silently became the DEFAULT delay, and the
        # slot never ripened. That cost an hour of chasing a fix that
        # was already correct. Fixed in #3093 -- 0 now means 0 -- but
        # this fixture is left at 1 because it is testing hiring, not
        # ripeness, and rewriting it would only re-prove #3093.
        post_slots={shift: {"keeper": None, "vacant_since": 1.0}},
        post_policy="successor", post_delay=1, post_blueprints=None,
        post_blueprint=None, post_keeper=None, post_vacant_since=1.0,
        post_role="worker", post_wage_rate=None, register=None)
    return post


def _soul(key, soul_id):
    soul = mock.MagicMock()
    soul.key = key
    soul.id = soul_id
    soul.db = SimpleNamespace(soul_job=None, soul_post=None)
    return soul


class TestOfferReportsWhetherItHired(EvenniaTest):
    """`_offer` has to SAY whether it took the job, or no caller can
    tell a hire from a refusal."""

    def test_a_reachable_soul_is_hired_and_says_so(self):
        room = _Room(id=7, contents=[])
        soul = _soul("Reachable", 1)
        with mock.patch.object(postsmod, "_can_reach", return_value=True):
            took = postsmod._offer(soul, _post("P", room), room, "day")
        self.assertTrue(took)
        self.assertIsNotNone(soul.db.soul_job)

    def test_an_unreachable_soul_is_not_hired_and_says_so(self):
        room = _Room(id=7, contents=[])
        soul = _soul("Sealed In", 1)
        with mock.patch.object(postsmod, "_can_reach", return_value=False):
            took = postsmod._offer(soul, _post("P", room), room, "day")
        self.assertFalse(took)
        self.assertIsNone(soul.db.soul_job)


class TestTheSweepDoesNotBurnItselfOnARefusal(EvenniaTest):

    def _run_sweep(self, posts, candidates, reachable):
        """Drive the real `sweep()` over mocked posts/candidates."""
        with mock.patch.object(postsmod, "get_posts", return_value=posts), \
             mock.patch.object(postsmod, "_eligible_candidates",
                               return_value=candidates), \
             mock.patch("world.director.security._in_combat",
                        return_value=False), \
             mock.patch.object(postsmod, "_can_reach",
                               side_effect=lambda s, r: s in reachable):
            postsmod.sweep(now=10_000.0)

    def test_it_offers_past_a_candidate_who_cannot_get_there(self):
        """The nearest soul is sealed in; the next one takes the job."""
        room = _Room(id=7, contents=[])
        sealed, walker = _soul("the Rook", 1), _soul("Ethel", 2)
        self._run_sweep([_post("Lobby", room)], [sealed, walker], {walker})
        self.assertIsNone(sealed.db.soul_job)
        self.assertIsNotNone(
            walker.db.soul_job,
            "the sweep stopped at the unreachable nearest candidate")

    def test_a_post_nobody_can_reach_does_not_starve_the_next_post(self):
        """THE STARVATION. Post A's only candidate cannot reach it.
        Post B's candidate can. B must still be hired this sweep."""
        room_a = _Room(id=7, contents=[])
        room_b = _Room(id=8, contents=[])
        sealed, walker = _soul("the Rook", 1), _soul("Ethel", 2)

        def candidates_for(room):
            return [sealed] if room is room_a else [walker]

        posts = [_post("Brackett Lobby", room_a), _post("Boiler Bench", room_b)]
        with mock.patch.object(postsmod, "get_posts", return_value=posts), \
             mock.patch.object(postsmod, "_eligible_candidates",
                               side_effect=candidates_for), \
             mock.patch("world.director.security._in_combat",
                        return_value=False), \
             mock.patch.object(postsmod, "_can_reach",
                               side_effect=lambda s, r: s is walker):
            postsmod.sweep(now=10_000.0)

        self.assertIsNone(sealed.db.soul_job)
        self.assertIsNotNone(
            walker.db.soul_job,
            "one unreachable candidate at an earlier post ended the whole "
            "sweep -- every later dark post starves, every beat, forever")
