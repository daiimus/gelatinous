"""The surgery tell does not publish the patient's real name (#2943).

#2943 made surgery a channeled act, and `world/channeled.py` shows a
visible tell by writing `actor.override_place` -- "the act is PUBLIC
time". The tell it passes is:

    tell=f"working on {getattr(target, 'key', 'a patient')}"

`target.key` is the patient's TRUE NAME, and `override_place` is a
single string rendered verbatim to everyone in the room
(`rooms.py`: `override_place > temp_place > look_place`). There is no
per-observer identity pass on it, which is what `msg_room_identity`
exists to provide everywhere else.

Measured in play, with the observer's own view as the control:

    stranger sees the patient as: 'a gaunt androog'
    doc.override_place -> 'working on Ivo Kestrelson'
    room line: A gaunt androog is working on Ivo Kestrelson

The same line ANONYMISES THE SURGEON and NAMES THE PATIENT. Anyone in
the room learns the real name of a body they have never been introduced
to, straight through the disguise system.

The other two consumers of the primitive do not do this: graffiti names
nothing ("crouched at the wall, spray can hissing.") and breach names a
DOOR (`target.key` where the target is a fitting), which is not an
identity at all.

A single shared string cannot carry a per-observer identity, so the tell
carries no identity: "working on a patient" -- which is also exactly
what the existing `getattr(..., 'a patient')` fallback already said for
a target with no key.
"""
from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from world.medical.procedures import start_procedure


class TestTheTellNamesNobody(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.doc = create_object("typeclasses.characters.Character",
                                 key="Testdoc", location=self.room1)
        self.patient = create_object("typeclasses.characters.Character",
                                     key="Ivo Kestrelson", location=self.room1)
        self.stranger = create_object("typeclasses.characters.Character",
                                      key="Stranger", location=self.room1)
        for who in (self.doc, self.patient, self.stranger):
            # AttributeProperties, not `db.*` -- setting `db.height` leaves
            # `get_sdesc` falling straight back to `self.key`, and then the
            # stranger "sees" the real name for reasons that have nothing
            # to do with the bug.
            who.height = "tall"
            who.build = "lean"
            who.sdesc_keyword = "androog"
        kit = spawn("SURGICAL_KIT")[0]
        kit.location = self.doc

    def test_the_control_holds(self):
        """The stranger must not already know the patient by name, or a
        leaked name proves nothing about the tell."""
        seen = self.patient.get_display_name(self.stranger)
        self.assertNotIn("Ivo Kestrelson", seen)

    def test_the_tell_does_not_carry_the_patients_name(self):
        start_procedure(self.patient, verb="suture", actor=self.doc)
        self.assertNotIn("Ivo Kestrelson", self.doc.override_place or "")

    def test_the_room_does_not_show_it_either(self):
        """Through the player-visible path, not just the attribute."""
        start_procedure(self.patient, verb="suture", actor=self.doc)
        desc = str(self.room1.return_appearance(self.stranger))
        self.assertNotIn("Ivo Kestrelson", desc)

    def test_there_is_still_a_visible_tell(self):
        """The act stays PUBLIC time -- this must not become silence."""
        start_procedure(self.patient, verb="suture", actor=self.doc)
        self.assertIn("working on", self.doc.override_place or "")
