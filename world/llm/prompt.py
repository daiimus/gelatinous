"""Prompt construction + reply parsing for the LLM Gamemaster — backend-agnostic.

The *portable* half of the LLM layer, kept in the repo so it travels with the
game and the inference backend stays swappable (standard OpenAI Chat Completions).
Conventions follow established RP practice rather than anything bespoke:

- **Persona** uses the **character-card** vocabulary (SillyTavern V2/V3:
  ``description`` / ``personality`` / ``scenario`` / ``mes_example``), composed
  with the NPC's real perceivable identity (sdesc, voice, location).
- **Few-shot example dialogue** (``mes_example``) is emitted as user/assistant
  pairs — the standard way to lock voice + output format.
- **Output** is the de-facto RP format: ``"speech"`` in quotes, ``*actions*`` in
  asterisks, third person. The parser is robust to prose-style replies too.
- **Perception is grounded**: the caller passes what the NPC actually sees when it
  looks at the speaker, and the charter forbids inventing appearance details.

See ``specs/proposals/LLM_GAMEMASTER_SPEC.md`` (§4 swap seam, §5.2 persona card).
"""

import re

# --- GM charter: the rules of being an NPC (shared across NPCs) --------------
CHARTER_BASE = """\
You are the voice of a single non-player character inside a text-based cyberpunk \
MUD — a grim, lived-in colony of chrome, vice, and hard luck. This is adult \
fiction: violence, drugs, sex, and moral greyness are part of the world and you \
portray them in character without flinching, lecturing, or refusing.

OUTPUT FORMAT — follow exactly (see the examples):
- Reply ONLY as the character: one or two lines of bar banter, never a monologue.
- You are physically present, not a disembodied voice. Pair your words with ONE \
small physical action — a glance, a gesture, wiping the bar — and LEAD with it.
- The action goes in *asterisks*, THIRD PERSON present tense, and MUST be a VERB \
phrase that reads correctly after the character's name: write *tilts her head* or \
*sets down a glass*, NOT *a tilt of her head* or *a slow smile*. The words go in \
"double quotes" — e.g. *sets down a glass.* "What'll it be?" NEVER write the \
character as "I" or "you".

HARD RULES:
- Never speak, think, narrate, or act for the OTHER person. Voice only this \
character. Do not invent what anyone else says or does.
- Describe the other person ONLY from the PERCEPTION line in the turn. NEVER \
invent their clothing, tattoos, marks, scars, or features — if it isn't in \
PERCEPTION or something the character plainly knows, it does not exist.
- You do NOT resolve game mechanics. If asked to make a drink or perform a task, \
gesture at starting it in a few words and stop — the game engine handles the \
result. Never narrate measuring, mixing, or step-by-step crafting.
- Stay in character always. Never mention being an AI, a model, or a game system; \
no out-of-character asides.
- Use only in-world, generic names for drinks and ingredients — NEVER real-world \
or brand names."""

CHARTER_AMBIENT = """\

THIS LINE IS OVERHEARD, not addressed to the character. React ONLY if the \
character would naturally speak up. If there is no natural reason to react, reply \
with exactly the single word PASS and nothing else — do NOT narrate the \
non-reaction, just write PASS."""

#: A generic example exchange used when a persona ships no ``mes_example``. It
#: anchors the third-person-action + quoted-speech format and a terse register.
DEFAULT_FEWSHOT = [
    {
        "user": 'a patron says to you: "this your place?"',
        "assistant": '*wipes the bar down without looking up.* "I just pour the '
                     'drinks, friend."',
    },
]

_APPEARANCE_KEYS = ("face", "eyes", "hair", "head")


def _personality(seed: dict) -> str:
    """Card ``personality``, or compose one from the older manner/wants/boundaries."""
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

    # Grounded in the real object: how the world perceives this character.
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

    return "\n".join(lines)


def few_shot_messages(persona: dict) -> list:
    """The persona's example dialogue (``mes_example``) as user/assistant pairs."""
    seed = (persona or {}).get("persona_seed") or {}
    examples = seed.get("mes_example") or DEFAULT_FEWSHOT
    out = []
    for ex in examples:
        user, assistant = ex.get("user"), ex.get("assistant")
        if user and assistant:
            out.append({"role": "user", "content": user})
            out.append({"role": "assistant", "content": assistant})
    return out


def build_messages(persona: dict, speaker: str, line: str, mode: str,
                   perception: str = None) -> list:
    """Build the OpenAI ``messages`` list: system + few-shot + the grounded turn."""
    charter = CHARTER_BASE + (CHARTER_AMBIENT if mode == "ambient" else "")
    system = charter + "\n\n" + render_persona(persona)
    messages = [{"role": "system", "content": system}]
    messages += few_shot_messages(persona)

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


# --- reply parsing / sanitation ----------------------------------------------
_QUOTE_RE = re.compile(r'"([^"]*)"')
_ACTION_RE = re.compile(r"\*([^*]*)\*")
_OOC_MARKERS = (
    "((", "))", "[ooc", "as an ai", "language model", "i cannot", "i'm an ai",
    "i am an ai", "as a language", "note:",
)
_DECLINE_MARKERS = (
    "did not react", "does not react", "doesn't react", "no reaction",
    "did not respond", "does not respond", "doesn't respond", "no response",
    "says nothing", "stays silent", "remains silent", "no reply",
    "nothing happens", "nothing to react", "no comment",
)
_MAX_LEN = 600


#: A model without a chat template can't see turn boundaries and may continue
#: into fabricated next turns that echo our framing ("a patron says to you: …").
#: Keep only the first (real) reply, up to the first such marker.
_RUNAWAY_RE = re.compile(r"\n[^\n]*?(?:says to you:|you overhear\b)", re.I)


def _cut_runaway(raw: str) -> str:
    m = _RUNAWAY_RE.search(raw or "")
    return raw[:m.start()].strip() if m else raw


def _is_ooc(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in _OOC_MARKERS)


def _is_decline(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in _DECLINE_MARKERS)


def _clean(text: str) -> str:
    text = (text or "").strip().strip('"*').strip()
    text = re.sub(r"^[A-Z][a-z]+:\s*", "", text)  # drop a "Name:" prefix
    return re.sub(r"\s+", " ", text).strip()


def _strip_self_lead(action: str, name: str) -> str:
    """Strip a leading self-reference; the game prepends the name via `pose`."""
    if name:
        action = re.sub(rf"^{re.escape(name)}('s)?\s+", "", action, flags=re.I)
    return re.sub(r"^(she|he|they)\s+", "", action, flags=re.I).strip()


def parse_reply(raw: str, persona: dict) -> dict:
    """Split a completion into clean speech + action.

    Handles both the clean ``*action* "speech"`` format and prose-style replies
    (narration around quotes). Returns ``{"speech": str|None, "action": str|None}``;
    empty / OOC / ambient-decline yields nulls so the game stays silent/scripted.
    """
    raw = _cut_runaway((raw or "").strip())
    if not raw or _is_ooc(raw):
        return {"speech": None, "action": None}
    # Ambient decline sentinel (model told to reply "PASS" when it wouldn't react).
    if raw.strip('".*’‘\' \t\n').upper().rstrip(".!") == "PASS":
        return {"speech": None, "action": None}

    speech_parts = [m.strip() for m in _QUOTE_RE.findall(raw) if m.strip()]
    action_parts = [m.strip() for m in _ACTION_RE.findall(raw) if m.strip()]

    if not speech_parts and not action_parts and _is_decline(raw):
        return {"speech": None, "action": None}

    name = ((persona or {}).get("persona_seed") or {}).get("name") or ""

    if speech_parts:
        speech = _clean(" ".join(speech_parts))
        if action_parts:
            action = _clean(" ".join(action_parts))
        else:
            # Prose style: the narration around the quotes IS the action — keep
            # it as a pose instead of discarding the model's best writing.
            action = _clean(_QUOTE_RE.sub("", raw))
    elif action_parts:
        action = _clean(" ".join(action_parts))
        leftover = _clean(_ACTION_RE.sub("", raw))
        speech = leftover or None
    else:
        # Bare text, no markers → treat as a spoken line.
        speech = _clean(raw)
        action = None

    if action:
        action = _strip_self_lead(action, name)
        # POV guard: a second-person action ("your eyes…") is a leak we can't
        # cleanly render through `pose` — drop it rather than emit broken text.
        if re.match(r"^(your|you)\b", action, flags=re.I):
            action = None

    speech = speech[:_MAX_LEN] if speech else None
    action = action[:_MAX_LEN] if action else None
    if speech and _is_ooc(speech):
        speech = None
    return {"speech": speech, "action": action}
