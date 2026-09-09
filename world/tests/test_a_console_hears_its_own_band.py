"""A radio-answering fixture hears the band it is powered on (#2951).

#2951 stopped a walkie's grille fanning to every OBJECT in the room --
corpses, organs, blood pools, and the 592 things in Limbo -- by
filtering the audience through `world.emote._perceives`. That fix is
right and stays: it cut a 911MHz transmission from 627 renders to 35.

`_perceives` is `hasattr(get_sdesc) and hasattr(medical_state)`, which
is "is this a person". An `AnsweringFixture` is neither: it is a Radio
subclass. So the filter removed the one class of non-person that has to
receive radio -- the console that LISTENS on a band and answers.

A console is not a handset lying on a floor. It is the station. Its
`location` is the room, so `_grille_audience(holder)` returns the
PEOPLE in that room and the console is not among them; it was reachable
before only because the unfiltered `list(contents)` happened to include
it.

Measured in the live game: one `AnsweringFixture` exists -- the Boiler
Run Mechanics crane console (#7399), powered, band 27.0, Ossie
Trelane's crane -- and `IS THE FIXTURE IN ITS OWN AUDIENCE? -> False`.
End-to-end in a testbed, a person in the room heard the traffic and the
console's `at_msg_receive` never fired. The radio-controlled crane
could not be radio-controlled.

Fixed on the delivery side rather than by loosening `_perceives`: the
fixture is ALREADY iterated as one of `_all_powered_radios()`, so it
collects itself as its own listener. `_grille_audience` keeps meaning
"the people who hear this grille", which is what it is for, and the
performance win stays intact.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import radio as R


class TestAPoweredConsoleHearsTraffic(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.heard = []
        self.console = create_object("typeclasses.items.AnsweringFixture",
                                     key="test console", location=self.room2)
        self.console.db.radio_on = True
        self.console.db.frequency = "27.0"
        self.console.db.is_npc = True

        original = type(self.console).at_msg_receive
        heard = self.heard

        def spy(inner_self, text=None, from_obj=None, **kwargs):
            heard.append((str(text), kwargs.get("type")))
            return original(inner_self, text=text, from_obj=from_obj, **kwargs)

        self.addCleanup(setattr, type(self.console), "at_msg_receive",
                        original)
        type(self.console).at_msg_receive = spy

        self.speaker = self.char1
        self.speaker.location = self.room1
        self.handset = create_object("typeclasses.items.Radio",
                                     key="test handset",
                                     location=self.speaker)
        self.handset.db.radio_on = True
        self.handset.db.frequency = "27.0"

    def _transmit(self, text="crane, boom down"):
        R._deliver(self.speaker, text, "27.0", self.handset)

    def test_the_console_receives_the_traffic(self):
        self._transmit()
        self.assertTrue(self.heard,
                        "the console never heard its own band")

    def test_it_arrives_tagged_as_radio(self):
        """`_maybe_answer` returns early on anything that is not
        `type="radio"`, so arriving untagged is the same as not
        arriving."""
        self._transmit()
        self.assertEqual(self.heard[0][1], "radio")

    def test_a_console_on_another_band_hears_nothing(self):
        """The filter still has to filter."""
        self.console.db.frequency = "88.8"
        self._transmit()
        self.assertFalse(self.heard,
                         "a console answered a band it is not on")

    def test_an_unpowered_console_hears_nothing(self):
        self.console.db.radio_on = False
        self._transmit()
        self.assertFalse(self.heard, "an unpowered console answered")


class TestTheGrilleStillOnlyFansToPeople(EvenniaTest):
    """#2951's win must survive: a corpse or a crate in the room is
    still not an audience."""

    def test_a_plain_object_is_not_in_the_audience(self):
        crate = create_object("typeclasses.items.Item", key="a crate",
                              location=self.room1)
        self.assertNotIn(crate, R._grille_audience(self.char1))

    def test_a_person_is(self):
        self.char2.location = self.room1
        self.char1.location = self.room1
        self.assertIn(self.char2, R._grille_audience(self.char1))
