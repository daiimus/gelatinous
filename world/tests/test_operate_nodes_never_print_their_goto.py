"""An operate node with nothing to show re-renders the top menu (#3500).

Run a chart to completion, pick Commence again: "Chart complete -- no
pending steps." then the literal word ``node_top``, and the menu closes.
EvMenu treats a NODE function's string return as its display text; the
goto-by-name form only works from option callbacks. Nine sites in six
node functions did it (commence x3, install donor, install location x2,
harvest, incise, amputate) -- every "nothing to list / nothing to run"
branch. Each now returns ``_node_top(...)``: the message shows, the top
menu re-renders, the surgeon carries on.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands import CmdOperate as menu
from world.medical import charts as chart_lib


class OperateNodesNeverPrintTheirGotoTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.patient = create_object("typeclasses.characters.Character", key="Patient", location=self.room1)
        self.patient.db.species = "human"
        self.char1.ndb._operate_target = self.patient
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))

    def _is_top_menu(self, ret):
        self.assertIsInstance(ret, tuple, "the node handed EvMenu a bare string: %r" % (ret,))
        text, options = ret
        self.assertNotEqual((text or "").strip(), "node_top")
        self.assertIn("OPTIONS", text)
        self.assertIs(options[0]["goto"], menu._process_top_choice)

    def test_commence_on_a_completed_chart_returns_to_the_top(self):
        chart = chart_lib.new_chart(self.char1)
        step = chart_lib.add_step(chart, "incise", {"location": "abdomen"})
        step["status"] = chart_lib.COMPLETED
        chart_lib.save_chart(self.patient, chart)
        ret = menu._node_commence(self.char1, "")
        self._is_top_menu(ret)
        self.assertTrue(any("Chart complete" in s for s in self.said), self.said)

    def test_commence_with_no_chart_returns_to_the_top(self):
        self._is_top_menu(menu._node_commence(self.char1, ""))
        self.assertTrue(any("No chart" in s for s in self.said), self.said)

    def test_harvest_with_nothing_to_offer_returns_to_the_top(self):
        with mock.patch.object(menu, "_list_organs", return_value=[]):
            self._is_top_menu(menu._node_harvest_organ(self.char1, ""))

    def test_install_with_no_donor_returns_to_the_top(self):
        with mock.patch.object(menu, "_list_donor_organs", return_value=[]):
            self._is_top_menu(menu._node_install_organ(self.char1, ""))

    def test_incise_with_nothing_to_list_returns_to_the_top(self):
        with mock.patch.object(menu, "_list_containers", return_value=[]):
            self._is_top_menu(menu._node_incise_location(self.char1, ""))

    def test_amputate_with_nothing_to_list_returns_to_the_top(self):
        with mock.patch.object(menu, "_list_severable_containers", return_value=[]):
            self._is_top_menu(menu._node_amputate_location(self.char1, ""))

    # --- control: option callbacks may still answer with a goto NAME ----------

    def test_an_option_callback_still_routes_by_name(self):
        self.assertEqual(menu._process_top_choice(self.char1, "1"), "node_add_verb")
        self.assertEqual(menu._process_verb_choice(self.char1, "x"), "node_top")

    def test_a_node_with_something_to_show_is_unchanged(self):
        text, options = menu._node_harvest_organ(self.char1, "")
        self.assertIn("Pick an organ to harvest", text)
        self.assertIs(options[0]["goto"], menu._process_harvest_organ)
