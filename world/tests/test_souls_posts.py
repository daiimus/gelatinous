"""The one post registry (#2132).

Coverage ported from the retired blueprint sweep, which had fourteen
tests while the system that actually runs succession had none. These
pin the behaviours that survived the merge: a held slot is left alone,
a dark one is stamped and then filled once its grace elapses, nobody
is seated over a live fight, resleeving restores the person, and an
unsouled cast member holds their post by standing in it.
"""
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.test_resources import BaseEvenniaTest

from world.souls import posts as postsmod


class _Slot(dict):
    """A post slot, readable the way sweep() reads one."""


def _post(room, shift="day", keeper=None, vacant_since=None,
          policy="successor", blueprint=None, delay=60):
    """A stand-in post fixture with just the surface sweep() touches."""
    db = SimpleNamespace(
        post_slots={shift: {"keeper": keeper, "vacant_since": vacant_since}},
        post_keeper=keeper,
        post_vacant_since=vacant_since,
        post_policy=policy,
        post_delay=delay,
        post_blueprints=({shift: blueprint} if blueprint else {}),
        post_blueprint=None,
        post_role="worker",
        post_wage_rate=0.02,
        register=None,
        post_insurer=None,
        post_memory_snapshots={},
        post_memory_snapshot=None,
    )
    return SimpleNamespace(db=db, location=room, key="a counter", id=999,
                           contents=[])


class TestSweepSlots(BaseEvenniaTest):
    """Vacancy stamping and the grace window."""

    def setUp(self):
        super().setUp()
        self.room = self.room1

    def _sweep(self, post, now, held=False, candidates=(), combat=False):
        with patch.object(postsmod, "get_posts", return_value=[post]), \
             patch.object(postsmod, "_slot_held", return_value=held), \
             patch.object(postsmod, "_eligible_candidates",
                          return_value=list(candidates)), \
             patch.object(postsmod, "_offer") as offer, \
             patch.object(postsmod, "_try_resleave",
                          return_value=True) as resleave, \
             patch("world.director.security._in_combat",
                   return_value=combat):
            postsmod.sweep(now=now)
        return offer, resleave

    def test_held_slot_is_left_alone(self):
        post = _post(self.room, keeper=self.char2)
        offer, resleave = self._sweep(post, now=1000.0, held=True)
        offer.assert_not_called()
        resleave.assert_not_called()

    def test_newly_dark_slot_is_stamped(self):
        post = _post(self.room)
        self._sweep(post, now=1000.0, held=False)
        self.assertEqual(post.db.post_slots["day"]["vacant_since"], 1000.0)

    def test_re_manned_slot_clears_its_stamp(self):
        post = _post(self.room, keeper=self.char2, vacant_since=500.0)
        self._sweep(post, now=1000.0, held=True)
        self.assertIsNone(post.db.post_slots["day"]["vacant_since"])

    def test_nothing_happens_before_the_grace_elapses(self):
        post = _post(self.room, vacant_since=990.0, delay=60)
        offer, resleave = self._sweep(post, now=1000.0,
                                      candidates=[self.char2])
        offer.assert_not_called()
        resleave.assert_not_called()

    def test_successor_seated_once_grace_elapses(self):
        post = _post(self.room, vacant_since=100.0, delay=60)
        offer, _ = self._sweep(post, now=1000.0, candidates=[self.char2])
        offer.assert_called_once()

    def test_nobody_is_seated_over_a_live_fight(self):
        post = _post(self.room, vacant_since=100.0, delay=60)
        offer, resleave = self._sweep(post, now=1000.0,
                                      candidates=[self.char2], combat=True)
        offer.assert_not_called()
        resleave.assert_not_called()

    def test_a_registered_blueprint_takes_the_resleeve_path(self):
        post = _post(self.room, vacant_since=100.0, delay=60,
                     blueprint="butcher_ottilie")
        offer, resleave = self._sweep(post, now=1000.0,
                                      candidates=[self.char2])
        resleave.assert_called_once()
        offer.assert_not_called()      # the person comes back, not a stranger


class TestSlotTenure(BaseEvenniaTest):
    """Who counts as still holding a post."""

    def test_souled_keeper_holds_by_assignment(self):
        self.char2.tags.add("soul", category="npc_role")
        self.char2.db.soul_post = self.room1
        self.char2.db.soul_schedule = "day"
        post = SimpleNamespace(db=SimpleNamespace(post_slots={}),
                               location=self.room1)
        self.assertTrue(postsmod._slot_held(
            post, "day", {"keeper": self.char2}))

    def test_souled_keeper_reassigned_frees_the_slot(self):
        self.char2.tags.add("soul", category="npc_role")
        self.char2.db.soul_post = self.room2
        self.char2.db.soul_schedule = "day"
        post = SimpleNamespace(db=SimpleNamespace(post_slots={}),
                               location=self.room1)
        self.assertFalse(postsmod._slot_held(
            post, "day", {"keeper": self.char2}))

    def test_unsouled_cast_hold_by_presence(self):
        """Vesper works her chaise without a needs engine. Reading her
        slot as vacant would resleeve a second Vesper beside her."""
        self.char2.location = self.room1
        post = SimpleNamespace(db=SimpleNamespace(post_slots={}),
                               location=self.room1)
        self.assertTrue(postsmod._slot_held(
            post, "swing", {"keeper": self.char2}))

    def test_a_dead_keeper_holds_nothing(self):
        post = SimpleNamespace(db=SimpleNamespace(post_slots={}),
                               location=self.room1)
        self.assertFalse(postsmod._slot_held(post, "day", {"keeper": None}))


class TestEstateAcrossDeath(BaseEvenniaTest):
    """The imprint: a resleeve restores what the post kept, minus the
    hours nobody remembers. Ported from the retired sweep's coverage."""

    def _post_with_imprint(self, snap):
        return SimpleNamespace(
            db=SimpleNamespace(
                post_blueprints={"day": "butcher_ottilie"},
                post_blueprint=None,
                post_memory_snapshots={"day": snap},
                post_memory_snapshot=None,
                register=1000, post_insurer=None,
                post_role="butcher", post_wage_rate=0.02,
                post_slots={"day": {"keeper": None, "vacant_since": 1.0}},
                post_keeper=None,
            ),
            location=self.room1, key="the block", id=998, contents=[])

    def test_resleeve_restores_the_imprint_minus_the_gap(self):
        died = 100000.0
        snap = {
            "name": "Ottilie Krug",
            "died_at": died,
            "memories": [{"created": died - 99999}, {"created": died - 60}],
            "dossiers": {"a regular": "buys offal"},
            "thoughts": [[died - 99999, "old"], [died - 60, "the killing"]],
        }
        post = self._post_with_imprint(snap)
        built = self.char2
        with patch.object(postsmod, "_archived_keeper", return_value=built), \
             patch.object(postsmod, "_install_keeper"), \
             patch("world.souls.thoughts.add_thought"):
            ok = postsmod._try_resleave(
                post, self.room1, "day", post.db.post_slots["day"], died)
        self.assertTrue(ok)
        # the last ~90 minutes never made the backup
        self.assertEqual(len(built.db.llm_memories), 1)
        self.assertEqual(built.db.llm_dossiers, {"a regular": "buys offal"})
        self.assertEqual(len(built.db.soul_thoughts), 1)

    def test_a_broke_till_cannot_pay_the_premium(self):
        post = self._post_with_imprint({"died_at": 1.0})
        post.db.register = 0
        with patch.object(postsmod, "_archived_keeper",
                          return_value=self.char2):
            ok = postsmod._try_resleave(
                post, self.room1, "day", post.db.post_slots["day"], 2.0)
        self.assertFalse(ok)      # it keeps earning toward her
