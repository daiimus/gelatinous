"""The NPC `look` tool examines what it asked for, not the patron (#3370).

`_run_context_tool("look", arg, patron)` ignored `arg` and returned the
patron's appearance every time -- whatever the model asked to examine, it
was handed the person it was already talking to. The tool's own contract
("examine someone or something you CAN'T already see ... do NOT look at
[the patron] again") forbade exactly that. An NPC could therefore never
perceive an object (the "show them a photo" scenario, NPC_MEMORY_AND_IDENTITY
§2b), and every look burned an agentic round for nothing.

Now the argument resolves like a real `look`: a person in the room by the
NPC's perceived identity, or an object in the room / the patron's hands /
the NPC's own. No argument still yields the patron; no match yields a
plain "nothing like that" rather than a silent fallback.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class NpcLooksAtWhatItAskedForTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc", key="Barkeep", location=self.room1)
        self.patron = self.char1
        self.patron.location = self.room1
        self.patron.db.desc = "A gaunt drifter in a rain-slick coat."
        self.notice = create_object("typeclasses.items.Item", key="wanted notice", location=self.room1)
        self.notice.db.desc = "A creased WANTED notice; the face is half torn away."
        self.photo = create_object("typeclasses.items.Item", key="photograph", location=self.patron)
        self.photo.db.desc = "A photograph of a heavy-jawed man, marked BILLY in pen."

    def look(self, arg):
        return self.npc._run_context_tool("look", arg, self.patron) or ""

    # --- the defect -------------------------------------------------------

    def test_look_at_a_room_object_returns_that_object(self):
        out = self.look("the wanted notice")
        self.assertIn("torn away", out, "did not describe the notice: %r" % out)
        self.assertNotIn("rain-slick", out, "described the patron instead of the notice")

    def test_look_at_something_the_patron_holds(self):
        out = self.look("photograph")
        self.assertIn("BILLY", out, "could not perceive the photo in the patron's hand: %r" % out)

    def test_look_at_nothing_matching_does_not_fall_back_to_the_patron(self):
        out = self.look("unicorn")
        self.assertNotIn("rain-slick", out)
        self.assertIn("nothing", out.lower())

    # --- controls -----------------------------------------------------------

    def test_look_with_no_argument_still_yields_the_patron(self):
        self.assertIn("rain-slick", self.look(""))

    def test_look_at_another_person_by_perceived_name(self):
        other = create_object("typeclasses.characters.Character", key="Ivo Kestrelson", location=self.room1)
        other.db.desc = "A wiry man with a soldering scar across one palm."
        name = other.get_display_name(self.npc)
        out = self.look(name)
        self.assertIn("soldering scar", out, "did not resolve the other person by perceived name %r: %r" % (name, out))
