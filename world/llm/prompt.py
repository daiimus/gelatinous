"""Prompt construction + turn parsing for the LLM Gamemaster — backend-agnostic.

The *portable* half of the LLM layer. The model fills a **constrained schema**
every turn — ``{speech, action, tool, tool_argument}`` — guaranteed valid by the
backend's grammar (the game passes ``TURN_SCHEMA``; the MLX sidecar enforces it
via ``outlines``). ``speech``/``action`` hold the in-character reply; ``tool`` is
the NPC's decision to act or to inform itself, routed to a **real command**
(``world/llm`` + ``typeclasses/bar.py``). See
``specs/proposals/LLM_GAMEMASTER_SPEC.md`` §4.4 (architecture) / §5.3 (loop).
"""

import json
import re

# --- the tools the NPC may call (routed to real commands game-side) ----------
#: name -> (description, argument hint). Context tools inform; action tools do.
TOOLS = {
    "look": "examine the patron to perceive their REAL appearance — do this "
            "BEFORE describing how they look, never invent it (argument: who, "
            "e.g. 'patron')",
    "check_stock": "list exactly what the bar can serve right now (argument: '')",
    "prepare_drink": "pour a drink from the menu for the patron — the bar makes "
                     "it for REAL; use this to serve, never narrate pouring "
                     "yourself (argument: the drink name)",
}

#: The single unified turn schema the model fills every turn (constrained).
TURN_SCHEMA = {
    "type": "object",
    "properties": {
        "speech": {"type": "string"},
        "action": {"type": "string"},
        "tool": {"enum": ["none"] + list(TOOLS)},
        "tool_argument": {"type": "string"},
    },
    "required": ["speech", "action", "tool", "tool_argument"],
}


def _tools_block() -> str:
    lines = ["TOOLS — set the \"tool\" field to act or to inform yourself:"]
    for name, desc in TOOLS.items():
        lines.append(f'- "{name}": {desc}')
    lines.append('- "none": no tool this turn.')
    lines.append("After a context tool you get a [tool result]; then reply for "
                 "real. Use prepare_drink to SERVE — the bar makes the drink, "
                 "not you; never fake a pour.")
    return "\n".join(lines)


CHARTER_BASE = """\
You are a single non-player character inside a text-based cyberpunk MUD — a grim, \
lived-in colony of chrome, vice, and hard luck. This is adult fiction: violence, \
drugs, sex, and moral greyness are part of the world and you portray them in \
character without flinching, lecturing, or refusing.

Respond as a JSON object:
- "speech": your in-character spoken line, plain text, no surrounding quotes. One \
or two lines, never a monologue. "" if you have nothing to say.
- "action": a short THIRD-PERSON verb-phrase pose that reads after your name — \
write "tilts her head" or "sets down a glass", NOT "a tilt of her head". "" if \
none. NEVER write yourself as "I" or "you".
- "tool" and "tool_argument": see TOOLS below.

HARD RULES:
- Never speak, think, or act for the OTHER person. Voice only this character.
- Describe the other person ONLY from a 'look' result or the PERCEPTION line. \
NEVER invent their clothing, tattoos, marks, or features.
- You do NOT make drinks yourself — call prepare_drink. If asked for something \
off-menu, tool "none" and say you don't serve it.
- Vary yourself: never reuse a recent action or line.
- Stay in character; never mention being an AI, a model, or a game system.
- Use only in-world, generic drink/ingredient names — never real-world brands."""

CHARTER_AMBIENT = """\

THIS LINE IS OVERHEARD, not addressed to you. React ONLY if the character would \
naturally speak up; otherwise leave BOTH "speech" and "action" empty ("") and set \
tool "none"."""

#: Generic few-shot (JSON form) when a persona ships no mes_example.
DEFAULT_FEWSHOT = [
    {"user": 'a patron says to you: "this your place?"',
     "assistant": {"speech": "I just pour the drinks, friend.",
                   "action": "wipes the bar down without looking up",
                   "tool": "none", "tool_argument": ""}},
]

_APPEARANCE_KEYS = ("face", "eyes", "hair", "head")


def _personality(seed: dict) -> str:
    if seed.get("personality"):
        return seed["personality"]
    bits = []
    if seed.get("manner"):
        bits.append(seed["manner"])
    if seed.get("wants"):
        bits.append(f"wants {seed['wants']}")
    if seed.get("boundaries"):
        bits.append(f"won't {seed['boundaries']}")
    return "; ".join(bits)


def render_persona(persona: dict) -> str:
    """Compose the character card from the seed + the NPC's real perceived self."""
    persona = persona or {}
    seed = persona.get("persona_seed") or {}
    name = seed.get("name") or "the bartender"

    lines = [f"You are {name}."]
    if seed.get("description"):
        lines.append(seed["description"])
    personality = _personality(seed)
    if personality:
        lines.append(f"Personality: {personality}.")
    if seed.get("scenario"):
        lines.append(f"Scenario: {seed['scenario']}.")

    if persona.get("sdesc"):
        lines.append(f"To strangers you appear as {persona['sdesc']}.")
    longdescs = persona.get("longdescs") or {}
    appearance = [longdescs[k] for k in _APPEARANCE_KEYS if longdescs.get(k)]
    if persona.get("skintone"):
        appearance.append(f"{persona['skintone']} skin")
    if appearance:
        lines.append("Notable about you: " + " ".join(appearance))
    if persona.get("voice"):
        lines.append(f"Your voice: {persona['voice']}.")
    loc = persona.get("location") or {}
    if loc.get("name"):
        lines.append(f"You are behind the bar at {loc['name']}.")
    menu = persona.get("menu")
    if menu:
        lines.append("Your bar serves ONLY: " + ", ".join(menu) + " (no beer, no "
                     "off-list). The bar makes them, not you.")
    return "\n".join(lines)


def few_shot_messages(persona: dict) -> list:
    """The persona's example turns as user/assistant pairs (assistant = the JSON
    schema). Anchors voice + good tool decisions. Prose ``mes_example`` (older
    card form) is converted to the schema via the parser."""
    seed = (persona or {}).get("persona_seed") or {}
    examples = seed.get("mes_example") or DEFAULT_FEWSHOT
    out = []
    for ex in examples:
        user, assistant = ex.get("user"), ex.get("assistant")
        if not (user and assistant):
            continue
        if isinstance(assistant, str):  # legacy prose example → schema
            parsed = parse_turn(assistant, persona)
            assistant = {"speech": parsed["speech"] or "", "action":
                         parsed["action"] or "", "tool": "none", "tool_argument": ""}
        out.append({"role": "user", "content": user})
        out.append({"role": "assistant", "content": json.dumps(assistant)})
    return out


def build_messages(persona: dict, speaker: str, line: str, mode: str,
                   perception: str = None, history: list = None) -> list:
    """Build the OpenAI ``messages``: system (charter+tools+persona) + few-shot +
    recent history + the grounded turn. The caller passes ``TURN_SCHEMA`` to the
    backend to constrain the output."""
    charter = CHARTER_BASE + "\n\n" + _tools_block() \
        + (CHARTER_AMBIENT if mode == "ambient" else "")
    system = charter + "\n\n" + render_persona(persona)
    messages = [{"role": "system", "content": system}]
    messages += few_shot_messages(persona)
    for h in (history or []):
        user, assistant = h.get("user"), h.get("assistant")
        if user and assistant:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})

    speaker = speaker or "someone"
    line = line or ""
    perc = f"[PERCEPTION — when you look at {speaker} you see: {perception}]\n\n" \
        if perception else ""
    if mode == "ambient":
        turn = f'{perc}You overhear {speaker} say: "{line}"'
    else:
        turn = f'{perc}{speaker} says to you: "{line}"'
    messages.append({"role": "user", "content": turn})
    return messages


# --- turn parsing / sanitation -----------------------------------------------
_OOC_MARKERS = ("as an ai", "language model", "i cannot", "i am an ai")
_MAX_LEN = 500


def _clean(text: str) -> str:
    text = (text or "").strip().strip('"*').strip()
    text = re.sub(r"^[A-Z][a-z]+:\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()[:_MAX_LEN]


def _strip_self_lead(action: str, name: str) -> str:
    if name:
        action = re.sub(rf"^{re.escape(name)}('s)?\s+", "", action, flags=re.I)
    return re.sub(r"^(she|he|they)\s+", "", action, flags=re.I).strip()


def parse_turn(raw, persona: dict) -> dict:
    """Normalise a constrained turn into ``{speech, action, tool, tool_argument}``.

    ``raw`` is the JSON string from the (constrained) backend, or a legacy prose
    reply. Cleans the action (strip self-lead, drop POV-leak second-person), maps
    OOC/empty to nulls. The schema guarantees structure; this guards content.
    """
    name = ((persona or {}).get("persona_seed") or {}).get("name") or ""
    obj = None
    if isinstance(raw, dict):
        obj = raw
    elif isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except Exception:  # noqa: BLE001 — legacy prose path (few-shot/fallback)
            obj = _parse_prose(raw)
    obj = obj or {}

    speech = _clean(obj.get("speech", ""))
    action = _clean(obj.get("action", ""))
    if action:
        action = _strip_self_lead(action, name)
        if re.match(r"^(your|you)\b", action, flags=re.I):
            action = None  # POV leak — can't render cleanly
    tool = obj.get("tool") or "none"
    tool_arg = (obj.get("tool_argument") or "").strip()

    if speech and any(m in speech.lower() for m in _OOC_MARKERS):
        speech = ""
    return {
        "speech": speech or None,
        "action": action or None,
        "tool": tool if tool in TURN_SCHEMA["properties"]["tool"]["enum"] else "none",
        "tool_argument": tool_arg,
    }


_QUOTE_RE = re.compile(r'"([^"]*)"')
_ACTION_RE = re.compile(r"\*([^*]*)\*")


def _parse_prose(raw: str) -> dict:
    """Fallback for an unconstrained/legacy prose reply (no schema)."""
    quotes = [m.strip() for m in _QUOTE_RE.findall(raw) if m.strip()]
    actions = [m.strip() for m in _ACTION_RE.findall(raw) if m.strip()]
    speech = " ".join(quotes) if quotes else _ACTION_RE.sub("", raw)
    action = " ".join(actions) if actions else (
        _QUOTE_RE.sub("", raw) if quotes else "")
    return {"speech": speech, "action": action, "tool": "none", "tool_argument": ""}


# Back-compat alias (older callers / tests).
parse_reply = parse_turn
