"""LLM Gamemaster client — off-reactor calls over the OpenAI Chat Completions API.

The game speaks the **standard OpenAI Chat Completions protocol** to a configurable
endpoint (``settings.LLM_GM_URL``), so the inference backend is swappable without a
code change — our MLX sidecar, Ollama, llama.cpp, vLLM, LM Studio, or a cloud API.
The repo owns the portable prompt/parse logic (``world/llm/prompt.py``); the
backend is just an inference endpoint. This keeps Gelatinous LLM-platform-agnostic.

Calls cross the Twisted reactor and must NEVER block it: the blocking
``requests.post`` runs in Evennia's async thread pool via ``run_async`` — the same
pattern the GitHub calls in ``commands/CmdBug.py`` use. Contract: the thread
function does pure network + parsing — NO Evennia object access, NO database
reads/writes (SQLite is not thread-safe). All live values (the persona dict, the
speaker name, the line) are captured on the reactor *before* the call; the reply
renders in the reactor-side ``at_return`` / ``at_err`` callbacks.
"""

import requests
from django.conf import settings
from evennia.utils import logger
from evennia.utils.utils import run_async

from world.llm.prompt import build_messages, parse_reply

#: Defaults if settings are absent. The URL is a standard OpenAI Chat Completions
#: endpoint; from inside the game container the host-native backend is reached via
#: ``host.docker.internal`` (a ``127.0.0.1`` URL would mean the container itself).
_DEFAULT_URL = "http://host.docker.internal:8765/v1/chat/completions"
_DEFAULT_TIMEOUT = 15
_DEFAULT_MAX_TOKENS = 120
_DEFAULT_TEMPERATURE = 0.8


def llm_enabled() -> bool:
    """Deployment-wide master switch for LLM-driven NPCs (one of two gates)."""
    return bool(getattr(settings, "LLM_GM_ENABLED", False))


def request_npc_reply(persona, speaker_name, line, mode, on_reply, on_fail,
                      perception=None):
    """POST a turn to the chat-completions backend off the reactor; render on return.

    Args:
        persona (dict): inert, JSON-safe persona data, built on the reactor BEFORE
            this call (``typeclasses.llm_persona.build_persona``).
        speaker_name (str): how the NPC perceives the speaker.
        line (str): the spoken words.
        mode (str): ``"directed"`` or ``"ambient"``.
        on_reply (callable): ``on_reply(speech, action)`` — runs on the reactor.
        on_fail (callable): ``on_fail()`` — runs on the reactor on timeout, error,
            or an empty (declined) reply.
        perception (str|None): what the NPC sees when it looks at the speaker
            (ANSI-stripped), captured on the reactor — grounds description so the
            model can't invent the speaker's appearance.
    """
    url = getattr(settings, "LLM_GM_URL", _DEFAULT_URL)
    model = getattr(settings, "LLM_GM_MODEL", "")
    api_key = getattr(settings, "LLM_GM_API_KEY", "")
    timeout = getattr(settings, "LLM_GM_TIMEOUT", _DEFAULT_TIMEOUT)
    max_tokens = getattr(settings, "LLM_GM_MAX_TOKENS", _DEFAULT_MAX_TOKENS)
    temperature = getattr(settings, "LLM_GM_TEMPERATURE", _DEFAULT_TEMPERATURE)

    messages = build_messages(persona, speaker_name, line, mode, perception)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if model:
        body["model"] = model

    def _thread_fn():
        # Pure network + parsing. NO Evennia/DB access (SQLite thread contract).
        resp = requests.post(url, json=body, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content = (
            (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        )
        return parse_reply(content, persona)

    def _at_return(result):
        result = result or {}
        speech, action = result.get("speech"), result.get("action")
        if not speech and not action:
            on_fail()  # null/declined reply → scripted fallback or silence
            return
        on_reply(speech, action)

    def _at_err(failure):
        logger.log_err(f"LLM backend call failed: {failure}")
        on_fail()

    run_async(_thread_fn, at_return=_at_return, at_err=_at_err)
