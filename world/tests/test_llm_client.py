"""The LLM client transport — pure bits (URL derivation). The networked calls
(request_turn / request_embedding) run via run_async and are exercised through
the bartender/NPC routing tests."""

from unittest import TestCase
from unittest.mock import patch

from world.llm import client


class TestEmbedUrl(TestCase):
    def test_derives_from_chat_url(self):
        with patch.object(client, "settings") as s:
            s.LLM_GM_EMBED_URL = ""
            s.LLM_GM_URL = "http://host.docker.internal:8765/v1/chat/completions"
            self.assertEqual(client._embed_url(),
                             "http://host.docker.internal:8765/v1/embeddings")

    def test_explicit_override_wins(self):
        with patch.object(client, "settings") as s:
            s.LLM_GM_EMBED_URL = "http://elsewhere/embed"
            s.LLM_GM_URL = "http://host/v1/chat/completions"
            self.assertEqual(client._embed_url(), "http://elsewhere/embed")
