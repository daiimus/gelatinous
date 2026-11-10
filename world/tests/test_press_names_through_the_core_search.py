"""Every name `press` reads goes through the core search (#3783).

`CmdPress` used to match machine and can names by hand: a substring of
the key or an alias, the first object in room order, no ordinals. Now the
bare press, `press <button> on <machine>`, `call`, `press <color> on
<can>`, and a machine's check of its own name all call `Character.search`
scoped to their pool. So, for each of them: an alias that is not part of
the key still names the object, an ordinal picks the second of two
twins, and a fragment from the middle of a word names nothing and gets
that path's own refusal.

Driven through the real command with real objects.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdGraffiti import CmdPress
from world.insurance import NO_POLICY, void_policy

KIOSK = "typeclasses.terminals.RentalTerminal"
DISPENSER = "typeclasses.terminals.SleeveDispenser"
INSURANCE = "typeclasses.terminals.InsuranceTerminal"
CALL_BUTTON = "typeclasses.elevator.ElevatorCallButton"
PANEL = "typeclasses.elevator.ElevatorPanel"
PLAIN_ITEM = "typeclasses.items.Item"
SPRAY_CAN = "typeclasses.items.SprayCanItem"

FIRST_BOARD = "Vacancies here: 0 of 0"
SECOND_BOARD = "Vacancies here: 1 of 1"


class _Room(EvenniaCommandTest):

    def press(self, args: str, cmdstring: str = "press") -> str:
        return self.call(CmdPress(), args, caller=self.char1,
                         cmdstring=cmdstring) or ""

    def kiosk(self, cubes: int = 0):
        """A rental kiosk; its status board shows how many cubes it has,
        which tells two twins apart."""
        k = create_object(KIOSK, key="rental terminal", location=self.room1)
        k.db.cubes = []
        for _ in range(cubes):
            cube = create_object("typeclasses.rooms.Room",
                                 key="The Brackett Arms - Unit 9B")
            door = create_object("typeclasses.doors.DoorExit", key="door",
                                 location=self.room1, destination=cube)
            cube.db.cube_door = door
            k.db.cubes = list(k.db.cubes) + [cube]
        return k

    def twin_kiosks(self):
        return self.kiosk(cubes=0), self.kiosk(cubes=1)


class TheBarePress(_Room):
    """`press <arg>`: exact name, then buttons, then partial name."""

    def test_an_alias_outside_the_key_presses_the_machine(self):
        self.kiosk()
        self.assertIn("Vacancies here", self.press("kiosk"))

    def test_an_ordinal_picks_the_second_twin(self):
        self.twin_kiosks()
        self.assertIn(SECOND_BOARD, self.press("2nd kiosk"))
        self.assertIn(SECOND_BOARD, self.press("kiosk-2"))

    def test_without_an_ordinal_the_first_twin_answers(self):
        self.twin_kiosks()
        self.assertIn(FIRST_BOARD, self.press("kiosk"))

    def test_a_word_start_still_presses_the_machine(self):
        self.kiosk()
        self.assertIn("Vacancies here", self.press("rental"))

    def test_a_mid_word_fragment_gets_the_usage(self):
        self.kiosk()
        out = self.press("ntal")
        self.assertNotIn("Vacancies here", out)
        self.assertIn(CmdPress.USAGE, out)

    def test_here_is_still_the_kiosk_claim_button(self):
        # 'here' names no machine in the pool, so the label tier gets it.
        self.kiosk(cubes=1)
        self.press("here")
        self.assertIsNotNone(self.char1.db.residence)


class PressOnAMachine(_Room):
    """`press <button> on <machine>`."""

    def test_an_alias_outside_the_key_names_the_machine(self):
        self.kiosk()
        self.assertIn("Vacancies here", self.press("status on kiosk"))

    def test_an_ordinal_picks_the_second_twin(self):
        self.twin_kiosks()
        self.assertIn(SECOND_BOARD, self.press("status on 2nd kiosk"))

    def test_a_mid_word_fragment_names_no_machine(self):
        self.kiosk()
        out = self.press("status on ntal")
        self.assertNotIn("Vacancies here", out)
        self.assertIn("You don't have a 'ntal'.", out)


class ThePressRouting(_Room):
    """Where `press` sends its words: a named button, a panel's label,
    `call`, or the spray grammar. Trailing words after `call` are pinned
    in TheCallShorthand."""

    def button(self):
        return create_object(CALL_BUTTON, key="call button",
                             aliases=["button"], location=self.room1)

    def test_the_bare_name_presses_the_button_with_no_label(self):
        # The button returns False for any label, so "It's dead." means
        # it was pressed with arg None.
        self.button()
        self.assertIn("It's dead.", self.press("call button"))

    def test_a_label_falls_through_to_the_panel(self):
        panel = create_object(PANEL, key="floor panel", location=self.room1)
        with patch.object(panel, "at_press", return_value=True) as pressed:
            self.press("2")
        pressed.assert_called_once_with(self.char1, "2")

    def test_nothing_pressable_defers_to_usage(self):
        create_object(PLAIN_ITEM, key="2", location=self.room1)
        self.assertIn(CmdPress.USAGE, self.press("2"))

    def test_spray_syntax_still_routes_to_the_can(self):
        with patch.object(CmdPress, "_press_spray_can") as spray:
            self.press("blue on spray can")
        spray.assert_called_once_with("blue", "spray can")

    def test_call_is_press_call(self):
        self.button()
        self.assertIn("It's dead.", self.press("", cmdstring="call"))

    def test_call_without_a_button_says_so(self):
        self.assertIn("There's no call button here.",
                      self.press("", cmdstring="call"))


class TheCallShorthand(_Room):
    """`call` presses the thing whose name starts with the word call."""

    def test_an_alias_outside_the_key_is_called(self):
        create_object(CALL_BUTTON, key="lift bell", aliases=["call box"],
                      location=self.room1)
        self.assertIn("It's dead.", self.press("", cmdstring="call"))

    def test_trailing_words_still_call(self):
        create_object(CALL_BUTTON, key="call button", location=self.room1)
        self.assertIn("It's dead.", self.press("elevator", cmdstring="call"))

    def test_an_ordinal_picks_the_second_twin_through_press(self):
        # `call` takes no ordinal of its own; the twin is reached by press.
        create_object(CALL_BUTTON, key="call button", location=self.room1)
        create_object(CALL_BUTTON, key="call button", location=self.room1)
        self.assertIn("It's dead.", self.press("2nd call button"))
        self.assertIn(CmdPress.USAGE, self.press("3rd call button"))

    def test_call_inside_a_word_is_not_a_call_button(self):
        create_object(CALL_BUTTON, key="recall panel", location=self.room1)
        out = self.press("", cmdstring="call")
        self.assertIn("There's no call button here.", out)
        self.assertNotIn("It's dead.", out)


class PressAColorOnACan(_Room):
    """`press <color> on <can>` searches what the presser carries."""

    def can(self):
        # Key and aliases as the SPRAYPAINT_CAN prototype carries them.
        return create_object(
            SPRAY_CAN, key="can of spraypaint", location=self.char1,
            aliases=["can", "paint", "spray", "spraycan", "spraypaint"])

    def test_the_name_a_player_sees_names_the_can(self):
        """The can shows as `can of spraypaint`. Its key was `can of`,
        which the search cannot complete to the shown name, and only a
        hand-rolled walk over display names made `press` find it. The
        key is now the shown name, so every command finds it (#3783)."""
        can = self.can()
        self.assertEqual(can.get_display_name(self.char1), "can of spraypaint")
        self.press("blue on can of spraypaint")
        self.assertEqual(can.db.current_color, "blue")

    def test_an_alias_outside_the_key_names_the_can(self):
        can = self.can()
        self.press("blue on spraycan")
        self.assertEqual(can.db.current_color, "blue")

    def test_an_ordinal_picks_the_second_twin(self):
        first, second = self.can(), self.can()
        self.press("blue on 2nd spraycan")
        self.assertEqual(second.db.current_color, "blue")
        self.assertEqual(first.db.current_color, "red")

    def test_a_mid_word_fragment_names_no_can(self):
        # Held, so the hands walk that used to substring-match is in play.
        can = self.can()
        self.char1.hands = {"left": can, "right": None}
        out = self.press("blue on pray")
        self.assertIn("You don't have a 'pray'.", out)
        self.assertEqual(can.db.current_color, "red")

    def test_an_empty_can_name_gets_the_usage(self):
        self.can()
        self.assertIn(CmdPress.USAGE, self.press("blue on  "))


class AMachineKnowsItsOwnName(_Room):
    """`SleeveDispenser` and `InsuranceTerminal` take their own name as a
    button, checked by the core search over themselves, exact only."""

    def held(self) -> list:
        return [obj.key for obj in self.char1.contents]

    def test_the_dispenser_takes_an_alias_outside_its_key(self):
        create_object(DISPENSER, key="sleeve dispenser", location=self.room1)
        self.press("machine on machine")
        self.assertTrue(self.held())

    def test_the_dispenser_refuses_a_fragment_of_its_name(self):
        d = create_object(DISPENSER, key="sleeve dispenser",
                          location=self.room1)
        self.assertFalse(d.at_press(self.char1, "spenser"))
        out = self.press("spenser on machine")
        self.assertIn("You don't have a 'machine'.", out)
        self.assertEqual(self.held(), [])

    def test_the_dispenser_refuses_a_word_start_of_its_name(self):
        # Exact only: a loose match on the name must not win the label tier.
        d = create_object(DISPENSER, key="sleeve dispenser",
                          location=self.room1)
        self.assertFalse(d.at_press(self.char1, "sleeve"))

    def test_a_second_dispenser_answers_by_ordinal(self):
        create_object(DISPENSER, key="sleeve dispenser", location=self.room1)
        create_object(DISPENSER, key="sleeve dispenser", location=self.room1)
        self.press("2nd dispenser")
        self.assertTrue(self.held())

    def test_the_terminal_takes_an_alias_outside_its_key(self):
        create_object(INSURANCE, key="a Thawn-Harrison policy terminal",
                      location=self.room1)
        self.addCleanup(void_policy, self.char2.sleeve_uid)
        out = self.call(CmdPress(), "insurance on terminal",
                        caller=self.char2) or ""
        self.assertIn(NO_POLICY, out)

    def test_the_terminal_refuses_a_fragment_of_its_name(self):
        term = create_object(INSURANCE, key="a Thawn-Harrison policy terminal",
                             location=self.room1)
        self.addCleanup(void_policy, self.char2.sleeve_uid)
        self.assertFalse(term.at_press(self.char2, "surance"))
        out = self.call(CmdPress(), "surance on terminal",
                        caller=self.char2) or ""
        self.assertIn("You don't have a 'terminal'.", out)
        self.assertNotIn(NO_POLICY, out)

    def test_the_second_twin_terminal_is_reached_by_ordinal(self):
        create_object(INSURANCE, key="a Thawn-Harrison policy terminal",
                      location=self.room1)
        create_object(INSURANCE, key="a Thawn-Harrison policy terminal",
                      location=self.room1)
        self.addCleanup(void_policy, self.char2.sleeve_uid)
        out = self.call(CmdPress(), "status on 2nd terminal",
                        caller=self.char2) or ""
        self.assertIn(NO_POLICY, out)
