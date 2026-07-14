"""Opt-in per-turn decision log for the LLM Gamemaster.

Records the RAW model output beside the FINAL rendered text for every NPC turn,
so the game-side post-processing — verb conjugation, selfify, second-person +
reflexive-gesture resolution, echo-guard, quote-weaving — is auditable. This is
the piece the sidecar's ``conversation.log`` can't see: the sidecar logs the
prompt/context in and the raw JSON out, but the transform from raw output to what
players actually read happens here in the game.

OFF by default (``settings.LLM_GM_DECISION_LOG``) — a tuning instrument, not a
production log. Flip it on in ``secret_settings.py`` on the live box while dialing
a model in; each record is one JSON line under ``server/logs/llm_decisions.log``.
Never raises: logging must not break a turn.
"""

import json
import os
import time

from django.conf import settings


def decision_log_enabled():
    return bool(getattr(settings, "LLM_GM_DECISION_LOG", False))


def _logpath():
    return os.path.join(getattr(settings, "LOG_DIR", "."), "llm_decisions.log")


def log_decision(npc, speaker_name, line, raw_turn, rendered):
    """Append one turn: what the NPC heard, the raw model decision, and the
    final rendered channels. ``raw_turn`` is the parsed model dict; ``rendered``
    is ``{"action", "speech", "thought"}`` as they left the render (None where a
    channel was empty or woven into another)."""
    if not decision_log_enabled():
        return
    try:
        room = getattr(getattr(npc, "location", None), "key", None)
        rec = {
            "t": time.strftime("%Y-%m-%d %H:%M:%S"),
            "npc": f"{getattr(npc, 'key', '?')}({getattr(npc, 'dbref', '?')})",
            "room": room,
            "heard_from": speaker_name,
            "heard": line,
            "raw": {k: (raw_turn or {}).get(k) for k in
                    ("speech", "action", "thought", "tool", "tool_argument")},
            "rendered": rendered,
        }
        with open(_logpath(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — logging must never break a turn
        pass
