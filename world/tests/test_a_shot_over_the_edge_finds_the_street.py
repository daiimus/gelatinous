"""Aiming over an edge means aiming at the ground it drops to (#3589).

Owner ruling (2026-09-16): *"Aiming at an edge typically means aiming at
the ground area it drops to because of sniping. Rooftop to street for
example."* So a shot, a look or a throw that leaves a roof by an edge is
not aimed at the empty air cell the exit technically leads into -- it is
aimed at whatever a fall from it would end on.

Four functions carry that, and this module pins all four:

* :func:`world.spatial.coordinate_index` is the one cell-addressed
  lookup in the game: every on-grid room keyed by its ``(x, y, z)`` in a
  single query, built once per action rather than re-queried per step.
  Exits are skipped outright -- an exit that somehow carries an ``xyz``
  is not a place, and letting one into the index would let it shadow the
  room whose cell it borrowed.
* :func:`world.gravity.is_surface` is what counts as somewhere a body
  could be standing: a rooftop, or any outdoor room that is not air.
  Interiors never qualify.
* :func:`world.gravity.ground_below` answers *what is under this cell*
  WITHOUT moving anyone: the HIGHEST non-air room in the same column
  below it, with no distance limit -- the Drifts run below z=0 and a
  shot off a high roof must still reach them. Geometry is the primary
  source, because a shooter needs to know what is under the parapet
  whether or not a builder ever wired the column. Two answers are
  ``None`` and they are not the same thing: nothing solid below at all
  (the bare column, #3581), and an INTERIOR straight below -- an unbuilt
  roof in the way, which you cannot shoot through. With nothing seeded
  below at all the walk falls back to the ``down`` chain the fall itself
  uses, which is also the only route off the grid.
* :func:`world.gravity.room_through` is the one seam the callers share
  (``CmdAttack``'s directional attack, ``Room.return_appearance``'s
  aiming path, the unified target search and ``CmdThrow``). A gap goes
  to its far perch -- read by :func:`world.gravity.gap_destination`, in
  gravity rather than on ``CmdJump`` so that what you can leap to is
  what you can shoot at; an edge, or any exit into air, goes to the
  ground below; anything else is just its destination.

The fixtures are REAL rooms with real coordinates, never doubles: the
index is an ObjectDB attribute query, so a stubbed room is invisible to
it and the on-grid branch -- the primary one -- would never run.
"""

from __future__ import annotations

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.gravity import gap_destination, ground_below, is_surface, room_through
from world.spatial import coordinate_index, set_xyz


def _room(key, xyz=None, sky=False, desc=None, outside=True, type=None):
    """A room. ``outside`` defaults to True because the fixtures here are
    streets and roofs -- the places a shot from a parapet can reach.
    Pass ``outside=False`` for an interior, which occludes."""
    room = create_object("typeclasses.rooms.Room", key=key, location=None)
    if sky:
        room.db.is_sky_room = True      # the FLAG is air, not the typeclass
    if outside:
        room.db.outside = True
    if type:
        room.db.type = type
    if desc:
        room.db.desc = desc
    if xyz is not None:
        set_xyz(room, *xyz)
    return room


def _exit(key, src, dst, **attrs):
    ex = create_object("typeclasses.exits.Exit", key=key,
                       location=src, destination=dst)
    for name, value in attrs.items():
        ex.attributes.add(name, value)
    return ex


class TestTheGridIsIndexedByCell(EvenniaTest):
    """``coordinate_index`` is what ``ground_below`` reads; if it cannot
    answer for a cell, nothing below can be found."""

    def test_a_seeded_room_is_held_under_its_cell(self):
        street = _room("Test Street", (2, 3, 0))
        self.assertIs(coordinate_index().get((2, 3, 0)), street)

    def test_an_unbuilt_cell_is_absent(self):
        _room("Test Street", (2, 3, 0))
        self.assertNotIn((2, 3, 1), coordinate_index(),
                         "an empty cell must be absent, not answered by a neighbour")

    def test_an_exit_is_never_a_cell(self):
        """An exit is a door, not a place. One that somehow carries an
        ``xyz`` must not occupy -- or shadow -- a cell."""
        street = _room("Test Street", (2, 3, 0))
        roof = _room("Test Roof", (2, 3, 1), type="rooftop")
        stray = _exit("down", roof, street)
        set_xyz(stray, 2, 3, 5)
        index = coordinate_index()
        self.assertNotIn((2, 3, 5), index)
        self.assertNotIn(stray, index.values())


class TestWhatCountsAsASurface(EvenniaTest):
    """Moved out of ``CmdBuildTools`` so the builder's air fill and the
    shooter's line of sight cannot drift apart."""

    def test_a_rooftop_is_a_surface(self):
        self.assertTrue(is_surface(_room("Test Roof", outside=False,
                                         type="rooftop")))

    def test_an_outdoor_street_is_a_surface(self):
        self.assertTrue(is_surface(_room("Test Street")))

    def test_an_interior_is_not(self):
        self.assertFalse(is_surface(_room("Back Office", outside=False)))

    def test_air_is_not(self):
        self.assertFalse(is_surface(_room("In the Air", sky=True)))

    def test_nothing_is_not(self):
        self.assertFalse(is_surface(None))


class TestGroundBelowOnTheGrid(EvenniaTest):
    """roof z3 / air z2 / air z1 / street z0, all at (0, 0)."""

    def setUp(self):
        super().setUp()
        self.street = _room("Test Street", (0, 0, 0))
        self.air1 = _room("In the Air", (0, 0, 1), sky=True)
        self.air2 = _room("In the Air", (0, 0, 2), sky=True)
        self.roof = _room("Test Roof", (0, 0, 3), type="rooftop")

    def test_air_over_a_column_finds_the_street(self):
        self.assertIs(ground_below(self.air2), self.street)

    def test_the_cell_just_above_the_street_finds_it_too(self):
        self.assertIs(ground_below(self.air1), self.street)

    def test_the_highest_surface_wins_not_the_lowest(self):
        """A shot stops at the first thing it meets on the way down: the
        street, not the Drift gallery under the street."""
        gallery = _room("Drift Gallery", (0, 0, -1))
        self.assertIs(ground_below(self.air2), self.street)
        self.street.attributes.remove("xyz")   # unseed it: now the gallery is
        self.assertIs(ground_below(self.air2), gallery)

    def test_a_solid_cell_is_its_own_ground(self):
        """You are standing on it: the roof does not fall to the street."""
        self.assertIs(ground_below(self.roof), self.roof)
        self.assertIs(ground_below(self.street), self.street)

    def test_none_is_none(self):
        self.assertIsNone(ground_below(None))


class TestTheDescentHasNoLimit(EvenniaTest):
    """The colony runs below zero -- the Drifts are mines and sewers at
    negative z -- and a shot off a high roof reaches them."""

    def test_a_long_drop_into_the_drifts_still_lands(self):
        air = _room("In the Air", (3, 3, 3), sky=True)
        drift = _room("Drift Gallery", (3, 3, -2))
        self.assertIs(ground_below(air), drift)
        # ...and the answer really came from that room five cells down:
        # unseed it and the same call has nothing to find.
        drift.attributes.remove("xyz")
        self.assertIsNone(ground_below(air))


class TestAnUnbuiltCellIsNotAFloor(EvenniaTest):
    """The colony is hand-built and full of holes. A cell nobody ever
    made is a hole in the grid, and a shot passes through it -- it must
    not be mistaken for the bottom of the column."""

    def test_a_missing_cell_is_skipped(self):
        street = _room("Test Street", (7, 7, 0))
        air = _room("In the Air", (7, 7, 2), sky=True)
        self.assertNotIn((7, 7, 1), coordinate_index(),
                         "fixture: z1 must be unbuilt")
        self.assertIs(ground_below(air), street)


class TestAnInteriorIsAnUnbuiltRoofInTheWay(EvenniaTest):
    """The occlusion rule. An interior directly below an air cell means
    the building's roof was never built as a room -- but it is physically
    there, over the interior's head. There is nothing to shoot at."""

    def test_an_interior_below_occludes(self):
        _room("Test Street", (8, 8, 0))
        _room("Back Office", (8, 8, 1), outside=False)
        air = _room("In the Air", (8, 8, 2), sky=True)
        self.assertIsNone(ground_below(air),
                          "the shot passed through an unbuilt roof")

    def test_a_roofed_interior_does_not_hide_a_street_in_another_column(self):
        """Control: the occluder only blocks its OWN column."""
        _room("Back Office", (8, 8, 1), outside=False)
        street = _room("Test Street", (9, 8, 0))
        air = _room("In the Air", (9, 8, 2), sky=True)
        self.assertIs(ground_below(air), street)


class TestABareColumnHasNoGround(EvenniaTest):

    def test_air_all_the_way_down_is_none(self):
        top = _room("In the Air", (4, 4, 2), sky=True)
        _room("In the Air", (4, 4, 1), sky=True)
        _room("In the Air", (4, 4, 0), sky=True)
        self.assertIsNone(ground_below(top),
                          "a column of air with no floor has nothing to aim at")

    def test_an_empty_column_is_none(self):
        """Not even air below: the grid simply stops, and there is no
        ``down`` to walk either."""
        top = _room("In the Air", (5, 5, 3), sky=True)
        self.assertIsNone(ground_below(top))


class TestTheDownChainIsTheFallback(EvenniaTest):
    """No coordinates below -- or none at all -- so walk the ``down``
    chain the fall itself walks."""

    def test_an_on_grid_cell_with_nothing_seeded_below_walks_down(self):
        """Half the colony is unseeded. A wired column still answers."""
        below = _room("Loading Dock")             # off the grid entirely
        cell = _room("In the Air", (6, 6, 2), sky=True)
        _exit("down", cell, below)
        self.assertNotIn((6, 6, 1), coordinate_index())
        self.assertNotIn((6, 6, 0), coordinate_index())
        self.assertIs(ground_below(cell), below)

    def test_the_down_chain_finds_the_first_solid_room(self):
        basement = _room("Sub-Level Floor")
        lower = _room("In the Air", sky=True)
        upper = _room("In the Air", sky=True)
        _exit("down", upper, lower)
        _exit("down", lower, basement)
        self.assertIsNone(getattr(upper.db, "xyz", None), "fixture: off-grid")
        self.assertIs(ground_below(upper), basement)

    def test_the_alias_d_is_a_down_exit_too(self):
        floor = _room("Sub-Level Floor")
        cell = _room("In the Air", sky=True)
        create_object("typeclasses.exits.Exit", key="d",
                      location=cell, destination=floor)
        self.assertIs(ground_below(cell), floor)

    def test_no_down_at_all_is_none(self):
        self.assertIsNone(ground_below(_room("In the Air", sky=True)))

    def test_a_chain_that_ends_in_air_is_none(self):
        lower = _room("In the Air", sky=True)
        upper = _room("In the Air", sky=True)
        _exit("down", upper, lower)
        self.assertIsNone(ground_below(upper))


class TestGapDestination(EvenniaTest):
    """``gap_destination`` is the one reading of a gap's far perch, shared
    by the leap (``jump across``) and the shot. It used to live on
    ``CmdJump``; a second copy inside ``room_through`` would be exactly
    the kind of drift that makes a shot land somewhere a leap would not."""

    def setUp(self):
        super().setUp()
        self.roof = _room("Test Roof", (0, 0, 3), type="rooftop")
        self.perch = _room("Far Perch", (2, 0, 3), type="rooftop")
        self.air = _room("In the Air", (1, 0, 3), sky=True)

    def test_a_dbref_int_resolves(self):
        ex = _exit("east", self.roof, self.air,
                   is_gap=True, gap_destination=self.perch.id)
        self.assertIs(gap_destination(ex), self.perch)

    def test_a_dbref_string_resolves(self):
        """Builders type the number; some scripts stored it as text."""
        ex = _exit("east", self.roof, self.air,
                   is_gap=True, gap_destination=str(self.perch.id))
        self.assertIs(gap_destination(ex), self.perch)

    def test_an_object_resolves(self):
        ex = _exit("east", self.roof, self.air,
                   is_gap=True, gap_destination=self.perch)
        self.assertIs(gap_destination(ex), self.perch)

    def test_a_perch_that_is_air_is_no_perch(self):
        """You cannot land on it, so it is not where the leap ends --
        and a shot must not stop there either."""
        ex = _exit("east", self.roof, self.air,
                   is_gap=True, gap_destination=self.air.id)
        self.assertIsNone(gap_destination(ex))

    def test_a_dangling_dbref_is_none(self):
        ex = _exit("east", self.roof, self.air,
                   is_gap=True, gap_destination=99999999)
        self.assertIsNone(gap_destination(ex))

    def test_no_perch_falls_back_to_a_solid_destination(self):
        ex = _exit("east", self.roof, self.perch, is_gap=True)
        self.assertIs(gap_destination(ex), self.perch)

    def test_no_perch_and_an_air_destination_is_none(self):
        ex = _exit("east", self.roof, self.air, is_gap=True)
        self.assertIsNone(gap_destination(ex))

    def test_no_exit_is_none(self):
        self.assertIsNone(gap_destination(None))


class TestRoomThrough(EvenniaTest):
    """The seam the shot, the look, the search and the throw all ask."""

    def setUp(self):
        super().setUp()
        self.roof = _room("Test Roof", (0, 0, 3), type="rooftop")
        self.street = _room("Test Street", (0, 0, 0),
                            desc="Wet asphalt under a dead streetlight.")
        self.air = _room("In the Air", (0, 0, 2), sky=True)
        _room("In the Air", (0, 0, 1), sky=True)
        self.perch = _room("Far Perch", (1, 0, 3), type="rooftop")
        # a second, floorless column for the refusal cases
        self.void = _room("In the Air", (9, 9, 2), sky=True)
        _room("In the Air", (9, 9, 1), sky=True)

    # --- gaps: the far perch, not the ground -----------------------------

    def test_a_gap_reaches_its_far_perch_by_dbref(self):
        ex = _exit("northeast", self.roof, self.air,
                   is_gap=True, gap_destination=self.perch.id)
        self.assertIs(room_through(ex), self.perch)

    def test_a_gap_reaches_its_far_perch_by_object(self):
        ex = _exit("northeast", self.roof, self.air,
                   is_gap=True, gap_destination=self.perch)
        self.assertIs(room_through(ex), self.perch)

    def test_a_gap_whose_perch_is_air_falls_to_the_ground(self):
        """A mis-authored perch is not a place to stand; the shot drops."""
        ex = _exit("northeast", self.roof, self.air,
                   is_gap=True, gap_destination=self.void.id)
        self.assertIs(room_through(ex), self.street)

    def test_a_gap_with_no_perch_falls_to_the_ground(self):
        ex = _exit("northeast", self.roof, self.air, is_gap=True)
        self.assertIs(room_through(ex), self.street)

    # --- edges: the ground the edge drops to -----------------------------

    def test_an_edge_over_air_reaches_the_street(self):
        ex = _exit("east", self.roof, self.air, is_edge=True)
        self.assertIs(room_through(ex), self.street,
                      "the shot is aimed at the ground, not the empty cell")

    def test_an_edge_onto_solid_ground_is_that_ground(self):
        """A low parapet straight onto a walkway: no fall, no lookup."""
        walkway = _room("Service Walkway", (0, 1, 3), type="rooftop")
        ex = _exit("north", self.roof, walkway, is_edge=True)
        self.assertIs(room_through(ex), walkway)

    def test_an_unflagged_exit_into_air_still_drops(self):
        """Air is air. The flag on the exit is not what makes it a fall."""
        ex = _exit("east", self.roof, self.air)
        self.assertIs(room_through(ex), self.street)

    def test_an_edge_over_a_bare_column_has_nothing_to_aim_at(self):
        ex = _exit("west", self.roof, self.void, is_edge=True)
        self.assertIsNone(room_through(ex))

    # --- everything else -------------------------------------------------

    def test_a_plain_exit_is_its_destination(self):
        other = _room("Test Roof Annex", (1, 1, 3), type="rooftop")
        ex = _exit("southeast", self.roof, other)
        self.assertIs(room_through(ex), other)

    def test_no_exit_is_none(self):
        self.assertIsNone(room_through(None))
