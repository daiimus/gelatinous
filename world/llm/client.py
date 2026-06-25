"""LLM Gamemaster client — off-reactor calls over OpenAI Chat Completions (MLX).

The game speaks the standard chat-completions protocol to a configurable endpoint
(``settings.LLM_GM_URL``); the backend is swappable. Each call passes
``TURN_SCHEMA`` so the backend (our MLX sidecar via ``outlines``) returns output
**guaranteed valid** against the unified ``{speech, action, tool}`` schema.

Calls never block the Twisted reactor: the blocking ``requests.post`` runs in
Evennia's async thread pool via ``run_async`` (the ``CmdBug`` pattern). The thread
does pure network — NO Evennia/DB access. The caller builds the ``messages`` (and
extends them across the agentic loop, §5.3) and orchestrates on the reactor in the
callbacks.
"""

import requests
from django.conf import settings
from evennia.utils import logger
from evennia.utils.utils import run_async

from world.llm.prompt import TURN_SCHEMA

_DEFAULT_URL = "http://host.docker.internal:8765/v1/chat/completions"
_DEFAULT_TIMEOUT = 40          # warm 24B constrained gen ~17s/round; cover one round + headroom
_DEFAULT_MAX_TOKENS = 160


def llm_enabled() -> bool:
    """Deployment-wide master switch for LLM-driven NPCs (one of two gates)."""
    return bool(getattr(settings, "LLM_GM_ENABLED", False))


def request_turn(messages, on_turn, on_fail, schema=None):
    """POST a constrained turn off the reactor; deliver the raw JSON to ``on_turn``.

    Args:
        messages (list): the full OpenAI ``messages`` (built + extended by the
            caller across the agentic loop).
        on_turn (callable): ``on_turn(raw_json_str)`` — runs on the reactor.
        on_fail (callable): ``on_fail()`` — runs on the reactor on error/empty.
        schema (dict): the constrained turn schema; defaults to the full-registry
            ``TURN_SCHEMA``. Callers pass ``prompt.schema_for(persona)`` to scope
            the ``tool`` enum to the NPC's archetype.
    """
    url = getattr(settings, "LLM_GM_URL", _DEFAULT_URL)
    model = getattr(settings, "LLM_GM_MODEL", "")
    api_key = getattr(settings, "LLM_GM_API_KEY", "")
    timeout = getattr(settings, "LLM_GM_TIMEOUT", _DEFAULT_TIMEOUT)
    max_tokens = getattr(settings, "LLM_GM_MAX_TOKENS", _DEFAULT_MAX_TOKENS)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {"messages": messages, "json_schema": schema or TURN_SCHEMA,
            "max_tokens": max_tokens}
    if model:
        body["model"] = model

    def _thread_fn():
        # Pure network + parsing. NO Evennia/DB access (SQLite thread contract).
        resp = requests.post(url, json=body, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")

    def _at_return(content):
        if not content:
            # Empty body = the model returned nothing usable — usually a turn
            # truncated against LLM_GM_MAX_TOKENS, occasionally a genuine decline.
            # Logged so a rash of fallbacks points at the right dial.
            logger.log_warn("LLM turn empty (no content — likely truncation; "
                            "check LLM_GM_MAX_TOKENS)")
            on_fail()
            return
        on_turn(content)

    def _at_err(failure):
        # Name the failure mode so we can dial the right knob: a *Timeout means
        # the turn ran past LLM_GM_TIMEOUT; a ConnectionError means the sidecar's
        # down; anything else is a backend bug.
        exc = getattr(failure, "value", failure)
        logger.log_err(f"LLM backend call failed [{type(exc).__name__}]: {exc}")
        on_fail()

    run_async(_thread_fn, at_return=_at_return, at_err=_at_err)


def _embed_url():
    """The embeddings endpoint, derived from the chat URL (override:
    ``settings.LLM_GM_EMBED_URL``)."""
    explicit = getattr(settings, "LLM_GM_EMBED_URL", "")
    if explicit:
        return explicit
    url = getattr(settings, "LLM_GM_URL", _DEFAULT_URL)
    return url.replace("/chat/completions", "/embeddings")


def request_embedding(text, on_done, on_fail):
    """Embed ``text`` off the reactor; deliver the vector (list[float]) to
    ``on_done`` (Phase 2 memory). Mirrors ``request_turn``'s thread contract —
    the thread does pure network, callbacks run on the reactor.
    """
    url = _embed_url()
    api_key = getattr(settings, "LLM_GM_API_KEY", "")
    timeout = getattr(settings, "LLM_GM_TIMEOUT", _DEFAULT_TIMEOUT)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {"input": text}

    def _thread_fn():
        resp = requests.post(url, json=body, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data") or []
        return items[0].get("embedding") if items else None

    def _at_return(vec):
        if not vec:
            on_fail()
            return
        on_done(vec)

    def _at_err(failure):
        logger.log_err(f"LLM embedding call failed: {failure}")
        on_fail()

    run_async(_thread_fn, at_return=_at_return, at_err=_at_err)
