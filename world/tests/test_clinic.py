"""The clinic Doctor NPC: diagnose (read) + treat (draw a supply, run the REAL
apply/inject), and patient targeting (the one on the AutoDoc)."""

from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

import typeclasses.clinic as clinicmod
from world.llm.prompt import tool_names


class TestDoctorTools(BaseEvenniaTest):
    """diagnose/treat routing, mock-bound (the file's bartender pattern)."""

    def _doctor(self):
        d = MagicMock()
        d.location = "clinic"
        for name in ("_run_context_tool", "_handle_action_tool", "_treat",
                     "_name_aliases"):
            setattr(d, name,
                    getattr(clinicmod.Doctor, name).__get__(d, clinicmod.Doctor))
        d._patient = lambda patron: patron        # default: the speaker
        return d

    def _patient(self, name="a wiry man"):
        p = MagicMock()
        p.get_display_name = lambda looker=None, **kw: name
        return p

    def test_diagnose_reads_patient_status(self):
        d = self._doctor()
        with patch("world.medical.utils.get_medical_status_summary",
                   return_value="bleeding from the chest"):
            res = d._run_context_tool("diagnose", "", self._patient())
        self.assertIn("bleeding", res)

    def test_treat_bandage_applies_gauze(self):
        d = self._doctor()
        d._draw_supply = lambda proto: MagicMock(key="gauze bandages")
        d._handle_action_tool("treat", "bandage", self._patient("a wiry man"))
        d.execute_cmd.assert_called_once_with("apply gauze bandages on a wiry man")

    def test_treat_painkiller_injects_loose_match(self):
        d = self._doctor()
        d._draw_supply = lambda proto: MagicMock(key="painkiller")
        d._handle_action_tool("treat", "a painkiller for the pain",
                              self._patient("a wiry man"))
        d.execute_cmd.assert_called_once_with("inject painkiller a wiry man")

    def test_unknown_supply_no_op(self):
        d = self._doctor()
        d._draw_supply = lambda proto: MagicMock(key="x")
        d._handle_action_tool("treat", "nanite cloud", self._patient())
        d.execute_cmd.assert_not_called()

    def test_name_aliases(self):
        d = self._doctor()
        self.assertIn("doc", d._name_aliases())
        self.assertIn("surgeon", d._name_aliases())


class TestDoctorPatientTargeting(BaseEvenniaTest):
    """The doctor works on whoever is lying on the AutoDoc, not just the speaker."""

    def test_patient_is_the_autodoc_occupant(self):
        from typeclasses.furniture import AutoDoc
        doc = create_object("typeclasses.clinic.Doctor", key="Doc",
                            location=self.room1)
        pod = create_object(AutoDoc, key="autodoc", location=self.room1)
        patient = create_object("typeclasses.characters.Character", key="Pat",
                                location=self.room1)
        patient.db.furniture = pod                # lying on the table
        speaker = create_object("typeclasses.characters.Character", key="Spk",
                                location=self.room1)
        self.assertEqual(doc._patient(speaker), patient)

    def test_patient_falls_back_to_speaker(self):
        doc = create_object("typeclasses.clinic.Doctor", key="Doc2",
                            location=self.room1)
        speaker = create_object("typeclasses.characters.Character", key="Spk2",
                                location=self.room1)
        self.assertEqual(doc._patient(speaker), speaker)   # no AutoDoc, no patient


class TestDoctorArchetype(BaseEvenniaTest):
    """The doctor archetype grants the medical tools."""

    def test_doctor_tools(self):
        persona = {"persona_seed": {"name": "Sawbones", "archetype": "doctor"}}
        tools = tool_names(persona)
        self.assertIn("diagnose", tools)
        self.assertIn("treat", tools)
        self.assertIn("look", tools)            # BASE
        self.assertNotIn("prepare_drink", tools)  # not a bartender
