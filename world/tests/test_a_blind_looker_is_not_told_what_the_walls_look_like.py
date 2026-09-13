"""The @integrate layer is perception-gated like the rest of the room (#3373).

`Room.get_display_desc` is sight-gated and hands a blind looker the void
line. `return_appearance` then appended every @integrate object's content
to that same line with no perception check -- so a sightless looker read
"You can't see a thing here" followed by the graffiti on the walls.

Now each sensory contribution passes `can_perceive_sense`; the visual-only
fallbacks (`integration_desc`, `integration_fallback`, "<key> is here")
are withheld from a looker who cannot see; non-visual contributions (a
generator's hum) still reach them.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class BlindLookerNotToldWhatWallsLookLikeTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.room = self.room1
        self.room.db.desc = "A service corridor."
        self.char1.location = self.room
        # An @integrate object authored per sense...
        self.gen = create_object("typeclasses.items.Item", key="generator", location=self.room)
        self.gen.db.integrate = True
        self.gen.db.sensory_contributions = {
            "visual": "The walls are daubed with colorful graffiti.",
            "auditory": "A generator hums somewhere behind the panels.",
        }
        # ...and one with only the visual fallback line.
        self.crate = create_object("typeclasses.items.Item", key="crate", location=self.room)
        self.crate.db.integrate = True
        self.crate.db.integration_desc = "A battered crate squats in the corner."

    def blind(self, who):
        state = who.medical_state
        for organ in state.organs.values():
            if (organ.data or {}).get("capacity") == "sight":
                organ.current_hp = 0
        who.medical_state = state
        who.save_medical_state()
        who._medical_state = None

    def look(self):
        return self.room.return_appearance(self.char1) or ""

    # --- the defect ---------------------------------------------------------

    def test_blind_looker_gets_void_line_and_no_visual_integration(self):
        self.blind(self.char1)
        out = self.look()
        self.assertIn("can't see a thing", out)
        self.assertNotIn("graffiti", out, "blind looker was told what the walls look like: %r" % out)
        self.assertNotIn("battered crate", out, "blind looker got the visual fallback line")

    def test_blind_looker_still_hears(self):
        self.blind(self.char1)
        self.assertIn("generator hums", self.look())

    # --- control ---------------------------------------------------------------

    def test_sighted_looker_gets_everything(self):
        out = self.look()
        for s in ("service corridor", "graffiti", "generator hums", "battered crate"):
            self.assertIn(s, out, "sighted looker missing %r" % s)
