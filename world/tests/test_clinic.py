"""The clinic Doctor NPC: diagnose (read) + treat (draw a supply, run the REAL
apply/inject), and patient targeting (the one on the AutoDoc)."""

from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

import typeclasses.clinic as clinicmod
import typeclasses.llm_npc as llmnpc
import world.clinic as worldclinic
from world.llm.prompt import tool_names


class TestDoctorTools(BaseEvenniaTest):
    """diagnose/treat routing, mock-bound (the file's bartender pattern)."""

    def _doctor(self):
        d = MagicMock()
        d.location = "clinic"
        for name in ("_run_context_tool", "_handle_action_tool"):
            setattr(d, name,
                    getattr(llmnpc.LLMNpcMixin, name).__get__(d, llmnpc.LLMNpc))
        d._treat = lambda patient, what: worldclinic.treat(d, patient, what)
        d._patient = lambda patron: patron        # default: the speaker
        # The tools belong to the JOB now (#2352): the archetype grants
        # them and the job runs them, so a bare mock with no post has no
        # tools at all. Stand this one at the clinic post.
        from world import service
        service._ensure_loaded()
        patcher = patch("world.service.job_of",
                        return_value=service.SERVICE["doctor"])
        patcher.start()
        self.addCleanup(patcher.stop)
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

    def test_name_aliases_come_from_the_job(self):
        """"doc" and "surgeon" belong to whoever is standing the clinic
        post, not to a typeclass (#2352)."""
        from world.clinic import CLINIC_ROLES
        from world import service
        service._ensure_loaded()
        job = service.SERVICE[CLINIC_ROLES[0]]
        self.assertIn("doc", job["aliases"])
        self.assertIn("surgeon", job["aliases"])


class TestDoctorPatientTargeting(BaseEvenniaTest):
    """The doctor works on whoever is lying on the AutoDoc, not just the speaker."""

    def test_patient_is_the_autodoc_occupant(self):
        from typeclasses.furniture import AutoDoc
        doc = create_object("typeclasses.llm_npc.LLMNpc", key="Doc",
                            location=self.room1)
        pod = create_object(AutoDoc, key="autodoc", location=self.room1)
        patient = create_object("typeclasses.characters.Character", key="Pat",
                                location=self.room1)
        patient.db.furniture = pod                # lying on the table
        speaker = create_object("typeclasses.characters.Character", key="Spk",
                                location=self.room1)
        self.assertEqual(worldclinic.patient_for(doc, speaker), patient)

    def test_patient_falls_back_to_speaker(self):
        doc = create_object("typeclasses.llm_npc.LLMNpc", key="Doc2",
                            location=self.room1)
        speaker = create_object("typeclasses.characters.Character", key="Spk2",
                                location=self.room1)
        self.assertEqual(worldclinic.patient_for(doc, speaker), speaker)   # no AutoDoc, no patient


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
        doc = create_object("typeclasses.llm_npc.LLMNpc", key="Doc3",
                            location=self.room1)
        self.assertEqual(worldclinic.resolve_cyberware("right eye")[0], "CYBER_RIGHT_EYE")
        self.assertEqual(worldclinic.resolve_cyberware("a new heart")[0],
                         "CYBERNETIC_HEART")
        self.assertEqual(worldclinic.resolve_cyberware("cyber arm, left"),
                         ("CYBER_ARM", "left"))
        self.assertEqual(worldclinic.resolve_cyberware("nanite cloud"), (None, None))

    def test_build_install_chart_lays_out_surgery(self):
        from world.medical import charts as chart_lib
        doc = create_object("typeclasses.llm_npc.LLMNpc", key="Doc4",
                            location=self.room1)
        patient = create_object("typeclasses.characters.Character", key="Pat4",
                                location=self.room1)
        chart = worldclinic.build_install_chart(doc, patient, "cyber arm left")
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
        d._parse_medical_request = worldclinic.parse_medical_request
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
        # the intercept is now the GENERIC one — a doctor is a post-holder
        # like any other (#2352)
        d._is_gratitude = llmnpc.LLMNpcMixin._is_gratitude
        d._handle_directed_speech = \
            llmnpc.LLMNpcMixin._handle_directed_speech.__get__(
                d, llmnpc.LLMNpc)
        return d

    def test_directed_install_routes(self):
        d = self._doctor(("install", "put a chrome arm on me"))
        with patch.object(worldclinic, "delay") as dl, \
                patch("world.service.post_for", return_value=MagicMock()), \
                patch("world.service.handler_for",
                      return_value=worldclinic.serve_at_clinic):
            handled = d._handle_directed_speech("put a chrome arm on me",
                                                MagicMock(), {})
        self.assertTrue(handled)
        self.assertEqual(dl.call_args.args[1], worldclinic.install_cyber)

    def test_directed_treat_routes(self):
        d = self._doctor(("treat", "gimme a painkiller"))
        with patch.object(worldclinic, "delay") as dl, \
                patch("world.service.post_for", return_value=MagicMock()), \
                patch("world.service.handler_for",
                      return_value=worldclinic.serve_at_clinic):
            handled = d._handle_directed_speech("gimme a painkiller",
                                                MagicMock(), {})
        self.assertTrue(handled)
        self.assertEqual(dl.call_args.args[1], worldclinic.treat)

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


class TestHoldingTheClinicPostIsTheQualification(BaseEvenniaTest):
    """The clinic is the last venue where competence rode the typeclass.

    It had no live gap when this was ported — both doctor posts were held
    by `Doctor` keepers — but every other 24/7 venue in the colony was
    dark two thirds of the time for exactly this reason, and the
    blueprint table cannot stop naming role typeclasses while one venue
    still depends on one (#2352). The `medic` post is the near one: it
    runs `policy=successor` with no blueprint, so a generic soul takes it
    the moment it falls vacant.
    """

    def setUp(self):
        super().setUp()
        from evennia import create_object
        from world.souls.posts import register_post
        self.station = create_object("typeclasses.items.Item",
                                     key="a billing terminal",
                                     location=self.room1)
        register_post(self.station, "medic", shifts=("day",))
        self.keeper = create_object("typeclasses.llm_npc.LLMNpc",
                                    key="Maritza", location=self.room1)
        self.station.db.post_slots = {
            "day": {"keeper": self.keeper, "vacant_since": None}}
        self.patient = self.char1
        self.patient.location = self.room1

    def _ask(self, line):
        with patch("world.souls.posts.current_shift", return_value="day"), \
                patch.object(worldclinic, "delay") as dl:
            handled = self.keeper._handle_directed_speech(
                line, self.patient, {"addressed": True})
        return handled, dl

    def test_a_plain_npc_on_the_post_treats(self):
        handled, dl = self._ask("gimme a painkiller")
        self.assertTrue(handled)
        self.assertEqual(dl.call_args.args[1], worldclinic.treat)

    def test_a_symptom_is_not_a_request(self):
        """Diagnosis-driven treatment belongs to the sim, not the words."""
        handled, _dl = self._ask("my arm hurts")
        self.assertFalse(handled)

    def test_a_question_is_not_a_request(self):
        handled, _dl = self._ask("can you do anything about a painkiller?")
        self.assertFalse(handled)
