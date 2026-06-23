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
        for m in ("at_msg_receive", "_observe_action", "_drain_actions"):
            _bind(b, m)
        return b

    def test_pose_is_observed_not_reacted(self):
        b = self._npc()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b.at_msg_receive(text="the drifter pisses on the bar",
                             from_obj=MagicMock(), type="pose")
        d.assert_not_called()   # observed cheaply, NO LLM reaction
        self.assertEqual(b.ndb.action_buffer,
                         ["the drifter pisses on the bar"])

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
        for m in ("_dossiers", "_relationship_line", "_note_alias"):
            _bind(b, m)
        return b

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
