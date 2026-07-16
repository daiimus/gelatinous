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
        self.assertIn("install", tools)
        self.assertIn("look", tools)            # BASE
        self.assertNotIn("prepare_drink", tools)  # not a bartender


class TestDoctorInstall(BaseEvenniaTest):
    """The install tool lays out the real incise -> install -> suture surgery."""

    def test_resolve_cyberware_sides(self):
        doc = create_object("typeclasses.clinic.Doctor", key="Doc3",
                            location=self.room1)
        self.assertEqual(doc._resolve_cyberware("right eye")[0], "CYBER_RIGHT_EYE")
        self.assertEqual(doc._resolve_cyberware("a new heart")[0],
                         "CYBERNETIC_HEART")
        self.assertEqual(doc._resolve_cyberware("cyber arm, left"),
                         ("CYBER_ARM", "left"))
        self.assertEqual(doc._resolve_cyberware("nanite cloud"), (None, None))

    def test_build_install_chart_lays_out_surgery(self):
        from world.medical import charts as chart_lib
        doc = create_object("typeclasses.clinic.Doctor", key="Doc4",
                            location=self.room1)
        patient = create_object("typeclasses.characters.Character", key="Pat4",
                                location=self.room1)
        chart = doc._build_install_chart(patient, "cyber arm left")
        self.assertIsNotNone(chart)
        self.assertEqual([s["verb"] for s in chart["steps"]],
                         ["incise", "install", "suture"])
        install = chart["steps"][1]
        self.assertIn("organ_item_key", install["args"])
        self.assertTrue(install["args"]["location"])      # an anchor was resolved
        self.assertIsNotNone(chart_lib.get_chart(patient))  # saved on the patient


class TestMedicalRequestParser(BaseEvenniaTest):
    """Deterministic medical-request detection (reliability lever, parity with the
    bartender's order parser): an EXPLICIT install/treat request runs for real; a
    question or bare symptom mention does NOT."""

    def _doctor(self):
        d = MagicMock()
        d._parse_medical_request = clinicmod.Doctor._parse_medical_request.__get__(
            d, clinicmod.Doctor)
        return d

    def test_install_requests(self):
        d = self._doctor()
        for s in ("put a chrome arm on me. i got the creds.",
                  "i want a cyber eye. left side.", "install a new kidney",
                  "replace my heart", "give me a new arm",
                  "right arm's dead weight. put a chrome one on."):
            self.assertEqual((d._parse_medical_request(s) or (None,))[0],
                             "install", f"install: {s!r}")

    def test_treat_requests(self):
        d = self._doctor()
        for s in ("gimme a painkiller", "need something for the pain",
                  "i need a stim", "hit me with the blood"):
            self.assertEqual((d._parse_medical_request(s) or (None,))[0],
                             "treat", f"treat: {s!r}")

    def test_not_requests(self):
        d = self._doctor()
        for s in ("my arm hurts", "my heart's racing", "keep an eye out for trouble",
                  "blood everywhere, help", "something's broke in here",
                  "just patch me up doc", "can you fix my eye?",
                  "i had a stim earlier", ""):
            self.assertIsNone(d._parse_medical_request(s), f"not a request: {s!r}")


class TestMedicalRequestRouting(BaseEvenniaTest):
    """_handle_directed_speech routes an explicit request to the real install/
    treat path — only when directed at this doctor, never on ambient chatter."""

    def _doctor(self, req, kind="directed"):
        d = MagicMock()
        d._parse_medical_request = lambda s: req
        d._classify_speech = lambda s, spk: kind
        d._patient = lambda spk: "patient"
        d._handle_directed_speech = clinicmod.Doctor._handle_directed_speech.__get__(
            d, clinicmod.Doctor)
        return d

    def test_directed_install_routes(self):
        d = self._doctor(("install", "put a chrome arm on me"))
        with patch.object(clinicmod, "delay") as dl:
            handled = d._handle_directed_speech("put a chrome arm on me",
                                                MagicMock(), {})
        self.assertTrue(handled)
        self.assertEqual(dl.call_args.args[1], d._install_cyber)

    def test_directed_treat_routes(self):
        d = self._doctor(("treat", "gimme a painkiller"))
        with patch.object(clinicmod, "delay") as dl:
            handled = d._handle_directed_speech("gimme a painkiller", MagicMock(), {})
        self.assertTrue(handled)
        self.assertEqual(dl.call_args.args[1], d._treat)

    def test_ambient_request_not_acted(self):
        d = self._doctor(("install", "put a chrome arm on me"), kind="ambient")
        with patch.object(clinicmod, "delay") as dl:
            handled = d._handle_directed_speech("put a chrome arm on me",
                                                MagicMock(), {})
        self.assertFalse(handled)
        dl.assert_not_called()

    def test_non_request_falls_through(self):
        d = self._doctor(None)
        handled = d._handle_directed_speech("something's broke in here",
                                            MagicMock(), {})
        self.assertFalse(handled)
