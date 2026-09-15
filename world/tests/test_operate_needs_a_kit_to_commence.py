"""Commencing a chart with no surgical kit refuses up front (#3504).

Spawn a mob, knock it out (consent satisfied), operate, chart incise +
harvest, commence -> it "failed instantly": start_procedure raises
SurgicalKitRequired, commence_chart swallows it into a step outcome the
surgeon never sees, and the menu had already printed the optimistic
"dispatched... in flight" line and closed. Owner ruling 2026-09-14:
commence checks for a kit up front, refuses with a clear message, and
leaves the chart intact. Charting without a kit stays legal.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands import CmdOperate as menu
from world.medical import charts as chart_lib


class OperateNeedsAKitToCommenceTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.patient = create_object("typeclasses.characters.Character", key="Patient", location=self.room1)
        self.patient.db.species = "human"
        self.char1.ndb._operate_target = self.patient
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))

    def _kit(self):
        kit = create_object("typeclasses.items.Item", key="a surgical kit", location=self.char1)
        kit.tags.add("surgical_kit", category="item_type")
        kit.db.medical_type = "surgical_treatment"
        return kit

    def _chart(self, *verbs_args):
        chart = chart_lib.new_chart(self.char1)
        for verb, args in verbs_args:
            chart_lib.add_step(chart, verb, args)
        chart_lib.save_chart(self.patient, chart)
        return chart

    def _is_top_menu(self, ret):
        self.assertIsInstance(ret, tuple, "commence handed EvMenu a bare string: %r" % (ret,))
        text, options = ret
        self.assertIn("OPTIONS", text)
        self.assertIs(options[0]["goto"], menu._process_top_choice)

    def test_no_kit_refuses_and_keeps_the_chart(self):
        self._chart(("incise", {"location": "head"}), ("harvest", {"organ_name": "brain"}))
        ret = menu._node_commence(self.char1, "")
        self._is_top_menu(ret)
        self.assertTrue(any("surgical kit" in s for s in self.said), self.said)
        # chart intact, nothing dispatched or failed
        steps = chart_lib.get_chart(self.patient)["steps"]
        self.assertEqual([s["status"] for s in steps], ["pending", "pending"])

    def test_message_names_the_right_instrument(self):
        self._chart(("incise", {"location": "head"}))
        menu._node_commence(self.char1, "")
        self.assertTrue(any("You need a surgical kit to operate" in s for s in self.said), self.said)

    def test_with_a_kit_it_dispatches(self):
        self._kit()
        self._chart(("incise", {"location": "head"}))
        menu._node_commence(self.char1, "")
        # incise is channeled -> the running step exists, no kit refusal
        self.assertFalse(any("You need" in s for s in self.said), self.said)
        statuses = [s["status"] for s in chart_lib.get_chart(self.patient)["steps"]]
        self.assertIn(statuses[0], ("running", "done"))

    def test_a_treatment_only_chart_needs_no_kit(self):
        # apply / inject are skipped by the runner and need no instruments.
        self._chart(("apply", {"item_key": "gauze", "location": "head"}))
        ret = menu._node_commence(self.char1, "")
        self.assertFalse(any("surgical kit" in s for s in self.said),
                         "a treatment-only chart was refused for want of a kit: %r" % self.said)
        self._is_top_menu(ret) if isinstance(ret, tuple) else None
