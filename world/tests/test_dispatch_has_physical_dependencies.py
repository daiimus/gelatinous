"""Dispatch has dependencies you can attack (#2442).

`RADIO_COMMS_SPEC` §2.1 promises the emergency band is physical: a
downed operator or a wrecked mast degrades it. Two of the three ways
that was supposed to be true did not work.

**An unconscious dispatcher kept dispatching.** Nothing clears
`db.furniture` except changing rooms or `stand`, and being downed does
neither — so a choked-out operator stayed "seated". Traffic reached her
through `seated_base_station`, which checked the chair, the room and
the console but never whether the body in it was awake, and
`consider_radio_report` only ever tested its operator for `is None`. So
you could choke the dispatcher, leave her in the chair, and the band
went on classifying calls and rolling the security force. The single
tell was that her spoken reply was silent.

The check goes in `seated_base_station` because it is the one door —
dispatch hearing, `xmit` and `to <console>` all resolve the desk
through it, so no consumer can be added later that forgets. Every other
console verb already gated on consciousness; the dispatch decision
itself had none.

**A wrecked mast did not shorten reach.** `get_base_station()` returned
None when the antenna was down, and `order_reaches` treats a None
console as a PRE-RADIO WORLD and fails open. So sabotaging the mast
changed nothing: units on the far side of the colony still rolled, and
`_effective_tx_range`'s handheld collapse was unreachable in
production.

Two docstrings disagreed about what a downed mast means — "dispatch has
no voice" in one, "wrecked mast = handheld range" in the other — and
the halves contradicted each other ON AIR: `units_available(board)` is
passed the SEATED board, applies the collapse, and had the dispatcher
announcing "0 unit(s) available" while units rolled. A mast is a RANGE
fact; the console still exists.

**The third finding did not survive checking.** "No units available"
being welded to one flagged NPC was fixed by #2710 —
`get_dispatch_operator` asks `keeper_on_duty` who holds the chair, and
falls back to the flag only so a post with no slots still works.
"""
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.radio import seated_base_station


class _DeskCase(EvenniaTest):
    def desk(self):
        chair = create_object("typeclasses.objects.Object", key="a chair",
                              location=self.room1)
        console = create_object("typeclasses.objects.Object",
                                key="a dispatch console", location=self.room1)
        console.db.is_radio = True
        console.db.radio_on = True
        console.db.is_base_station = True
        console.db.frequency = "911"
        self.char1.location = self.room1
        self.char1.db.furniture = chair
        return console


class TestAnUnconsciousOperatorIsNotWorkingTheDesk(_DeskCase):
    def test_an_awake_operator_holds_the_board(self):
        console = self.desk()
        self.assertIs(seated_base_station(self.char1), console)

    def test_an_unconscious_one_does_not(self):
        self.desk()
        with patch.object(type(self.char1), "is_unconscious",
                          return_value=True):
            self.assertIsNone(seated_base_station(self.char1))

    def test_nor_a_dead_one(self):
        self.desk()
        with patch.object(type(self.char1), "is_dead", return_value=True):
            self.assertIsNone(seated_base_station(self.char1))

    def test_the_chair_is_not_released_by_being_downed(self):
        """Which is exactly why the check has to live here: the body is
        still 'seated' by every other measure."""
        self.desk()
        with patch.object(type(self.char1), "is_unconscious",
                          return_value=True):
            seated_base_station(self.char1)
        self.assertIsNotNone(self.char1.db.furniture)

    def test_a_stand_in_that_answers_every_predicate_still_works(self):
        """A MagicMock returns a truthy Mock for `is_dead()`, so a plain
        truthiness test would read every fixture as a corpse. Strict
        `is True` is the idiom this codebase uses on that hazard."""
        console = self.desk()
        stand_in = MagicMock()
        stand_in.db.furniture = self.char1.db.furniture
        stand_in.location = self.room1
        self.assertIs(seated_base_station(stand_in), console)


class TestAWreckedMastIsARangeFact(EvenniaTest):
    def test_the_console_still_exists_without_its_mast(self):
        from world.director.population import get_base_station
        import inspect
        source = inspect.getsource(get_base_station)
        self.assertIn("require_mast", source)

    def test_reach_asks_without_the_mast_requirement(self):
        """`order_reaches` treats a None console as a pre-radio world
        and fails OPEN, so a mast-filtered None made the handheld
        collapse unreachable."""
        import inspect
        from world import radio
        source = inspect.getsource(radio.order_reaches)
        self.assertIn("require_mast=False", source)

    def test_the_responder_search_does_too(self):
        # FULL SUBMODULE PATH. `from world.director import dispatch`
        # binds the FUNCTION `dispatch`, not the module — the package
        # re-exports it and shadows its own submodule, the same trap
        # `world/weather/__init__.py` sets with `weather_system`.
        # `importlib.import_module`, because BOTH `from world.director
        # import dispatch` AND `import world.director.dispatch as x`
        # hand back the FUNCTION: the package re-exports it and shadows
        # its own submodule, the same trap `world/weather/__init__.py`
        # sets with `weather_system`. Only sys.modules has the module.
        import importlib
        import inspect
        dispatch_mod = importlib.import_module("world.director.dispatch")
        self.assertIn("require_mast=False",
                      inspect.getsource(dispatch_mod))

    def test_the_default_still_means_has_a_voice(self):
        """Callers asking 'does dispatch have a voice at all' keep the
        strict answer."""
        import inspect
        from world.director.population import get_base_station
        sig = inspect.signature(get_base_station)
        self.assertIs(sig.parameters["require_mast"].default, True)


class TestTheOperatorLookupStaysFixed(EvenniaTest):
    """#2710 — a pin, not evidence."""

    def test_it_asks_who_holds_the_chair(self):
        import inspect
        from world.director.population import get_dispatch_operator
        source = inspect.getsource(get_dispatch_operator)
        self.assertIn("keeper_on_duty", source)

    def test_and_still_refuses_a_downed_operator(self):
        import inspect
        from world.director.population import get_dispatch_operator
        source = inspect.getsource(get_dispatch_operator)
        self.assertIn("is_unconscious", source)
