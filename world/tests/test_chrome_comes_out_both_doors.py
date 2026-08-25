"""Chrome comes out whichever door you use (#2286).

`can_be_harvested` is checked in exactly ONE place in the codebase --
the standalone `harvest` command. `operate` has no such guard, and its
resolver happily produces the item: forced to a successful roll, a
surgeon ends up holding a "robot integrated shotgun module".

But an AUGMENT has no species spec entry at all. It's fitted at
runtime by `factory_fit_armament` / the install path, not declared on
the anatomy — so the filter was rejecting chrome by ABSENCE rather
than by decision, and the same extraction worked through `operate`
and was refused through `harvest`.

This is the two-routes-disagree bug again, not a new capability:
nothing here lets anyone do something they couldn't already do
through the operate chart.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.anatomy import get_organ_spec
from world.medical.procedures import get_organ_snapshot


class TestBothDoorsAgree(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        from world.director.population import factory_fit_armament
        self.wreck = self.char2
        self.wreck.db.species = "robot"
        self.wreck.db.role = "security"
        factory_fit_armament(self.wreck)

    def _organs(self):
        return get_organ_snapshot(self.wreck).get("organs") or {}

    def _harvestable_via_command(self):
        """Mirror of the command's own filter."""
        out = []
        for name, data in self._organs().items():
            if not hasattr(data, "get"):
                continue
            spec = get_organ_spec(name, "robot") or {}
            if not spec.get("can_be_harvested") \
                    and not (data.get("data") or {}).get("module_type"):
                continue
            if data.get("current_hp", 0) <= 0:
                continue
            out.append(name)
        return out

    def test_the_module_has_no_spec_entry_at_all(self):
        """The premise: it was never marked unharvestable — it was
        never described. The filter said no by absence."""
        self.assertEqual(get_organ_spec("integrated_shotgun_module",
                                        "robot"), {})

    def test_operate_offers_it(self):
        from commands import CmdOperate as op
        names = [n for n, _c in op._list_organs(self.wreck)]
        self.assertIn("integrated_shotgun_module", names)

    def test_and_now_the_command_does_too(self):
        self.assertIn("integrated_shotgun_module",
                      self._harvestable_via_command())

    def test_ordinary_organs_are_unaffected(self):
        """Additive: this only ADDS augments. Nothing that was
        harvestable stops being, and nothing non-augment starts."""
        offered = self._harvestable_via_command()
        self.assertIn("heart", offered)
        self.assertNotIn("cervical_spine", offered)

    def test_a_destroyed_module_is_still_refused(self):
        """Opening the door doesn't drop the other checks."""
        self._organs()
        state = self.wreck.medical_state
        state.organs["integrated_shotgun_module"].current_hp = 0
        self.assertNotIn("integrated_shotgun_module",
                         self._harvestable_via_command())


class TestItReallyComesOut(EvenniaCommandTest):
    """Not a filter agreeing with itself — the object at the end."""

    def setUp(self):
        super().setUp()
        from world.director.population import factory_fit_armament
        self.wreck = self.char2
        self.wreck.db.species = "robot"
        factory_fit_armament(self.wreck)

    def test_a_successful_extraction_yields_the_module(self):
        from world.medical import procedures as pr
        actor = self.char1
        pr.open_incision(self.wreck, "right_arm", surgeon=actor)
        with mock.patch.object(pr, "roll_procedure",
                               return_value={"outcome": "success"}):
            pr._resolve_harvest(actor, self.wreck,
                                organ_name="integrated_shotgun_module",
                                location="right_arm")
        keys = [o.key for o in actor.contents]
        self.assertTrue(any("shotgun" in k for k in keys),
                        f"nothing came out; actor holds {keys}")

    def test_a_botched_extraction_still_ruins_it(self):
        """The failure branch marks it removed and yields nothing —
        the wreck is disarmed but the thief goes home empty. That's
        the risk that makes the race a race."""
        from world.medical import procedures as pr
        actor = self.char1
        pr.open_incision(self.wreck, "right_arm", surgeon=actor)
        with mock.patch.object(pr, "roll_procedure",
                               return_value={"outcome": "failure"}):
            pr._resolve_harvest(actor, self.wreck,
                                organ_name="integrated_shotgun_module",
                                location="right_arm")
        self.assertIn("integrated_shotgun_module",
                      self.wreck.db.removed_organs or [])
        self.assertFalse([o for o in actor.contents
                          if "shotgun" in o.key])
