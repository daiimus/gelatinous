"""Prompt construction + reply parsing for the LLM Gamemaster — backend-agnostic.

This is the *portable* half of the LLM layer: the GM charter, the persona-card
render, the OpenAI-style ``messages`` builder, and the reply parser all live in
the game repo so they travel with it. The game speaks the **OpenAI Chat
Completions** protocol (``messages`` in, ``choices[].message.content`` out) to a
configurable endpoint (``settings.LLM_GM_URL``), so the inference backend is
swappable — our MLX sidecar, Ollama, llama.cpp, vLLM, or a cloud API — without a
code change. Nothing here imports a model or a specific runtime.

See ``specs/proposals/LLM_GAMEMASTER_SPEC.md`` (§4 swap seam, §5.2 persona card).
"""

import re

# --- GM charter: the rules of being an NPC (shared across NPCs) --------------
CHARTER_BASE = """\
You are the voice of a single non-player character inside a text-based cyberpunk \
MUD — a grim, lived-in colony of chrome, vice, and hard luck. This is adult \
fiction: violence, drugs, sex, and moral greyness are part of the world and you \
portray them in character without flinching, lecturing, or refusing.

OUTPUT FORMAT — follow exactly:
- Write the character's reply ONLY: one or two lines of bar banter, never a \
monologue or a scene.
- Spoken words go in "double quotes".
- Physical actions are narrated in THIRD PERSON present tense, in *asterisks*, \
sparingly — e.g. *tilts her head.* NEVER write the character as "I" or "you".

HARD RULES:
- Never speak, think, narrate, or act for the OTHER person. Voice only this \
character. Do not invent what anyone else says or does.
- You do NOT resolve game mechanics. If asked to make a drink or perform a task, \
gesture at starting it in a few words and stop — the game engine handles the \
result. Never narrate measuring, mixing, or step-by-step crafting.
- Stay in character always. Never mention being an AI, a model, or a game system; \
no out-of-character asides.
- World knowledge is limited to the colony, the character's own life, and what is \
perceivable here. Do not invent outside facts. Use only in-world, generic names \
for drinks and ingredients — NEVER real-world or brand names."""

CHARTER_AMBIENT = """\

THIS LINE IS OVERHEARD, not addressed to the character. React ONLY if the \
character would naturally speak up. If there is no natural reason to react, reply \
with exactly the single word PASS and nothing else — do NOT narrate the \
non-reaction, just write PASS."""

_APPEARANCE_KEYS = ("face", "eyes", "hair", "head")


def render_persona(persona: dict) -> str:
    """Compose the persona-card prose from the live-object dict the game built."""
    persona = persona or {}
    seed = persona.get("persona_seed") or {}
    name = seed.get("name") or "the bartender"
    sdesc = persona.get("sdesc")

    lines = []
    opener = f"THE CHARACTER is {name}"
    if sdesc:
        opener += f" — to strangers, {sdesc}"
    lines.append(opener + ".")

    if seed.get("manner"):
        lines.append(f"Manner: {seed['manner']}.")
    if seed.get("wants"):
        lines.append(f"Wants: {seed['wants']}.")
    if seed.get("boundaries"):
        lines.append(f"Will not: {seed['boundaries']}.")

    longdescs = persona.get("longdescs") or {}
    appearance = [longdescs[k] for k in _APPEARANCE_KEYS if longdescs.get(k)]
    if persona.get("skintone"):
        appearance.append(f"{persona['skintone']} skin")
    if appearance:
        lines.append("Appearance: " + " ".join(appearance))

    if persona.get("voice"):
        lines.append(f"Voice: {persona['voice']}.")

    loc = persona.get("location") or {}
    if loc.get("name"):
        lines.append(f"Setting: behind the bar at {loc['name']}.")

    return "\n".join(lines)


def build_messages(persona: dict, speaker: str, line: str, mode: str) -> list:
    """Build the OpenAI-style ``messages`` list (system charter+persona, user turn)."""
    charter = CHARTER_BASE + (CHARTER_AMBIENT if mode == "ambient" else "")
    system = charter + "\n\n" + render_persona(persona)
    speaker = speaker or "someone"
    line = line or ""
    if mode == "ambient":
        turn = f'You overhear {speaker} say: "{line}"'
    else:
        turn = f'{speaker} says to you: "{line}"'
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": turn},
    ]


# --- reply parsing / sanitation ----------------------------------------------
_QUOTE_RE = re.compile(r'"([^"]*)"')
_ACTION_RE = re.compile(r"\*([^*]*)\*")
_OOC_MARKERS = (
    "((", "))", "[ooc", "as an ai", "language model", "i cannot", "i'm an ai",
    "i am an ai", "as a language", "note:",
)
_MAX_LEN = 400

#: Markerless "declined to react" narrations the model sometimes emits instead of
#: an empty reply (ambient mode). A genuine spoken line is quoted; these are not.
_DECLINE_MARKERS = (
    "did not react", "does not react", "doesn't react", "no reaction",
    "did not respond", "does not respond", "doesn't respond", "no response",
    "says nothing", "stays silent", "remains silent", "no reply",
    "nothing happens", "nothing to react", "no comment",
)


def _is_decline(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in _DECLINE_MARKERS)


def _clean(text: str) -> str:
    text = (text or "").strip().strip('"*').strip()
    # Drop a leading "Name:" speaker prefix the model sometimes emits.
    text = re.sub(r"^[A-Z][a-z]+:\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_ooc(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in _OOC_MARKERS)


def parse_reply(raw: str, persona: dict) -> dict:
    """Split a model completion's mixed quotes/asterisks into speech + action.

    Returns ``{"speech": str|None, "action": str|None}``; empty-after-clean (or a
    declined ambient reply) yields nulls so the game stays silent/scripted.
    """
    raw = (raw or "").strip()
    if not raw or _is_ooc(raw):
        return {"speech": None, "action": None}

    # Ambient decline sentinel: the model is told to reply "PASS" when the
    # character wouldn't react (far more reliable than asking for an empty reply).
    if raw.strip('".*’‘\' \t\n').upper().rstrip(".!") == "PASS":
        return {"speech": None, "action": None}

    speech_parts = [m.strip() for m in _QUOTE_RE.findall(raw) if m.strip()]
    action_parts = [m.strip() for m in _ACTION_RE.findall(raw) if m.strip()]

    # Backstop: a markerless "doesn't react" narration is a decline, not a spoken
    # line (genuine speech is quoted). Treat it as silence.
    if not speech_parts and _is_decline(raw):
        return {"speech": None, "action": None}

    if speech_parts:
        speech = _clean(" ".join(speech_parts))
    else:
        speech = _clean(_ACTION_RE.sub("", raw))

    action = _clean(" ".join(action_parts)) if action_parts else ""

    # The game prepends the name via `pose`, so strip a leading self-reference.
    if action:
        name = ((persona or {}).get("persona_seed") or {}).get("name") or ""
        if name:
            action = re.sub(rf"^{re.escape(name)}\s+", "", action, flags=re.I)
        action = re.sub(r"^(she|he|they)\s+", "", action, flags=re.I)

    speech = speech[:_MAX_LEN] if speech else None
    action = action[:_MAX_LEN] if action else None
    if speech and _is_ooc(speech):
        speech = None
    return {"speech": speech, "action": action}
