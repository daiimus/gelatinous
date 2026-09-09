"""`LLM_GM_TEMPERATURE` is actually sent (#2769, second half).

A repo-wide grep for `LLM_GM_TEMPERATURE` found EXACTLY ONE occurrence:
the line in `server/conf/settings.py` that defines it. Nothing imported
it, and `world/llm/client.py` contained no reference to `temperature` in
any form -- so the field was absent from the request body entirely and
every GM-lane call ran at whatever default the backend happened to pick.

The dial was not merely unread; the parameter never reached the wire.

Its siblings are all live and read the same way -- `LLM_GM_ENABLED`,
`LLM_GM_URL`, `LLM_GM_MODEL`, `LLM_GM_API_KEY`, `LLM_GM_TIMEOUT`,
`LLM_GM_MAX_TOKENS` -- which is what made the omission easy to miss: the
file looks like it consumes the whole `LLM_GM_*` block, and it consumed
all of it but this.

That matters more here than a dead setting usually would. The project's
stated goal is a backend- and model-agnostic portable layer, and
temperature is the knob most likely to differ between backends and the
first one reached for when output register drifts. Setting it did
nothing and nothing said so.

NOT extended to the other three request bodies, deliberately:
  * the EMBEDDINGS body (`{"input": text}`) -- temperature is
    meaningless for an embedding, and sending it invites a 400 from a
    strict backend;
  * the two CIVIC bodies -- there is no `CIVIC_LLM_TEMPERATURE` setting
    to read, and inventing one is a new dial rather than a repair. The
    civic lane also does constrained decoding, where temperature matters
    far less.
"""
from unittest import mock

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest

from world.llm import client


class _Wire(EvenniaTest):
    """Capture the JSON body a request would put on the wire."""

    def _post_body(self, fn, *args, **kwargs):
        seen = {}

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "{}"}}],
                        "data": [{"embedding": [0.0]}]}

        def fake_post(url, json=None, **kw):
            seen["body"] = json
            return _Resp()

        # `run_async` would put the work on a thread; run it inline so
        # the body is built and posted within the test.
        def inline(thread_fn, at_return=None, at_err=None):
            try:
                result = thread_fn()
            except Exception as err:  # noqa: BLE001
                if at_err:
                    at_err(err)
                return
            if at_return:
                at_return(result)

        with mock.patch.object(client, "requests") as req, \
             mock.patch.object(client, "run_async", side_effect=inline):
            req.post.side_effect = fake_post
            fn(*args, **kwargs)
        return seen.get("body")


class TestTheGmTurnCarriesTemperature(_Wire):

    @override_settings(LLM_GM_TEMPERATURE=0.8)
    def test_it_is_on_the_wire(self):
        body = self._post_body(client.request_turn, [{"role": "user",
                                                      "content": "hi"}],
                               lambda *_a: None, lambda *_a: None)
        self.assertIn("temperature", body or {},
                      "no temperature reached the request body")

    @override_settings(LLM_GM_TEMPERATURE=0.15)
    def test_it_is_the_configured_value_not_a_constant(self):
        """Control: a hardcoded 0.8 would pass the test above."""
        body = self._post_body(client.request_turn, [{"role": "user",
                                                      "content": "hi"}],
                               lambda *_a: None, lambda *_a: None)
        self.assertEqual(body["temperature"], 0.15)

    @override_settings(LLM_GM_TEMPERATURE=0.8)
    def test_the_siblings_still_travel(self):
        """The body must not have been rebuilt around the new field."""
        body = self._post_body(client.request_turn, [{"role": "user",
                                                      "content": "hi"}],
                               lambda *_a: None, lambda *_a: None)
        self.assertIn("messages", body)
        self.assertIn("max_tokens", body)


class TestEmbeddingsDoNotGetOne(_Wire):

    @override_settings(LLM_GM_TEMPERATURE=0.8)
    def test_an_embedding_body_has_no_temperature(self):
        """Meaningless for an embedding, and a strict backend answers a
        400 rather than ignoring it."""
        body = self._post_body(client.request_embedding, "some text",
                               lambda *_a: None, lambda *_a: None)
        self.assertNotIn("temperature", body or {})
