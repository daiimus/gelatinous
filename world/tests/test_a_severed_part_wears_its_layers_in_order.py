"""The outermost garment shows, and a styled garment covers what it
currently covers -- on a severed part as on the body (#3578 review).

Three ways the first cut got it wrong, each pinned through the player's
path (``return_appearance`` on a real :class:`typeclasses.items.Appendage`):

* a part's ledger lists garments **outermost first** at each location,
  the way the living ``worn_items`` stack does; a flat "later wins" read
  showed the innermost one and lost the outer one entirely;
* the ledger, not the garment's base ``coverage``, says where it is
  worn -- a knit cap rolled up off the ears must leave the ears (and
  their wounds) in view;
* a styled garment reads through ``get_current_worn_desc``: the active
  style's prose, and the terminating period the prototypes are authored
  without.

The corpse keeps no ledger, only a flat list, so its builder orders by
layer and reads current coverage; that is pinned here too.
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

HEAD = {
    "hair": "{Their} hair is cropped close.",
    "head": "{They} {hold} {their} head very still.",
    "left_ear": "{Their} {ears} {sit} close to the skull.",
    "right_ear": "{Their} {ears} {sit} close to the skull.",
    "face": "{Their} face is cool alabaster.",
}


def garment(key, *, coverage, layer, worn_desc, location):
    item = create_object("typeclasses.items.Item", key=key, location=location)
    item.db.coverage = list(coverage)
    item.layer = layer
    item.db.worn_desc = worn_desc
    return item


class _Head(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.head = create_object("typeclasses.items.Appendage",
                                  key="human head", location=self.room1)
        self.head.db.desc = "A severed human head."
        self.head.db.location_name = "head"
        self.head.db.original_gender = "male"
        self.head.db.original_character_name = "Iver"
        self.head.db.source_species = "human"
        self.head.db.longdesc_data = dict(HEAD)

    def look(self):
        return self.head.return_appearance(self.char1)


class TestTheOuterGarmentShows(_Head):
    """Helmet (layer 5) over balaclava (layer 2), ledger outermost-first."""

    def setUp(self):
        super().setUp()
        self.helmet = garment("mining helmet", coverage=["head"], layer=5,
                              worn_desc="A yellow helmet sits square on {their} head",
                              location=self.head)
        self.balaclava = garment("balaclava", coverage=["hair", "head"], layer=2,
                                 worn_desc="A black balaclava hugs {their} skull",
                                 location=self.head)
        self.head.db.worn_items = {"head": [self.helmet, self.balaclava],
                                   "hair": [self.balaclava]}

    def test_helmet_at_the_head_balaclava_at_the_hair(self):
        out = self.look()
        self.assertEqual(out.count("A yellow helmet sits square on his head."), 1, out)
        self.assertEqual(out.count("A black balaclava hugs his skull."), 1, out)
        self.assertNotIn("His hair is cropped close", out)
        self.assertNotIn("holds his head very still", out)
        self.assertIn("His face is cool alabaster.", out)

    def test_the_order_in_the_ledger_decides_not_the_order_of_wearing(self):
        # The same two garments, balaclava listed first at the head:
        # the ledger says the balaclava is outermost there, so it shows.
        self.head.db.worn_items = {"head": [self.balaclava, self.helmet],
                                   "hair": [self.balaclava]}
        out = self.look()
        self.assertEqual(out.count("A black balaclava hugs his skull."), 1, out)
        self.assertNotIn("A yellow helmet", out)
        # ...and the helmet, hidden under it, is not listed as contents either
        self.assertNotIn("You see", out)


class TestARolledCapLeavesTheEars(_Head):
    def setUp(self):
        super().setUp()
        self.cap = garment("knit cap", coverage=["head", "left_ear", "right_ear"],
                           layer=3, worn_desc="A knit cap is pulled down over {their} ears",
                           location=self.head)
        self.cap.style_configs = {"adjustable": {
            "rolled": {"desc_mod": "A knit cap sits rolled high on {their} head, the ears bare",
                       "coverage_mod": ["-left_ear", "-right_ear"]},
            "down": {"desc_mod": "", "coverage_mod": []},
        }}
        self.cap.style_properties = {"adjustable": "rolled"}
        # the ledger records where it is actually worn: rolled = head only
        self.head.db.worn_items = {"head": [self.cap]}
        self.head.db.wounds_at_death = [{"location": "left_ear",
                                         "injury_type": "cut", "severity": "Minor"}]

    def test_the_ears_and_their_wound_stay_in_view(self):
        from unittest.mock import patch
        with patch("world.medical.wounds.get_wound_description",
                   return_value="A notch is cut from the ear."):
            out = self.look()
        self.assertIn("A knit cap sits rolled high on his head, the ears bare.", out)
        self.assertNotIn("pulled down over", out)
        self.assertIn("His ears sit close to the skull.", out)
        self.assertIn("A notch is cut from the ear.", out)

    def test_pulled_down_it_covers_them(self):
        self.cap.style_properties = {"adjustable": "down"}
        self.head.db.worn_items = {"head": [self.cap], "left_ear": [self.cap],
                                   "right_ear": [self.cap]}
        out = self.look()
        self.assertEqual(out.count("A knit cap is pulled down over his ears."), 1, out)
        self.assertNotIn("His ears sit", out)


class TestTheCorpseOrdersByLayer(EvenniaTest):
    """Outer created FIRST, so the old 'later wins' read would have shown
    the inner one; and pinned through return_appearance, since the corpse
    prints what its map says it covers."""

    def test_outermost_wins_and_style_narrows_coverage(self):
        corpse = create_object("typeclasses.corpse.Corpse", key="corpse",
                               location=self.room1)
        corpse.db.original_gender = "male"
        corpse.db.original_character_name = "Iver"
        corpse.db.longdesc_data = {"hair": "{Their} hair is cropped close.",
                                   "head": "{They} {hold} {their} head still.",
                                   "left_ear": "{Their} {ears} {sit} close to the skull.",
                                   "right_ear": "{Their} {ears} {sit} close to the skull."}
        outer = garment("helmet", coverage=["head"], layer=5,
                        worn_desc="A yellow helmet sits square on {their} head",
                        location=corpse)
        inner = garment("balaclava", coverage=["hair", "head"], layer=2,
                        worn_desc="A black balaclava hugs {their} skull",
                        location=corpse)
        cap = garment("knit cap", coverage=["left_ear", "right_ear"], layer=3,
                      worn_desc="A knit cap is pulled down over {their} ears",
                      location=corpse)
        cap.style_configs = {"adjustable": {"rolled": {
            "desc_mod": "A knit cap sits rolled high, the ears bare",
            "coverage_mod": ["-left_ear", "-right_ear"]}}}
        cap.style_properties = {"adjustable": "rolled"}
        cmap = corpse._build_corpse_clothing_coverage_map()
        self.assertIs(cmap.get("head"), outer)
        self.assertIs(cmap.get("hair"), inner)
        self.assertNotIn("left_ear", cmap)
        out = corpse.return_appearance(self.char1)
        self.assertIn("A yellow helmet sits square on his head.", out)
        self.assertIn("A black balaclava hugs his skull.", out)
        self.assertNotIn("holds his head still", out)
        # rolled: the ears show, and the ROLLED sentence is the one printed
        self.assertIn("His ears sit close to the skull.", out)
        self.assertNotIn("pulled down over", out)


class TestTheWritersKeepOutermostFirst(EvenniaTest):
    """Both ledger writers leave the order the renderer reads."""

    def _head(self):
        head = create_object("typeclasses.items.Appendage", key="human head",
                             location=self.room1)
        head.db.location_name = "head"
        head.db.chain = ("head", "hair")
        head.db.worn_items = {}
        return head

    def test_dress_puts_the_higher_layer_in_front_whatever_the_order(self):
        from commands.CmdClothing import CmdDress
        head = self._head()
        balaclava = garment("balaclava", coverage=["hair", "head"], layer=2,
                            worn_desc="inner", location=self.char1)
        helmet = garment("helmet", coverage=["head"], layer=5,
                         worn_desc="outer", location=self.char1)
        cmd = CmdDress(); cmd.caller = self.char1
        ok, _ = cmd._dress_appendage(head, balaclava); self.assertTrue(ok)
        ok, _ = cmd._dress_appendage(head, helmet); self.assertTrue(ok)
        self.assertEqual(list(head.db.worn_items["head"]), [helmet, balaclava])
        self.assertEqual(list(head.db.worn_items["hair"]), [balaclava])

    def test_detach_copies_the_body_s_per_location_order(self):
        from typeclasses.items import detach_items_to_appendage
        glove = garment("glove", coverage=["left_hand"], layer=1,
                        worn_desc="g", location=self.char1)
        sleeve = garment("sleeve", coverage=["left_arm", "left_hand"], layer=2,
                         worn_desc="s", location=self.char1)
        bracer = garment("bracer", coverage=["left_arm"], layer=3,
                         worn_desc="b", location=self.char1)
        # the living stack after wearing glove, sleeve, bracer in that order
        self.char1.worn_items = {"left_hand": [sleeve, glove],
                                 "left_arm": [bracer, sleeve]}
        arm = create_object("typeclasses.items.Appendage", key="severed arm",
                            location=self.room1)
        arm.db.worn_items = {}
        moved = detach_items_to_appendage(self.char1, arm, ["left_arm", "left_hand"])
        self.assertEqual(set(moved), {glove, sleeve, bracer})
        self.assertEqual(list(arm.db.worn_items["left_arm"]), [bracer, sleeve])
        self.assertEqual(list(arm.db.worn_items["left_hand"]), [sleeve, glove])
