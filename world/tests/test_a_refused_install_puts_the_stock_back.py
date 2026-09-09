"""A refused install does not pocket the cyberware (#2474 / #2801).

`build_install_chart` draws a cyber organ, and a surgical kit if the
surgeon has none, BEFORE it knows whether the surgery can be laid out.
Every path that then refuses has to put back what it drew, and the
no-anchor branch says so in as many words:

    # Genuinely nothing to mount it to ... Put back everything THIS
    # request drew rather than pocketing it in silence.
    _discard(cyber)
    _discard(drawn_kit)
    return None

The guard immediately below it does not:

    existing = chart_lib.get_chart(patient)
    if existing and _chart_is_live(existing):
        return None                     # <- cyber and kit still drawn

So asking for a second install while a surgery is already running --
the exact case #2801's no-clobber guard exists to refuse -- mints a
cyber organ into the surgeon's pockets and abandons it there. That is
the accumulation #2474 was filed about (nine surgical kits on Jericho
Black III, eight with consecutive object ids), reintroduced through a
different door.

The `_discard` helper and the comment naming the rule were both already
here. The guard was simply added above them without either being read.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import clinic


class TestARefusedInstallDrawsNothingPermanent(EvenniaTest):

    def setUp(self):
        super().setUp()
        # `draw_supply` is a post perk (#2474), so the surgeon must
        # actually stand one or every draw returns None and the whole
        # test passes vacuously.
        self.doc = create_object("typeclasses.llm_npc.LLMNpc",
                                 key="Testdoc", location=self.room1)
        self.doc.db.soul_post = self.room1
        self.patient = create_object("typeclasses.characters.Character",
                                     key="Testpatient", location=self.room1)

    def _carried(self):
        return [o.key for o in self.doc.contents]

    def test_the_first_request_draws_and_charts(self):
        """The control. Without this, 'nothing was pocketed' would also
        be true of a function that never draws anything at all."""
        chart = clinic.build_install_chart(self.doc, self.patient,
                                           "cyber arm left")
        self.assertIsNotNone(chart, "the fixture never reached a draw")
        self.assertTrue(self._carried(), "nothing was drawn at all")

    def test_a_refused_second_request_pockets_nothing(self):
        clinic.build_install_chart(self.doc, self.patient, "cyber arm left")
        after_first = sorted(self._carried())

        second = clinic.build_install_chart(self.doc, self.patient,
                                            "cyber arm left")
        self.assertIsNone(second, "#2801's no-clobber guard did not refuse")
        self.assertEqual(
            sorted(self._carried()), after_first,
            "the refused request left stock in the surgeon's pockets")
