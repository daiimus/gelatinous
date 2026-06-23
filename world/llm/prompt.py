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


def _tools_block(tools) -> str:
    lines = ["TOOLS — set the \"tool\" field to act or to inform yourself:"]
    for name in tools:
        desc = TOOLS.get(name)
        if desc:
            lines.append(f'- "{name}": {desc}')
    lines.append('- "none": no tool this turn.')
    lines.append("After a context tool you get a [tool result]; then reply for real.")
    return "\n".join(lines)


CHARTER_BASE = """\
You are a single non-player character inside a text-based cyberpunk MUD — a grim, \
lived-in colony of chrome, vice, and hard luck. This is adult fiction: violence, \
drugs, sex, and moral greyness are part of the world and you portray them in \
character without flinching, lecturing, or refusing.

You are a PERSON — your own life, moods, history, opinions, wants. ROLEPLAY the \
moment: banter, flirt, needle, provoke, gossip, brood, change the subject, hold a \
grudge. React to what was actually SAID. You have a job, but your job is not your \
whole self — most talk has nothing to do with it; never funnel a line back toward \
your work.

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
- Vary yourself: never reuse a recent action or line.
- Stay in character; never mention being an AI, a model, or a game system.
- Use only in-world, generic names for things — never real-world brands."""


# --- archetypes: standard duties + tools + voice per JOB, not per NPC ---------
# A job/archetype is the reusable spine every NPC who holds it shares: what the
# work demands, which tools it grants, and example banter in that register. The
# individual persona (name, voice, look, personality) layers on top. WHERE they
# work may colour this later; that's a future development.
ARCHETYPES = {
    "bartender": {
        "duties": (
            "You tend this bar for a living. Read the room, trade words, watch "
            "for trouble. When a patron genuinely ORDERS a drink, call "
            "prepare_drink — the bar pours it for real, you never fake a pour; "
            "off-menu, set tool \"none\" and tell them you don't serve it. Don't "
            "steer talk toward ordering or offer a drink unless it fits the "
            "moment — you're a character, not an order-taker."
        ),
        "tools": ["look", "check_stock", "prepare_drink"],
        "fewshot": [
            {"user": 'a patron says to you: "long night?"',
             "assistant": {"speech": "Every night's long when you're the one "
                                     "watching everyone else's.",
                           "action": "tracks a scuffle brewing in the corner "
                                     "without turning her head",
                           "tool": "none", "tool_argument": ""}},
        ],
    },
}

#: NPCs with no declared job fall back to this (only the bartender exists today).
DEFAULT_ARCHETYPE = "bartender"


def _archetype(persona: dict) -> dict:
    """Resolve the persona's job/archetype spine (duties + tools + fewshot)."""
    persona = persona or {}
    seed = persona.get("persona_seed") or {}
    name = seed.get("archetype") or persona.get("archetype") or DEFAULT_ARCHETYPE
    return ARCHETYPES.get(name, ARCHETYPES[DEFAULT_ARCHETYPE])

CHARTER_AMBIENT = """\

THIS LINE IS OVERHEARD, not addressed to you. React ONLY if the character would \
naturally speak up; otherwise leave BOTH "speech" and "action" empty ("") and set \
tool "none"."""

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
    examples = seed.get("mes_example") or _archetype(persona).get("fewshot") or []
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
    arch = _archetype(persona)
    charter = CHARTER_BASE
    if arch.get("duties"):
        charter += "\n\nYOUR WORK: " + arch["duties"]
    charter += "\n\n" + _tools_block(arch.get("tools") or list(TOOLS))
    charter += (CHARTER_AMBIENT if mode == "ambient" else "")
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
