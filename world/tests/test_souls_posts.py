"""The one post registry (#2132).

Coverage ported from the retired blueprint sweep, which had fourteen
tests while the system that actually runs succession had none. These
pin the behaviours that survived the merge: a held slot is left alone,
a dark one is stamped and then filled once its grace elapses, nobody
is seated over a live fight, resleeving restores the person, and a
post keeper is a soul.
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
        post_role="worker",
        post_wage_rate=0.02,
        register=None,
        post_memory_snapshots={},
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
                          return_value=postsmod.RESLEEVED) as resleave, \
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

    def test_an_unsouled_keeper_holds_nothing(self):
        """A post keeper is a soul — an invariant now, not a hope.

        This used to be the reverse: an unsouled cast member held a slot
        by standing in it, because Vesper worked her chaise without a
        needs engine and reading her slot as vacant would have resleeved
        a second Vesper beside her (#2132). She was the only body it was
        ever for and she has a soul now (#2362), so an unsouled keeper
        is a build error and the slot correctly reads vacant."""
        self.char2.location = self.room1
        post = SimpleNamespace(db=SimpleNamespace(post_slots={}),
                               location=self.room1)
        self.assertFalse(postsmod._slot_held(
            post, "swing", {"keeper": self.char2}))

    def test_a_dead_keeper_holds_nothing(self):
        post = SimpleNamespace(db=SimpleNamespace(post_slots={}),
                               location=self.room1)
        self.assertFalse(postsmod._slot_held(post, "day", {"keeper": None}))


class TestEstateAcrossDeath(BaseEvenniaTest):
    """The imprint: a return restores the person's OWN record, minus the
    hours nobody remembers, and only when their sleeve policy pays
    (#3667). Ported from the retired sweep's coverage."""

    def setUp(self):
        super().setUp()
        # The base harness's char2 is a vanilla DefaultCharacter with no
        # sleeve uid; the body here is the game's own Character.
        from evennia import create_object
        from world.insurance import void_policy
        self.body = create_object("typeclasses.characters.Character",
                                  key="Ottilie Krug", location=self.room1)
        self.addCleanup(void_policy, self.body.sleeve_uid)

    def _post_with_keeper(self, keeper):
        return SimpleNamespace(
            db=SimpleNamespace(
                post_blueprints={"day": "butcher_ottilie"},
                post_memory_snapshots={},
                register=None,
                post_role="butcher", post_wage_rate=0.02,
                post_slots={"day": {"keeper": keeper, "vacant_since": 1.0}},
                post_keeper=None,
            ),
            location=self.room1, key="the block", id=998, contents=[])

    def _archived(self, died, snap):
        """Ottilie's archived body: dead, her own imprint on it."""
        body = self.body
        ms = body.medical_state
        ms.blood_level = 0                   # a real medical death
        ms._cached_is_dead = None
        body.db.blueprint_key = "butcher_ottilie"
        body.db.essential = True
        body.db.is_npc = True
        body.db.archived = True
        body.db.imprint = snap
        return body

    def _install_stub(self, post):
        def install(npc, post_, room, shift):
            slots = dict(post.db.post_slots)
            slots[shift] = {"keeper": npc, "vacant_since": None}
            post.db.post_slots = slots
        return install

    def test_a_return_restores_her_own_imprint_minus_the_gap(self):
        from world.insurance import policy_for, restore_policy
        died = 100000.0
        body = self._archived(died, {
            "name": "Ottilie Krug", "sleeve_uid": self.body.sleeve_uid,
            "died_at": died,
            "memories": [{"created": died - 99999}, {"created": died - 60}],
            "dossiers": {"a regular": "buys offal"},
            "thoughts": [[died - 99999, "old"], [died - 60, "the killing"]],
        })
        post = self._post_with_keeper(body)
        restore_policy({"uid": body.sleeve_uid, "buyer_dbref": body.id,
                        "bought_at": 0, "buyer_key": body.key,
                        "blueprint_key": "butcher_ottilie", "account_id": None})
        with patch.object(postsmod, "_install_keeper",
                          side_effect=self._install_stub(post)), \
             patch("world.souls.thoughts.add_thought"):
            outcome = postsmod._try_resleave(
                post, self.room1, "day", post.db.post_slots["day"], died)
        self.assertEqual(outcome, postsmod.RESLEEVED)
        # the last ~90 minutes never made the backup
        self.assertEqual(len(body.db.llm_memories), 1)
        self.assertEqual(body.db.llm_dossiers, {"a regular": "buys offal"})
        self.assertEqual(len(body.db.soul_thoughts), 1)
        self.assertIsNone(policy_for(body.sleeve_uid), "the policy was not spent")
        self.assertFalse(body.is_archived)

    def test_no_policy_means_nobody_comes_back(self):
        body = self._archived(2.0, {"died_at": 1.0})
        post = self._post_with_keeper(body)
        outcome = postsmod._try_resleave(
            post, self.room1, "day", post.db.post_slots["day"], 2.0)
        self.assertEqual(outcome, postsmod.SUCCESSOR)
        self.assertTrue(body.is_archived, "the body was touched without a policy")

    def test_another_bodys_policy_does_not_pay_for_her(self):
        from world.insurance import policy_for, restore_policy
        body = self._archived(2.0, {"died_at": 1.0})
        post = self._post_with_keeper(body)
        restore_policy({"uid": body.sleeve_uid, "buyer_dbref": self.char1.id,
                        "bought_at": 0, "buyer_key": "someone else",
                        "blueprint_key": None, "account_id": None})
        outcome = postsmod._try_resleave(
            post, self.room1, "day", post.db.post_slots["day"], 2.0)
        self.assertEqual(outcome, postsmod.SUCCESSOR)
        self.assertIsNotNone(policy_for(body.sleeve_uid), "another body's record was spent")


class TestSweepDoesNotRevertAResleave(BaseEvenniaTest):
    """`sweep` must not write its snapshot over an install (#2802).

    `sweep` takes `slots = dict(post.db.post_slots or {})` at the top of
    each post, then calls `_try_resleave` — which reaches
    `_install_keeper`, and that re-reads `post_slots`, records the new
    keeper and persists it. Writing the loop's snapshot afterwards put
    the vacancy straight back, so a keeper who had just been installed
    and emoted "back at the post" left the slot reading empty.
    """

    def setUp(self):
        super().setUp()
        self.room = self.room1

    def test_the_installed_keeper_survives_the_sweep(self):
        post = _post(self.room, shift="day", keeper=None,
                     vacant_since=1.0, policy="successor", blueprint="bp-1")

        def _install_like_the_real_thing(*_a, **_kw):
            # what _install_keeper does: re-read, record, persist
            slots = dict(post.db.post_slots or {})
            slots["day"] = {"keeper": self.char2, "vacant_since": None}
            post.db.post_slots = slots
            return postsmod.RESLEEVED

        with patch.object(postsmod, "get_posts", return_value=[post]), \
             patch.object(postsmod, "_slot_held", return_value=False), \
             patch.object(postsmod, "_living_body", return_value=None), \
             patch.object(postsmod, "_eligible_candidates", return_value=[]), \
             patch.object(postsmod, "_try_resleave",
                          side_effect=_install_like_the_real_thing), \
             patch("world.director.security._in_combat", return_value=False):
            postsmod.sweep(now=10_000.0)

        self.assertEqual(post.db.post_slots["day"]["keeper"], self.char2,
                         "sweep reverted the keeper _install_keeper had just set")
        self.assertIsNone(post.db.post_slots["day"]["vacant_since"])
