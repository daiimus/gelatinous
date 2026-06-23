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


class TestRecall(TestCase):
    def _npc(self, memories):
        b = MagicMock()
        b.db.llm_driven = True
        b.location = "room"
        b.ndb.last_llm = 0
        b._memory_subject = lambda p: f"#{p.id}"
        b._load_memories = lambda: memories
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
