"""Two renderers that bypassed the canonical accessor (#2586, #2588).

## #2586 — the paragraph break vanished in half the world

`format_appearance` decides where to put the blank line after the
description by string-matching each rendered line against the **raw**
`db.desc`. But the `{desc}` slot in `appearance_template` is filled by
`get_display_desc(looker)`, which since the five-senses work returns the
visual blob **plus** every authored non-visual layer from
`db.sense_descs`.

So `line.strip() == desc.strip()` is False in any room that has a sense
layer at all, and `result.append("")` never fires.

Measured live:

```
rooms:                    1,072
with sense_descs:           527      <- every one loses the break
sampled 400 of those: raw desc == rendered desc in   0
```

## #2588 — the one secret door was named in prose

`_visible_exits` is this file's single secret-door gate, and its
docstring states the guarantee: a `view:false()` exit *"stays out of the
exit prose entirely."* `get_custom_exit_display` honours it.
`get_adjacent_character_sightings` walked the raw `self.exits` and named
directions in player prose, so the view-locked exit was revealed by
anybody standing beyond it.

Two renderers onto the same exit set; only one carried the gate. Live:
**2,163 exits, exactly 1 view-locked** — the rooftop hatch the gate's
docstring names.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestTheBreakFollowsTheRenderedDesc(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.db.desc = "A narrow service corridor."
        self.char2.location = self.room1

    def rendered(self):
        return (self.room1.get_display_desc(self.char1) or "").strip()

    def test_a_plain_room_renders_its_raw_desc(self):
        self.assertEqual(self.rendered(), "A narrow service corridor.")

    def test_a_sense_layered_room_does_not(self):
        """The premise: the rendered text stops matching `db.desc`."""
        self.room1.db.sense_descs = {"auditory": "Pipes tick somewhere."}
        self.assertNotEqual(self.rendered(), self.room1.db.desc.strip())

    def test_the_rendered_desc_still_contains_the_visual(self):
        self.room1.db.sense_descs = {"auditory": "Pipes tick somewhere."}
        self.assertIn("A narrow service corridor.", self.rendered())

    def test_format_appearance_breaks_after_a_layered_desc(self):
        self.room1.db.sense_descs = {"auditory": "Pipes tick somewhere."}
        desc = self.rendered()
        appearance = f"{desc}\nYou see a crate here."
        out = self.room1.format_appearance(appearance, self.char1)
        self.assertIn("\n\n", out, "no paragraph break after the description")

    def test_and_still_breaks_for_a_plain_room(self):
        appearance = "A narrow service corridor.\nYou see a crate here."
        out = self.room1.format_appearance(appearance, self.char1)
        self.assertIn("\n\n", out)

    def test_no_break_when_nothing_follows(self):
        """The break exists to separate the desc from what comes after;
        with nothing after it, there is nothing to separate."""
        self.room1.db.sense_descs = {"auditory": "Pipes tick somewhere."}
        for obj in list(self.room1.contents):
            if obj not in (self.room1,):
                obj.location = self.room2
        desc = self.rendered()
        out = self.room1.format_appearance(desc, self.char1)
        self.assertNotIn("\n\n", out)


class TestTheSecretDoorStaysSecret(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        # A THIRD room reachable only through the hatch. Pointing it at
        # room2 proved nothing: the harness already links room1 -> room2
        # by an ordinary "out" exit, so the watcher was visible through
        # that instead and the assertion was about the wrong door.
        self.beyond = create_object("typeclasses.rooms.Room",
                                    key="a crawlspace")
        self.hatch = create_object("typeclasses.exits.Exit", key="hatch",
                                   location=self.room1,
                                   destination=self.beyond)
        self.watcher = create_object("typeclasses.characters.Character",
                                     key="Someone", location=self.beyond)

    def sightings(self):
        return self.room1.get_adjacent_character_sightings(self.char1) or ""

    def test_an_open_exit_reports_the_neighbour(self):
        """The control — the feature must still work."""
        self.assertTrue(self.sightings().strip(),
                        "an ordinary exit reported nothing")

    def test_a_view_locked_exit_reports_nothing(self):
        self.hatch.locks.add("view:false()")
        self.assertNotIn("hatch", self.sightings())

    def test_the_direction_is_not_named_either(self):
        self.hatch.locks.add("view:false()")
        self.assertNotIn("crawlspace", self.sightings())
        self.assertNotIn("hatch", self.sightings())

    def test_it_goes_through_the_one_gate(self):
        """Both renderers must ask the same question."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "rooms.py").read_text(errors="ignore")
        start = body.index("def get_adjacent_character_sightings")
        end = body.index("def ", start + 40)
        self.assertIn("self._visible_exits(looker)", body[start:end])
        self.assertNotIn("for exit_obj in self.exits:", body[start:end])


class TestTheGateStillGuaranteesIt(EvenniaTest):
    """`_visible_exits` is the single gate; pinned so a third renderer
    cannot quietly grow its own exit walk."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "typeclasses" / "rooms.py").read_text(errors="ignore")

    def test_the_gate_exists_and_checks_view(self):
        body = self._source()
        start = body.index("def _visible_exits")
        end = body.index("def ", start + 30)
        self.assertIn('access(looker, "view")', body[start:end])

    def test_the_prose_renderers_use_the_gate(self):
        """Only the two that NAME exits to the player.

        Three other walks over `self.exits` remain and are left alone
        deliberately: two resolve an exit for a direction the player has
        already aimed at, and one classifies destination rooms to group
        street types. None of them puts an exit name in front of a
        looker, which is what the gate exists to control.

        (Whether aiming should also respect a view lock is a separate
        question — you arguably should not be able to aim through a door
        you cannot see — and is not what #2588 reported.)
        """
        body = self._source()
        for fname in ("get_adjacent_character_sightings",
                      "get_custom_exit_display"):
            start = body.index(f"def {fname}")
            end = body.index("def ", start + 40)
            self.assertIn("self._visible_exits(looker)", body[start:end],
                          f"{fname} bypasses the gate")
