"""LLM Gamemaster sidecar client — off-reactor calls to the MLX sidecar.

The sidecar is an external, native process (see
``specs/proposals/LLM_GAMEMASTER_SPEC.md``; it lives out-of-repo in
``~/llm-gm-spike`` for Phase 1) that voices NPCs. Calls cross the Twisted reactor
and must NEVER block it: the blocking ``requests.post`` runs in Evennia's async
thread pool via ``run_async`` — exactly the pattern the GitHub calls in
``commands/CmdBug.py`` use.

Contract (mirrors ``CmdBug._run_github_call``): the thread function does pure
network + parsing — NO Evennia object access, NO database reads/writes (SQLite is
not thread-safe). All needed values are captured on the reactor *before* this call
(the persona dict, the speaker name, the line); the reply is rendered in the
reactor-side ``at_return`` / ``at_err`` callbacks, where ``execute_cmd`` is safe.
"""

import requests
from django.conf import settings
from evennia.utils import logger
from evennia.utils.utils import run_async

#: Defaults if settings are absent — the game container reaches the host-native
#: sidecar via ``host.docker.internal`` (a ``127.0.0.1`` URL would mean the
#: container itself). Read defensively like ``CmdBug``'s ``getattr(settings, …)``.
_DEFAULT_URL = "http://host.docker.internal:8765/converse"
_DEFAULT_TIMEOUT = 12


def llm_enabled() -> bool:
    """Deployment-wide master switch for LLM-driven NPCs (one of two gates)."""
    return bool(getattr(settings, "LLM_GM_ENABLED", False))


def request_npc_reply(persona, speaker_name, line, mode, on_reply, on_fail):
    """POST a situation to the sidecar off the reactor; render on return.

    Args:
        persona (dict): inert, JSON-safe persona data, built on the reactor
            BEFORE this call (``typeclasses.llm_persona.build_persona``).
        speaker_name (str): how the NPC perceives the speaker.
        line (str): the spoken words.
        mode (str): ``"directed"`` or ``"ambient"``.
        on_reply (callable): ``on_reply(speech, action)`` — runs on the reactor.
        on_fail (callable): ``on_fail()`` — runs on the reactor on timeout, error,
            or an empty (declined) reply.
    """
    url = getattr(settings, "LLM_GM_URL", _DEFAULT_URL)
    timeout = getattr(settings, "LLM_GM_TIMEOUT", _DEFAULT_TIMEOUT)
    payload = {
        "persona": persona,
        "speaker": speaker_name,
        "line": line,
        "mode": mode,
    }

    def _thread_fn():
        # Pure network + parsing. NO Evennia/DB access (SQLite thread contract).
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("speech"), data.get("action"))

    def _at_return(result):
        speech, action = result if result else (None, None)
        if not speech and not action:
            on_fail()  # null/declined reply → scripted fallback or silence
            return
        on_reply(speech, action)

    def _at_err(failure):
        logger.log_err(f"LLM sidecar call failed: {failure}")
        on_fail()

    run_async(_thread_fn, at_return=_at_return, at_err=_at_err)
