"""A destroyed unit is disarmed before it is discarded (#2284).

    destroyed → remains taken to the constabulary
              → weapon arm module removed
              → disposed of in the junkyard

A unit's weapon is an augment ORGAN seated in its right arm, not a
carried item. So a wreck nobody strips is a working shotgun lying
around — and this game harvests organs and chrome, which means the
colony's own security force is a weapons supply if nobody comes for
the bodies.

Owner: *"The shotgun arm module is what needs to be removed."* The
module, not the limb. A stripped chassis keeps its arms.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.director import disposal


class TestStripAndJunk(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.unit = self.char1
        self.wreck = self.char2
        self.wreck.db.species = "robot"
        self.wreck.db.role = "security"

    def test_the_module_comes_off(self):
        with mock.patch("world.medical.procedures.strip_organ") as strip:
            strip.return_value = object()
            out = disposal.strip_and_junk(self.unit, self.wreck)
        self.assertIsNotNone(out["module"])
        self.assertEqual(strip.call_args.args[1], "integrated_shotgun_module")

    def test_the_limb_stays_on(self):
        """The module, not the arm (owner, 2026-08-24). Asserted on a
        real body below in TestOnARealBody — a string constant proves
        nothing about what the strip actually does."""
        self.assertEqual(disposal.ARMAMENT, "integrated_shotgun_module")

    def test_the_module_lands_where_the_actor_is(self):
        """It stays at the precinct. Sending it to the yard with the
        chassis would put a shotgun in the junkyard, which is the
        exact outcome this errand exists to prevent."""
        with mock.patch("world.medical.procedures.strip_organ") as strip:
            disposal.strip_and_junk(self.unit, self.wreck)
        self.assertIs(strip.call_args.kwargs["into"], self.unit.location)

    def test_the_chassis_goes_to_the_yard(self):
        self.room2.tags.add(*disposal.SCRAPYARD_TAG)
        with mock.patch("world.medical.procedures.strip_organ",
                        return_value=None):
            out = disposal.strip_and_junk(self.unit, self.wreck)
        self.assertTrue(out["junked"])
        self.assertIs(self.wreck.location, self.room2)

    def test_the_chassis_persists(self):
        """Owner ruling: it stays as an object — feedstock for the
        Ripper's cold room, and the yard accumulates a history of the
        force's bad nights."""
        self.room2.tags.add(*disposal.SCRAPYARD_TAG)
        with mock.patch("world.medical.procedures.strip_organ",
                        return_value=None):
            disposal.strip_and_junk(self.unit, self.wreck)
        self.assertTrue(self.wreck.pk, "the chassis was deleted, not junked")


class TestDisarmingBeatsTidying(EvenniaCommandTest):
    """Order is deliberate: the gun comes off first. If anything later
    fails, the colony has still recovered its shotgun."""

    def setUp(self):
        super().setUp()
        self.wreck = self.char2
        self.wreck.db.species = "robot"

    def test_no_yard_still_disarms(self):
        with mock.patch("world.medical.procedures.strip_organ") as strip:
            strip.return_value = object()
            out = disposal.strip_and_junk(self.char1, self.wreck)
        self.assertIsNotNone(out["module"])
        self.assertFalse(out["junked"])

    def test_a_failed_move_still_disarms(self):
        self.room2.tags.add(*disposal.SCRAPYARD_TAG)
        with mock.patch("world.medical.procedures.strip_organ") as strip, \
             mock.patch.object(type(self.wreck), "move_to",
                               side_effect=RuntimeError("boom")):
            strip.return_value = object()
            out = disposal.strip_and_junk(self.char1, self.wreck)
        self.assertIsNotNone(out["module"])
        self.assertFalse(out["junked"])

    def test_a_failed_strip_does_not_strand_the_wreck(self):
        self.room2.tags.add(*disposal.SCRAPYARD_TAG)
        with mock.patch("world.medical.procedures.strip_organ",
                        side_effect=RuntimeError("boom")):
            out = disposal.strip_and_junk(self.char1, self.wreck)
        self.assertIsNone(out["module"])
        self.assertTrue(out["junked"])

    def test_a_vanished_wreck_is_a_no_op(self):
        out = disposal.strip_and_junk(self.char1, None)
        self.assertIsNone(out["module"])
        self.assertFalse(out["junked"])


class TestOnlyTheFinishedGetJunked(EvenniaCommandTest):
    def test_deliver_junks_the_dead_and_benches_the_living(self):
        import inspect
        from world.souls import jobs
        src = inspect.getsource(jobs.step_job)
        deliver = src[src.index('if do == "deliver":'):]
        deliver = deliver[:deliver.index('if do == "rob":')]
        self.assertIn("is_dead()", deliver)
        self.assertIn("strip_and_junk", deliver)

    def test_an_unreadable_body_is_never_junked(self):
        """Junking is irreversible-ish and the wrong call on a
        repairable unit. When in doubt, take it to the bench."""
        import inspect
        from world.souls import jobs
        src = inspect.getsource(jobs.step_job)
        deliver = src[src.index('if do == "deliver":'):]
        self.assertIn("finished = False", deliver)


class TestOnARealBody(EvenniaCommandTest):
    """Everything above mocks `strip_organ`. This one doesn't.

    A gate that agrees with its own mock proves nothing; the question
    is whether an augment organ actually becomes an object you can
    pick up, and whether the wreck genuinely stops having a gun.
    """

    def setUp(self):
        super().setUp()
        from world.director.population import factory_fit_armament
        self.wreck = self.char2
        self.wreck.db.species = "robot"
        self.wreck.db.role = "security"
        factory_fit_armament(self.wreck)

    def _organs(self):
        from world.medical.procedures import get_organ_snapshot
        return get_organ_snapshot(self.wreck).get("organs") or {}

    def test_the_unit_starts_armed(self):
        self.assertIn(disposal.ARMAMENT, self._organs())

    def test_stripping_produces_a_real_object(self):
        from world.medical.procedures import strip_organ
        item = strip_organ(self.wreck, disposal.ARMAMENT,
                           into=self.char1.location)
        self.assertIsNotNone(item, "no object came off the wreck")
        self.assertIs(item.location, self.char1.location)

    def test_and_the_wreck_is_disarmed(self):
        from world.medical.procedures import strip_organ
        strip_organ(self.wreck, disposal.ARMAMENT, into=self.char1.location)
        self.assertIn(disposal.ARMAMENT,
                      self.wreck.db.removed_organs or [])

    def test_it_cannot_be_stripped_twice(self):
        """Otherwise one wreck is an unlimited supply of shotguns."""
        from world.medical.procedures import strip_organ
        first = strip_organ(self.wreck, disposal.ARMAMENT,
                            into=self.char1.location)
        second = strip_organ(self.wreck, disposal.ARMAMENT,
                             into=self.char1.location)
        self.assertIsNotNone(first)
        self.assertIsNone(second, "the wreck yielded a second shotgun")

    def test_an_organ_it_never_had_yields_nothing(self):
        from world.medical.procedures import strip_organ
        self.assertIsNone(strip_organ(self.wreck, "flux_capacitor"))

    def test_the_arm_stays_on_the_chassis(self):
        """Verified on a real armed body: the module is an augment
        organ SEATED in the right arm, so taking it is removing a
        component, not taking the limb. A stripped chassis keeps both
        arms and loses the gun."""
        from world.medical.procedures import strip_organ
        strip_organ(self.wreck, disposal.ARMAMENT, into=self.char1.location)
        self.assertNotIn("right_arm",
                         self.wreck.db.severed_locations or [])
        still_there = [n for n, d in self._organs().items()
                       if d.get("container") == "right_arm"]
        self.assertIn("right_humerus", still_there)

    def test_the_whole_errand_end_to_end(self):
        """Disarm and dispose, unmocked, and check both halves."""
        self.room2.tags.add(*disposal.SCRAPYARD_TAG)
        out = disposal.strip_and_junk(self.char1, self.wreck)
        self.assertIsNotNone(out["module"], "the wreck kept its gun")
        self.assertTrue(out["junked"])
        self.assertIs(self.wreck.location, self.room2)
        self.assertIs(out["module"].location, self.char1.location,
                      "the shotgun went to the junkyard with the chassis")
