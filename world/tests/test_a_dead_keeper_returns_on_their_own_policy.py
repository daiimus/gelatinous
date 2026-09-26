"""A dead keeper comes back on their own sleeve policy, or not at all
(#3667, Slice B).

The payout is keyed to the PERSON who died, never to the post: the
archived body is revived on a record that names that exact body, and
restored from its own imprint; a keeper who was never archived is rebuilt
only from a snapshot that is this namesake's own. Without a policy the
shift is nobody's and a successor may be hired. Souls walk to the lobby
terminal and buy their own.

Real objects throughout: the premise (a deleted reference reads back as
None, an archived body keeps its pk) is Evennia's, and a mock cannot show
it. The record store is `ServerConfig`; every test voids what it wrote.
"""
from types import SimpleNamespace
from unittest import mock

from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from world import imprint
from world.insurance import (policy_for, restore_policy, void_policy)
from world.souls import posts


def _kill(body):
    """A real medical death: the blood-loss floor (`_compute_is_dead`)."""
    ms = body.medical_state
    ms.blood_level = 0
    ms._cached_is_dead = None
    body.save_medical_state()              # as real damage does
    assert body.is_dead()


def _record(body, blueprint_key=None):
    return {"uid": body.sleeve_uid, "buyer_dbref": body.id, "bought_at": 0,
            "buyer_key": body.key, "blueprint_key": blueprint_key,
            "account_id": None}


class _Shift(EvenniaTest):
    """A registered post in room1 whose day shift is Marta's."""

    def setUp(self):
        super().setUp()
        self.post = self.obj1
        self.post.location = self.room1
        posts.register_post(self.post, role="doctor", schedule="day",
                            policy="successor", delay=0)
        self.post.db.post_blueprints = {"day": "doctor_marta"}
        self.marta = self.char2
        self.marta.db.blueprint_key = "doctor_marta"
        self.marta.db.essential = True
        self.marta.db.is_npc = True
        self.addCleanup(void_policy, self.marta.sleeve_uid)

    def dies_archived(self, died=1000.0):
        """Her death as the game leaves it: dead, own imprint, archived,
        slot keeper still pointing at the body."""
        _kill(self.marta)
        self.marta.db.imprint = imprint.capture(self.marta, died)
        self.marta.db.archived = True
        self.post.db.post_slots = {
            "day": {"keeper": self.marta, "vacant_since": 1.0}}
        return self.post.db.post_slots["day"]

    def install_stub(self):
        def install(npc, post, room, shift):
            slots = dict(post.db.post_slots or {})
            slots[shift] = {"keeper": npc, "vacant_since": None}
            post.db.post_slots = slots
        return install

    def attempt(self, slot, now=2000.0, install=None):
        with mock.patch.object(posts, "_install_keeper",
                               side_effect=install or self.install_stub()), \
             mock.patch("world.souls.thoughts.add_thought"), \
             mock.patch.object(type(self.marta), "execute_cmd"):
            return posts._try_resleave(self.post, self.room1, "day", slot, now)


class TheArchivedKeeper(_Shift):

    def test_with_a_policy_she_comes_back_and_the_policy_is_spent(self):
        slot = self.dies_archived()
        restore_policy(_record(self.marta, "doctor_marta"))
        self.assertEqual(self.attempt(slot), posts.RESLEEVED)
        self.assertIsNone(policy_for(self.marta.sleeve_uid))
        self.assertFalse(self.marta.is_archived)
        self.assertEqual(self.post.db.post_slots["day"]["keeper"], self.marta)

    def test_without_a_policy_the_shift_is_a_successors(self):
        slot = self.dies_archived()
        self.assertEqual(self.attempt(slot), posts.SUCCESSOR)
        self.assertTrue(self.marta.is_archived, "touched without a policy")

    def test_another_bodys_record_does_not_pay_for_her(self):
        slot = self.dies_archived()
        restore_policy({**_record(self.marta), "buyer_dbref": self.char1.id})
        self.assertEqual(self.attempt(slot), posts.SUCCESSOR)
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid), "spent someone else's")

    def test_while_she_is_still_on_the_table_the_sweep_waits(self):
        # Dead, progression running, NOT yet archived: the game's real
        # dying state. Neither a return nor a successor may touch it.
        _kill(self.marta)
        self.marta.db.death_processed = True
        create_script("typeclasses.scripts.Script", key="death_progression",
                      obj=self.marta, autostart=False)
        slot = {"keeper": self.marta, "vacant_since": 1.0}
        restore_policy(_record(self.marta, "doctor_marta"))
        self.assertEqual(self.attempt(slot), posts.HOLD)
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid))
        self.assertEqual(self.post.db.post_blueprints, {"day": "doctor_marta"})

    def test_dead_and_not_yet_archived_with_no_progression_is_still_waiting(self):
        # A wedged death: death completed, the boot sweep will archive it.
        _kill(self.marta)
        self.marta.db.death_processed = True
        slot = {"keeper": self.marta, "vacant_since": 1.0}
        self.assertEqual(self.attempt(slot), posts.HOLD)

    def test_a_failed_return_puts_everything_back_as_it_was(self):
        """The body was healed before the failure; it must read DEAD and
        archived again, or the sweep reads a live body in Limbo as a held
        slot forever (review of #3667 Slice B)."""
        slot = self.dies_archived()
        restore_policy(_record(self.marta, "doctor_marta"))

        def broken(npc, post, room, shift):
            raise RuntimeError("the post refused her")
        self.assertEqual(self.attempt(slot, install=broken), posts.HOLD)
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid), "the record was burnt")
        self.assertTrue(self.marta.is_archived)
        self.assertTrue(self.marta.is_dead(), "revived body left alive in Limbo")
        self.assertTrue(self.marta.db.death_processed)
        self.assertFalse(posts._slot_held(self.post, "day",
                                          self.post.db.post_slots["day"]))
        self.assertEqual(self.post.db.post_slots["day"]["return_failures"], 1)

    def test_three_failed_returns_give_the_shift_up(self):
        slot = self.dies_archived()
        restore_policy(_record(self.marta, "doctor_marta"))

        def broken(npc, post, room, shift):
            raise RuntimeError("the post refused her")
        outcomes = [self.attempt(self.post.db.post_slots["day"], install=broken)
                    for _ in range(posts.RETURN_ATTEMPTS)]
        self.assertEqual(outcomes, [posts.HOLD] * (posts.RETURN_ATTEMPTS - 1)
                         + [posts.SUCCESSOR])
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid), "spent on a failure")

    def test_an_archived_body_never_holds_a_slot(self):
        self.dies_archived()
        self.marta.db.soul_post = self.room1
        self.marta.db.soul_schedule = "day"
        from world.souls import engine
        self.marta.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])
        self.assertFalse(posts._slot_held(self.post, "day",
                                          {"keeper": self.marta, "vacant_since": 1.0}))

    def test_the_slot_keeper_lost_but_the_stamp_kept_still_finds_her(self):
        # The sweep stamps dead_id when the slot goes dark; the keeper
        # reference may read None later. The stamp finds the body.
        self.dies_archived()
        slot = {"keeper": None, "vacant_since": 1.0,
                "dead_uid": self.marta.sleeve_uid, "dead_id": self.marta.id}
        restore_policy(_record(self.marta, "doctor_marta"))
        self.assertEqual(self.attempt(slot), posts.RESLEEVED)

    def test_a_stamp_naming_a_body_that_is_gone_does_not_fall_back_to_a_namesake(self):
        # A stamped dead_id that no longer resolves (a deleted body) must
        # not let some OTHER archived body of the blueprint pay out here.
        self.dies_archived()
        if self.room2.id == 2:
            self.marta.location = self.room2
        slot = {"keeper": None, "vacant_since": 1.0,
                "dead_uid": "someone", "dead_id": 10 ** 8}
        restore_policy(_record(self.marta, "doctor_marta"))
        self.assertEqual(self.attempt(slot), posts.SUCCESSOR)
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid))

    def test_a_shift_vacated_before_the_stamp_existed_finds_the_archived_body(self):
        self.dies_archived()
        self.marta.location = self.room2 if self.room2.id == 2 else self.marta.location
        slot = {"keeper": None, "vacant_since": 1.0}
        restore_policy(_record(self.marta, "doctor_marta"))
        # Limbo is object #2; only when the fixture's room2 is #2 can this
        # path be driven, which is the harness's own arrangement.
        if self.room2.id != 2:
            self.skipTest("room2 is not object #2 in this harness")
        self.assertEqual(self.attempt(slot), posts.RESLEEVED)

    def test_her_own_imprint_is_restored_not_the_shifts_snapshot(self):
        died = 1000.0
        self.marta.db.llm_dossiers = {"a regular": "hers"}
        slot = self.dies_archived(died)
        self.post.db.post_memory_snapshots = {"day": {
            "name": "a successor", "died_at": died,
            "dossiers": {"stranger": "theirs"}, "blueprint_key": None}}
        restore_policy(_record(self.marta, "doctor_marta"))
        self.assertEqual(self.attempt(slot), posts.RESLEEVED)
        self.assertEqual(self.marta.db.llm_dossiers, {"a regular": "hers"})


class TheRebuiltKeeper(_Shift):
    """No archived body: only this namesake's own snapshot may rebuild."""

    def setUp(self):
        super().setUp()
        self.slot = {"keeper": None, "vacant_since": 1.0}
        self.marta.db.essential = False      # no archived body anywhere
        _kill(self.marta)                    # and no living one either

    def snapshot(self, **over):
        snap = imprint.capture(self.marta, 1000.0)
        snap.update(over)
        self.post.db.post_memory_snapshots = {"day": snap}
        return snap

    def build_stub(self):
        def build(bp_key, room):
            npc = create_object("typeclasses.characters.Character",
                                key="Marta (rebuilt)", location=room)
            npc.db.blueprint_key = bp_key
            return npc
        return build

    def attempt_rebuild(self, build=None):
        with mock.patch("world.npcs.blueprints.build_npc",
                        side_effect=build or self.build_stub()):
            return self.attempt(self.slot)

    def test_her_own_snapshot_and_policy_rebuild_her(self):
        snap = self.snapshot()
        self.assertEqual(snap["blueprint_key"], "doctor_marta")
        self.assertEqual(snap["dbref"], self.marta.id)
        restore_policy(_record(self.marta, "doctor_marta"))
        self.assertEqual(self.attempt_rebuild(), posts.RESLEEVED)
        self.assertIsNone(policy_for(self.marta.sleeve_uid))

    def test_a_successors_snapshot_cannot_rebuild_the_namesake(self):
        # A hired successor died on the shift last; the snapshot is theirs.
        self.snapshot(blueprint_key=None, dbref=self.char1.id,
                      sleeve_uid=self.char1.sleeve_uid)
        restore_policy({**_record(self.char1), "buyer_dbref": self.char1.id})
        self.addCleanup(void_policy, self.char1.sleeve_uid)
        self.assertEqual(self.attempt_rebuild(), posts.SUCCESSOR)
        self.assertIsNotNone(policy_for(self.char1.sleeve_uid), "spent the successor's")

    def test_no_snapshot_no_rebuild(self):
        restore_policy(_record(self.marta, "doctor_marta"))
        self.assertEqual(self.attempt_rebuild(), posts.SUCCESSOR)
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid))

    def test_a_rebuild_whose_install_fails_deletes_the_body_and_restores_the_record(self):
        self.snapshot()
        restore_policy(_record(self.marta, "doctor_marta"))
        built = []

        def build(bp_key, room):
            npc = create_object("typeclasses.characters.Character",
                                key="Marta (rebuilt)", location=room)
            npc.db.blueprint_key = bp_key
            built.append(npc)
            return npc

        def broken(npc, post, room, shift):
            raise RuntimeError("no cube, no soul")
        with mock.patch("world.npcs.blueprints.build_npc", side_effect=build):
            outcome = self.attempt(self.slot, install=broken)
        self.assertEqual(outcome, posts.HOLD)
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid), "spent on a failure")
        self.assertFalse(built[0].pk, "the half-built body was left standing")

    def test_a_stamped_slot_rebuilds_only_the_stamped_body(self):
        snap = self.snapshot()
        restore_policy(_record(self.marta, "doctor_marta"))
        self.slot["dead_id"] = snap["dbref"] + 1        # somebody else died here
        self.assertEqual(self.attempt_rebuild(), posts.SUCCESSOR)
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid))

    def test_a_blueprint_that_raises_leaves_the_policy_unspent(self):
        self.snapshot()
        restore_policy(_record(self.marta, "doctor_marta"))

        def broken(bp_key, room):
            raise ValueError("bad identity vocabulary")
        self.assertEqual(self.attempt_rebuild(build=broken), posts.SUCCESSOR)
        self.assertIsNotNone(policy_for(self.marta.sleeve_uid))


class TheSweepStampsWhoDied(_Shift):

    def test_a_newly_dark_slot_records_the_keepers_uid_and_id(self):
        _kill(self.marta)
        self.marta.db.archived = True
        self.post.db.post_slots = {"day": {"keeper": self.marta,
                                           "vacant_since": None}}
        with mock.patch.object(posts, "_slot_held", return_value=False), \
             mock.patch.object(posts, "get_posts", return_value=[self.post]):
            posts.sweep(now=5.0)
        slot = self.post.db.post_slots["day"]
        self.assertEqual(slot["dead_uid"], self.marta.sleeve_uid)
        self.assertEqual(slot["dead_id"], self.marta.id)

    def test_re_manning_clears_the_stamp(self):
        self.post.db.post_slots = {"day": {
            "keeper": self.marta, "vacant_since": 1.0,
            "dead_uid": "x", "dead_id": 1}}
        with mock.patch.object(posts, "_slot_held", return_value=True), \
             mock.patch.object(posts, "get_posts", return_value=[self.post]):
            posts.sweep(now=5.0)
        slot = self.post.db.post_slots["day"]
        self.assertNotIn("dead_uid", slot)
        self.assertIsNone(slot["vacant_since"])


class TheSoulGoesToBuy(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.soul = self.char2
        self.addCleanup(void_policy, self.soul.sleeve_uid)

    def test_uninsured_is_a_soft_want_insured_is_none(self):
        from world.souls import needs
        self.assertEqual(needs.insurance_pressure(self.soul), needs.INSURANCE_PRESSURE)
        # Exactly SOFT: elected, but yielding to any need that has risen.
        self.assertEqual(needs.INSURANCE_PRESSURE, needs.SOFT)
        self.assertLess(needs.INSURANCE_PRESSURE, needs.CRITICAL)
        restore_policy(_record(self.soul))
        self.assertEqual(needs.insurance_pressure(self.soul), 0.0)

    def test_the_arbitration_reads_the_derived_value(self):
        # pressures()/pressure() must route 'insurance' to insurance_pressure,
        # or the need reads its stored 0.0 forever and nobody ever buys.
        from world.souls import needs
        self.soul.db.soul_species = "human"
        self.assertEqual(needs.pressures(self.soul)["insurance"],
                         needs.INSURANCE_PRESSURE)
        self.assertEqual(needs.pressure(self.soul, "insurance"),
                         needs.INSURANCE_PRESSURE)

    def test_a_meal_that_has_risen_beats_the_errand(self):
        from world.souls import engine, needs
        self.soul.db.soul_species = "human"
        with mock.patch.object(needs, "pressures", return_value={
                "hunger": needs.SOFT + 0.01, "rest": 0.0, "craving": 0.0,
                "wardrobe": 0.0, "social": 0.0, "health": 0.0,
                "insurance": needs.INSURANCE_PRESSURE, "safety": 0.0}):
            self.assertEqual(engine._desired_goal(self.soul, 12), (3, "hunger"))

    def test_a_body_with_no_sleeve_signature_never_wants_one(self):
        from world.souls import needs
        self.soul.sleeve_uid = None
        self.assertEqual(needs.insurance_pressure(self.soul), 0.0)

    def test_human_and_synth_profiles_carry_the_need_robots_and_recluses_do_not(self):
        from world.souls import needs
        self.assertIn("insurance", needs.PROFILES["human"])
        self.assertIn("insurance", needs.PROFILES["synth"])
        self.assertNotIn("insurance", needs.PROFILES["robot"])
        self.assertNotIn("insurance", needs.PROFILES["recluse"])

    def test_the_plan_walks_to_the_terminal_and_presses_the_buy_button(self):
        from typeclasses.terminals import InsuranceTerminal
        from world.souls import actions, engine
        term = create_object("typeclasses.terminals.InsuranceTerminal",
                             key="a Thawn-Harrison policy terminal",
                             location=self.room2)
        job = actions.plan_for(self.soul, "insurance")
        self.assertEqual([s["do"] for s in job["steps"]],
                         ["travel", "press", "insured"])
        self.assertEqual(job["steps"][0]["room"], self.room2.id)
        self.assertEqual(job["steps"][1]["fixture"], term.id)
        self.assertEqual(job["steps"][1]["button"], InsuranceTerminal.BUY_BUTTON)
        self.assertEqual(engine._goal_band("insurance"), 3)

    def test_no_terminal_no_plan(self):
        from world.souls import actions
        self.assertIsNone(actions.plan_for(self.soul, "insurance"))

    def test_the_press_step_names_the_button(self):
        from world.souls import jobs
        term = create_object("typeclasses.terminals.InsuranceTerminal",
                             key="a Thawn-Harrison policy terminal",
                             location=self.room1)
        self.soul.db.soul_job = {"goal": "insurance", "at": 0, "steps": [
            {"do": "press", "fixture": term.id, "button": "insure"}]}
        with mock.patch.object(type(self.soul), "execute_cmd") as run:
            jobs.step_job(self.soul)
        run.assert_called_once_with("press insure on a Thawn-Harrison policy terminal")

    def test_the_insured_step_faults_when_the_press_bought_nothing(self):
        from world.souls import jobs
        self.soul.db.soul_job = {"goal": "insurance", "at": 0,
                                 "steps": [{"do": "insured"}]}
        with mock.patch.object(jobs, "fault") as faulted:
            jobs.step_job(self.soul)
        self.assertTrue(faulted.called)
        self.assertIn("no policy is on file", faulted.call_args.args[1])

    def test_the_insured_step_advances_once_covered(self):
        from world.souls import jobs
        restore_policy(_record(self.soul))
        self.soul.db.soul_job = {"goal": "insurance", "at": 0,
                                 "steps": [{"do": "insured"}]}
        with mock.patch.object(jobs, "fault") as faulted:
            jobs.step_job(self.soul)
        self.assertFalse(faulted.called)
        self.assertEqual((self.soul.db.soul_job or {}).get("at", 1), 1)


class TheOldModelIsGone(EvenniaTest):

    def test_no_till_pays_and_no_post_labels_a_return(self):
        import inspect
        src = inspect.getsource(posts)
        for gone in ("RESLEAVE_PREMIUM", "post_insurer", "resleeve_premium",
                     "billing terminal", "_archived_keeper"):
            self.assertNotIn(gone, src, gone)
        self.assertNotIn('"resleave"', src)
