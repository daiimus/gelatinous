"""LLMNpcMixin long-term-memory wiring (Phase 2 slice 3).

Methods bound to a MagicMock stand-in (the file's established pattern), so no
Evennia boot — just the recall-before-generate and the write-after-turn flows.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import typeclasses.llm_npc as llmnpc
from world.llm import memory as mem


def _bind(b, name):
    setattr(b, name, getattr(llmnpc.LLMNpcMixin, name).__get__(b, llmnpc.LLMNpcMixin))


class TestStoreMemory(TestCase):
    def test_embeds_then_saves_record(self):
        b = MagicMock()
        b._memory_subject = lambda p: f"#{p.id}"
        b._load_memories = lambda: []
        b._llm_silent = lambda: None
        _bind(b, "_store_memory")
        patron = MagicMock()
        patron.id = 5
        with patch.object(llmnpc, "request_embedding") as re:
            b._store_memory(patron, "a man", "i want the VIP room", "not tonight")
        re.assert_called_once()
        self.assertIn("VIP room", re.call_args.args[0])          # embedded text
        # firing the embed callback writes the record
        re.call_args.kwargs["on_done"]([0.1, 0.2, 0.3])
        saved = b.db.llm_memories
        self.assertEqual(len(saved), 1)
        self.assertIn("VIP room", saved[0]["text"])
        self.assertEqual(saved[0]["subject"], "#5")
        self.assertEqual(saved[0]["embedding"], [0.1, 0.2, 0.3])

    def test_no_line_no_write(self):
        b = MagicMock()
        _bind(b, "_store_memory")
        with patch.object(llmnpc, "request_embedding") as re:
            b._store_memory(MagicMock(), "a man", "", "hi")
        re.assert_not_called()


class TestActionAwareness(TestCase):
    def _npc(self):
        b = MagicMock()
        b.db.llm_driven = True
        b.ndb.action_buffer = None
        b._is_npc_speaker = lambda s: False
        for m in ("at_msg_receive", "_observe_action", "_drain_actions"):
            _bind(b, m)
        return b

    def test_ambient_pose_is_observed_not_reacted(self):
        b = self._npc()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b.at_msg_receive(text="the drifter pisses on the bar",
                             from_obj=MagicMock(), type="pose")  # not addressed
        d.assert_not_called()   # observed cheaply, NO LLM reaction
        self.assertEqual(b.ndb.action_buffer,
                         ["the drifter pisses on the bar"])

    def test_addressed_pose_triggers_action_reaction(self):
        b = self._npc()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b.at_msg_receive(text="a lean man runs a hand up your arm",
                             from_obj=MagicMock(), type="pose", addressed=True)
        self.assertIn("a lean man runs a hand up your arm", b.ndb.action_buffer)
        d.assert_called_once()                  # observed AND reacts
        self.assertIn("action", d.call_args.args)

    def test_addressed_pose_from_npc_ignored(self):
        b = self._npc()
        b._is_npc_speaker = lambda s: True      # another NPC posing at us
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b.at_msg_receive(text="the bartender nods at you",
                             from_obj=MagicMock(), type="pose", addressed=True)
        d.assert_not_called()                   # loop guard: observe, don't react

    def test_drain_returns_and_clears(self):
        b = self._npc()
        b._observe_action(MagicMock(), "a does X")
        b._observe_action(MagicMock(), "b does Y")
        self.assertEqual(b._drain_actions(), ["a does X", "b does Y"])
        self.assertEqual(b._drain_actions(), [])     # cleared after drain

    def test_buffer_caps(self):
        b = self._npc()
        for i in range(llmnpc.LLM_ACTION_BUFFER + 5):
            b._observe_action(MagicMock(), f"act {i}")
        self.assertEqual(len(b.ndb.action_buffer), llmnpc.LLM_ACTION_BUFFER)


class TestDossier(TestCase):
    def _npc(self, dossiers):
        b = MagicMock()
        b.db.llm_dossiers = dossiers
        for m in ("_dossiers", "_relationship_line", "_note_alias",
                  "_set_valence"):
            _bind(b, m)
        return b

    def test_set_valence_persists(self):
        b = self._npc({})
        b._set_valence("#5", "fed up with their bullshit")
        self.assertEqual(b.db.llm_dossiers["#5"]["valence"],
                         "fed up with their bullshit")

    def test_valence_surfaces_in_relationship_line(self):
        b = self._npc({})
        b._set_valence("#5", "wary")
        # re-read what _set_valence wrote
        b.db.llm_dossiers = b.db.llm_dossiers
        line = b._relationship_line("#5", MagicMock())
        self.assertIn("wary", line)

    def test_relationship_line_none_for_stranger(self):
        self.assertIsNone(self._npc({})._relationship_line("#5", MagicMock()))

    def test_relationship_line_with_aliases_and_valence(self):
        b = self._npc({"#5": {"aliases": ["the foot guy", "Bob"],
                              "valence": "wary"}})
        line = b._relationship_line("#5", MagicMock())
        self.assertIn("the foot guy", line)
        self.assertIn("Bob", line)
        self.assertIn("wary", line)

    def test_note_alias_appends_dedups_and_persists(self):
        b = self._npc({})
        b._note_alias("#5", "the foot guy")
        b._note_alias("#5", "the foot guy")   # dup ignored
        b._note_alias("#5", "Bob")
        self.assertEqual(b.db.llm_dossiers["#5"]["aliases"],
                         ["the foot guy", "Bob"])


class TestRememberTool(TestCase):
    def _npc(self):
        b = MagicMock()
        b.location = "room"
        _bind(b, "_handle_action_tool")
        _bind(b, "_remember_person")
        return b

    def test_remember_routes_to_real_command(self):
        b = self._npc()
        patron = MagicMock()
        patron.get_display_name = lambda looker=None, **k: "a gaunt drifter"
        with patch("world.identity.get_assigned_name", return_value=None):
            b._handle_action_tool("remember", "the cagey one", patron)
        b.execute_cmd.assert_called_once_with(
            "remember a gaunt drifter as the cagey one")

    def test_skips_when_already_named(self):
        b = self._npc()
        patron = MagicMock()
        patron.get_display_name = lambda looker=None, **k: "the cagey one"
        with patch("world.identity.get_assigned_name",
                   return_value="the cagey one"):
            b._handle_action_tool("remember", "the cagey one", patron)
        b.execute_cmd.assert_not_called()      # no churn re-naming

    def test_base_mixin_ignores_drink_tool(self):
        b = self._npc()
        b._handle_action_tool("prepare_drink", "Negroni", MagicMock())
        b.execute_cmd.assert_not_called()       # drinks are the bartender's job

    def test_feel_routes_to_set_valence(self):
        b = self._npc()
        b._memory_subject = lambda p: "#5"
        b._set_valence = MagicMock()
        b._handle_action_tool("feel", "wary", MagicMock())
        b._set_valence.assert_called_once_with("#5", "wary")


class TestRecall(TestCase):
    def _npc(self, memories):
        b = MagicMock()
        b.db.llm_driven = True
        b.location = "room"
        b.ndb.last_llm = 0
        b._memory_subject = lambda p: f"#{p.id}"
        b._load_memories = lambda: memories
        b._relationship_line = lambda subject, patron: None
        b._drain_actions = lambda: []
        b._perceive = lambda p: None
        b._recent_history = lambda p: []
        b._agentic_round = MagicMock()
        b._llm_silent = lambda: None
        _bind(b, "_try_llm_reply")
        return b

    def _patron(self):
        p = MagicMock()
        p.id = 5
        p.location = "room"
        p.get_display_name = lambda looker=None, **k: "a man"
        return p

    def test_recall_injects_memories(self):
        rec = mem.make_record("he asked about the VIP", [1.0, 0.0], subject="#5")
        b, patron = self._npc([rec]), self._patron()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "build_persona", return_value={}), \
                patch.object(llmnpc, "request_embedding") as re, \
                patch.object(llmnpc, "build_messages", return_value=["m"]) as bm:
            b._try_llm_reply("tell me about the VIP", patron, "directed")
            re.assert_called_once()                       # memories exist → embed
            re.call_args.kwargs["on_done"]([1.0, 0.0])    # query ~ the memory
        self.assertIn("he asked about the VIP",
                      bm.call_args.kwargs.get("memories") or [])
        b._agentic_round.assert_called_once()

    def test_skip_embed_when_no_memories(self):
        b, patron = self._npc([]), self._patron()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "build_persona", return_value={}), \
                patch.object(llmnpc, "request_embedding") as re, \
                patch.object(llmnpc, "build_messages", return_value=["m"]) as bm:
            b._try_llm_reply("hi", patron, "directed")
        re.assert_not_called()                            # nothing to recall
        self.assertIsNone(bm.call_args.kwargs.get("memories"))
        b._agentic_round.assert_called_once()


class TestConversationHold(TestCase):
    """RP-session continuity: poses refresh the hold, the engaged partner
    stays 'directed' without re-naming the NPC, release ends it."""

    def _npc(self):
        b = MagicMock()
        b.db.llm_driven = True
        b.location = "room"
        b.ndb.last_llm = 0
        b.ndb.llm_engaged_until = None
        b.ndb.llm_engaged_with = None
        b._memory_subject = lambda p: f"#{p.id}"
        b._load_memories = lambda: []
        b._relationship_line = lambda subject, patron: None
        b._drain_actions = lambda: []
        b._perceive = lambda p: None
        b._recent_history = lambda p: []
        b._agentic_round = MagicMock()
        b._llm_silent = lambda: None
        b._hist_key = lambda p: f"#{p.id}"
        b._is_npc_speaker = lambda s: False
        for m in ("_try_llm_reply", "_classify_speech", "_is_engaged_with",
                  "_handle_action_tool"):
            _bind(b, m)
        return b

    def _patron(self):
        p = MagicMock()
        p.id = 5
        p.location = "room"
        return p

    def test_directed_pose_refreshes_hold(self):
        b, patron = self._npc(), self._patron()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "build_persona", return_value={}), \
                patch.object(llmnpc, "build_messages", return_value=["m"]):
            b._try_llm_reply("leans close", patron, "action")
        self.assertIsNotNone(b.ndb.llm_engaged_until)
        self.assertEqual(b.ndb.llm_engaged_with, "#5")

    def test_engaged_partner_stays_directed_in_a_crowd(self):
        from time import monotonic
        b, patron = self._npc(), self._patron()
        b.ndb.llm_engaged_until = monotonic() + 60
        b.ndb.llm_engaged_with = "#5"
        b._mentions_self = lambda s: False
        b._is_alone_with = lambda s: False      # crowded room
        self.assertEqual(b._classify_speech("more of that", patron), "directed")

    def test_stranger_stays_ambient_while_npc_is_engaged(self):
        from time import monotonic
        b = self._npc()
        b.ndb.llm_engaged_until = monotonic() + 60
        b.ndb.llm_engaged_with = "#5"
        b._mentions_self = lambda s: False
        b._is_alone_with = lambda s: False
        other = MagicMock()
        other.id = 9
        self.assertEqual(b._classify_speech("hey", other), "ambient")

    def test_expired_hold_is_not_engagement(self):
        b, patron = self._npc(), self._patron()
        b.ndb.llm_engaged_until = 1.0          # long past
        b.ndb.llm_engaged_with = "#5"
        self.assertFalse(b._is_engaged_with(patron))

    def test_release_clears_hold_and_partner(self):
        b = self._npc()
        b.ndb.llm_engaged_until = 123.0
        b.ndb.llm_engaged_with = "#5"
        b._handle_action_tool("release", "", MagicMock())
        self.assertIsNone(b.ndb.llm_engaged_until)
        self.assertIsNone(b.ndb.llm_engaged_with)


class TestStyleTool(TestCase):
    def _npc(self):
        b = MagicMock()
        _bind(b, "_handle_action_tool")
        return b

    def test_remove_and_wear_route_to_real_commands(self):
        b = self._npc()
        b._handle_action_tool("style", "remove mesh top", MagicMock())
        b.execute_cmd.assert_called_once_with("remove mesh top")
        b.execute_cmd.reset_mock()
        b._handle_action_tool("style", "wear long coat", MagicMock())
        b.execute_cmd.assert_called_once_with("wear long coat")

    def test_unknown_verb_refused(self):
        b = self._npc()
        b._handle_action_tool("style", "eat hat", MagicMock())
        b.execute_cmd.assert_not_called()

    def test_natural_synonyms_map_to_real_verbs(self):
        # the model writes in its own register — normalise, don't drop
        for arg, cmd in (("take off mesh top", "remove mesh top"),
                         ("put on long coat", "wear long coat"),
                         ("strip slit skirt", "remove slit skirt"),
                         ("shed cropped jacket", "remove cropped jacket")):
            b = self._npc()
            b._handle_action_tool("style", arg, MagicMock())
            b.execute_cmd.assert_called_once_with(cmd)

    def test_possessive_and_state_parenthetical_stripped(self):
        # "her mesh top (unzipped)" — possessive lead + the wardrobe card's
        # style-state suffix both break the command matcher
        b = self._npc()
        b._handle_action_tool("style", "remove her mesh top (unzipped)",
                              MagicMock())
        b.execute_cmd.assert_called_once_with("remove mesh top")


class TestEchoGuard(TestCase):
    """A pose aimed at the NPC must never come straight back as its reply."""

    def _turn(self, turn, line):
        b = MagicMock()
        _bind(b, "_on_turn")
        with patch.object(llmnpc, "parse_turn", return_value=dict(turn)), \
                patch.object(llmnpc, "tool_names", return_value=[]):
            b._on_turn([], {}, MagicMock(), line, "a man", lambda: None, 0,
                       None, "{}")
        return b._render_llm_reply.call_args.args

    def test_parroted_pose_dropped_before_render(self):
        line = "runs a hand down the synth's arm, smiling slowly"
        speech, action = self._turn(
            {"speech": None, "thought": None, "tool": "none", "tool_argument": "",
             "action": "runs a hand down the synth's arm, smiling"}, line)[:2]
        self.assertIsNone(action)

    def test_original_action_renders(self):
        speech, action = self._turn(
            {"speech": "mm", "thought": None, "tool": "none", "tool_argument": "",
             "action": "arches into the touch, unhurried"},
            "runs a hand down the synth's arm")[:2]
        self.assertEqual(action, "arches into the touch, unhurried")


class TestForcePerception(TestCase):
    """Admin `force` speaks THROUGH the NPC — the brain must own the act."""

    def _npc(self):
        b = MagicMock()
        b.db.llm_driven = True
        b.ndb.action_buffer = None
        _bind(b, "perceive_forced_command")
        _bind(b, "_observe_action")
        return b

    def test_forced_say_reads_as_own_words(self):
        b = self._npc()
        b.perceive_forced_command("say follow me, quick")
        self.assertIn('You yourself just said: "follow me, quick"',
                      b.ndb.action_buffer)

    def test_forced_pose_reads_as_own_act(self):
        b = self._npc()
        b.perceive_forced_command("emote checks the door twice")
        self.assertIn("You yourself just did: checks the door twice",
                      b.ndb.action_buffer)

    def test_other_commands_buffer_verbatim(self):
        b = self._npc()
        b.perceive_forced_command("remove slit skirt")
        self.assertIn("You yourself just did this: remove slit skirt",
                      b.ndb.action_buffer)

    def test_not_llm_driven_ignored(self):
        b = self._npc()
        b.db.llm_driven = False
        b.perceive_forced_command("say hi")
        self.assertFalse(b.ndb.action_buffer)


class TestCmdForceHook(TestCase):
    def _cmd(self, targ):
        from commands.CmdAdmin import CmdForce
        cmd = CmdForce()
        cmd.caller = MagicMock()
        cmd.caller.search.return_value = targ
        cmd.msg = MagicMock()
        cmd.args = "bliss = say hello there"
        cmd.parse()
        return cmd

    def test_force_notifies_llm_brain(self):
        targ = MagicMock()
        targ.access.return_value = True
        self._cmd(targ).func()
        targ.execute_cmd.assert_called_once_with("say hello there")
        targ.perceive_forced_command.assert_called_once_with("say hello there")

    def test_plain_object_without_brain_still_forced(self):
        targ = MagicMock(spec=["access", "execute_cmd"])
        targ.access.return_value = True
        self._cmd(targ).func()
        targ.execute_cmd.assert_called_once_with("say hello there")


class TestRoomDescPerception(TestCase):
    def test_perceived_desc_ansi_stripped(self):
        from typeclasses.llm_persona import _room_desc
        npc = MagicMock()
        npc.location.get_display_desc = (
            lambda looker, **kw: "|rNeon|n  bleeds over   wet ferrocrete.")
        self.assertEqual(_room_desc(npc), "Neon bleeds over wet ferrocrete.")

    def test_falls_back_to_db_desc(self):
        from typeclasses.llm_persona import _room_desc
        npc = MagicMock()
        npc.location = MagicMock(spec=["db"])
        npc.location.db.desc = "A bare service corridor."
        self.assertEqual(_room_desc(npc), "A bare service corridor.")

    def test_long_desc_sentence_bounded(self):
        from typeclasses.llm_persona import _room_desc
        npc = MagicMock()
        npc.location.get_display_desc = (
            lambda looker, **kw: ("A sentence about the street. " * 40))
        out = _room_desc(npc)
        self.assertLessEqual(len(out), 500)
        self.assertTrue(out.endswith("street."))

    def test_no_location_none(self):
        from typeclasses.llm_persona import _room_desc
        npc = MagicMock()
        npc.location = None
        self.assertIsNone(_room_desc(npc))


class TestSecondPersonResolution(TestCase):
    """Surviving second-person in an ACTION resolves onto the patron's handle
    so the emote engine renders it per-observer (bystanders read the name,
    the target reads you/your)."""

    def _npc(self):
        b = MagicMock()
        b._address_handle = lambda p: "the lean man"
        _bind(b, "_resolve_second_person")
        return b

    def test_bare_you_becomes_handle(self):
        b = self._npc()
        out = b._resolve_second_person(
            "presses you against the wall, pinning you there", MagicMock())
        self.assertEqual(out, "presses the lean man against the wall, "
                              "pinning the lean man there")

    def test_your_becomes_handle_possessive(self):
        b = self._npc()
        out = b._resolve_second_person("traces your collarbone", MagicMock())
        self.assertEqual(out, "traces the lean man's collarbone")

    def test_yourself_becomes_handle(self):
        b = self._npc()
        out = b._resolve_second_person("lets you steady yourself", MagicMock())
        self.assertEqual(out, "lets the lean man steady the lean man")

    def test_contractions_survive(self):
        b = self._npc()
        out = b._resolve_second_person("hums like you've never heard",
                                       MagicMock())
        self.assertIn("you've never heard", out)

    def test_quoted_speech_untouched(self):
        b = self._npc()
        out = b._resolve_second_person(
            'leans close to you, "you want to play dress-up with me,"',
            MagicMock())
        self.assertIn('"you want to play dress-up with me,"', out)
        self.assertTrue(out.startswith("leans close to the lean man"))

    def test_no_handle_no_rewrite(self):
        b = MagicMock()
        b._address_handle = lambda p: None
        _bind(b, "_resolve_second_person")
        out = b._resolve_second_person("watches you", MagicMock())
        self.assertEqual(out, "watches you")


class TestRememberNameGuard(TestCase):
    def _npc(self):
        b = MagicMock()
        b.location = "room"
        _bind(b, "_remember_person")
        return b

    def test_pronoun_names_rejected(self):
        for junk in ("you", "You.", "him", "her", "them"):
            b = self._npc()
            b._remember_person(MagicMock(), junk)
            b.execute_cmd.assert_not_called()

    def test_contentless_names_rejected(self):
        # determiner/demonstrative + generic person-word = not a name
        for junk in ("that guy", "the one", "this one", "that man",
                     "the lady", "you two"):
            b = self._npc()
            b._remember_person(MagicMock(), junk)
            b.execute_cmd.assert_not_called()

    def test_contentful_names_accepted(self):
        for good in ("the foot guy", "tab dodger", "Roony",
                     "the negotiating ninja"):
            b = self._npc()
            patron = MagicMock()
            patron.get_display_name = lambda looker=None, **k: "a lean man"
            with patch("world.identity.get_assigned_name", return_value=None):
                b._remember_person(patron, good)
            b.execute_cmd.assert_called_once_with(
                f"remember a lean man as {good}")

    def test_trailing_punctuation_stripped(self):
        b = self._npc()
        patron = MagicMock()
        patron.get_display_name = lambda looker=None, **k: "a lean man"
        with patch("world.identity.get_assigned_name", return_value=None):
            b._remember_person(patron, "the negotiating ninja.")
        b.execute_cmd.assert_called_once_with(
            "remember a lean man as the negotiating ninja")


class TestActionConjugation(TestCase):
    """A small RP model writes base-form pose verbs ('fill an empty pint');
    the action renders as '<name> <action>' with no conjugation, so the verb
    must be agreed to third-person singular in code (#1224 follow-up)."""

    def _npc(self):
        b = MagicMock()
        b._NOT_A_LEADING_VERB = llmnpc.LLMNpcMixin._NOT_A_LEADING_VERB
        _bind(b, "_conjugate_action")
        return b

    def test_leading_base_verb_agreed(self):
        self.assertEqual(self._npc()._conjugate_action("fill an empty pint"),
                         "fills an empty pint")

    def test_each_clause_verb_agreed(self):
        b = self._npc()
        self.assertEqual(
            b._conjugate_action(
                "dry a glass with a rag and decant a brassy pint alongside"),
            "dries a glass with a rag and decants a brassy pint alongside")

    def test_then_and_comma_clauses(self):
        b = self._npc()
        self.assertEqual(
            b._conjugate_action("move the half-pint into place then polish it"),
            "moves the half-pint into place then polishes it")

    def test_already_conjugated_left_alone(self):
        b = self._npc()
        self.assertEqual(b._conjugate_action("wipes the bar, tracking the man"),
                         "wipes the bar, tracking the man")

    def test_quoted_speech_untouched(self):
        b = self._npc()
        out = b._conjugate_action('nods slow, "fill it yourself" and turns away')
        self.assertEqual(out, 'nods slow, "fill it yourself" and turns away')

    def test_non_verb_openers_skipped(self):
        # a clause that opens on a determiner/adverb, not a verb
        b = self._npc()
        self.assertEqual(b._conjugate_action("slowly leans in"), "slowly leans in")


class TestPromptNoBracketBlocks(TestCase):
    """Context blocks must NOT be [bracket]-wrapped: a small RP model copies an
    inline `[gloss]` shape into dialogue ('Lotta GANES [a nightrunner]…')."""

    def test_context_blocks_have_no_enclosing_brackets(self):
        import re as _re
        from world.llm import prompt as P
        persona = {"persona_seed": {"archetype": "bartender", "name": "Del",
                                    "pronouns": "she/her", "description": "keeper",
                                    "personality": "warm"}}
        msgs = P.build_messages(
            persona, "a lean man", "how's your day?", "directed",
            perception="a lean man in a scuffed jacket",
            present=["a wiry woman with a shaved head"],
            events=["a droog knocked over a stool"],
            memories=["the lean man tips well"])
        blob = "\n".join(m["content"] for m in msgs)
        self.assertEqual(_re.findall(r"\[[^\]]{1,40}\]", blob), [])
        # the labels still anchor the blocks
        for label in ("PRESENT", "PERCEPTION", "RECENTLY", "MEMORY"):
            self.assertIn(label, blob)


class TestReflexiveGesture(TestCase):
    """The model writes a self-gesture in the second person ('cock your head')
    because the prompt addresses IT as 'you'; that must resolve to the NPC's own
    pronoun BEFORE _resolve_second_person claims the 'your' for the patron.
    Ambiguous, genuinely patron-directed possessives must be left alone."""

    def _npc(self, gender="male"):
        b = MagicMock()
        b.gender = gender
        b._REFLEXIVE_GESTURE_VERBS = llmnpc.LLMNpcMixin._REFLEXIVE_GESTURE_VERBS
        b._REFLEXIVE_GESTURE_PARTS = llmnpc.LLMNpcMixin._REFLEXIVE_GESTURE_PARTS
        _bind(b, "_selfify_reflexive_gesture")
        return b

    def test_the_live_bug(self):
        # "cocks your head" (already conjugated) -> the NPC's own head
        out = self._npc()._selfify_reflexive_gesture(
            "cocks your head, weathered face ticking")
        self.assertEqual(out, "cocks his head, weathered face ticking")

    def test_common_self_gestures(self):
        b = self._npc()
        cases = {
            "rolls your shoulders": "rolls his shoulders",
            "cracks your knuckles": "cracks his knuckles",
            "shakes your head slow": "shakes his head slow",
            "arches your brow": "arches his brow",          # -es sibilant form
            "scratches your jaw": "scratches his jaw",       # -es sibilant form
            "cock your damn head": "cock his damn head",     # base + adjective
        }
        for src, want in cases.items():
            self.assertEqual(b._selfify_reflexive_gesture(src), want)

    def test_gender_possessive(self):
        self.assertEqual(
            self._npc("female")._selfify_reflexive_gesture("cocks your head"),
            "cocks her head")
        self.assertEqual(
            self._npc("nonbinary")._selfify_reflexive_gesture("cocks your head"),
            "cocks their head")

    def test_patron_directed_left_untouched(self):
        # ambiguous verbs with real directed uses fall through to the
        # second-person resolver — a bartender handling the PATRON's body
        b = self._npc()
        for src in ("tilts your chin up to meet his eyes",
                    "cups your jaw", "lifts your head",
                    "presses your head to the bar", "takes your hand"):
            self.assertEqual(b._selfify_reflexive_gesture(src), src)

    def test_quoted_speech_skipped(self):
        b = self._npc()
        out = b._selfify_reflexive_gesture('grins, "watch your head" and turns')
        self.assertEqual(out, 'grins, "watch your head" and turns')


class TestWieldTool(TestCase):
    """The wield action tool routes natural draw/holster phrasing onto the REAL
    Mr. Hands commands (wield / unwield), so hand state and fiction agree."""

    def _npc(self):
        b = MagicMock()
        b.location = "room"
        _bind(b, "_handle_action_tool")
        return b

    def _wield(self, arg):
        b = self._npc()
        b._handle_action_tool("wield", arg, MagicMock())
        return b.execute_cmd.call_args.args[0] if b.execute_cmd.called else None

    def test_draw_family_routes_to_wield(self):
        for arg, want in (("draw the shotgun", "wield shotgun"),
                          ("the boomstick", "wield boomstick"),
                          ("bring out my coach gun", "wield coach gun"),
                          ("wield reaper in right", "wield reaper in right")):
            self.assertEqual(self._wield(arg), want)

    def test_holster_family_routes_to_unwield(self):
        for arg, want in (("holster the pistol", "unwield pistol"),
                          ("unwield shotgun", "unwield shotgun"),
                          ("put the shotgun away", "unwield shotgun"),
                          ("set the knife down", "unwield knife")):
            self.assertEqual(self._wield(arg), want)

    def test_empty_arg_no_command(self):
        b = self._npc()
        b._handle_action_tool("wield", "", MagicMock())
        b.execute_cmd.assert_not_called()

    def test_style_parenthetical_stripped(self):
        self.assertEqual(self._wield("draw the shotgun (loaded)"), "wield shotgun")
