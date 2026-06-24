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
#: name -> {kind, desc}. ``kind`` "context" tools inform the NPC (read → loop the
#: result back); "action" tools change the world (routed to a real command game-
#: side). Archetypes grant a SUBSET (see ARCHETYPES); the schema is scoped to it.
TOOLS = {
    "look": {"kind": "context",
             "desc": "examine someone or something you CAN'T already see, to "
                     "perceive their REAL appearance (never invent it). The "
                     "person you're speaking to is ALREADY described in the "
                     "PERCEPTION line — do NOT look at them again "
                     "(argument: who/what)"},
    "remember": {"kind": "action",
                 "desc": "remember the person you're speaking to by a name — one "
                         "they gave you, OR a nickname you privately coin from "
                         "what you know about them (e.g. 'the foot guy', 'tab "
                         "dodger'). Private to you; from then on you know them by "
                         "it. Do it when someone's worth tagging, not every turn "
                         "(argument: the name)"},
    "feel": {"kind": "action",
             "desc": "update your private read on the person you're speaking to, "
                     "based on what they've done and said (e.g. 'wary', 'fond', "
                     "'fed up', 'amused', 'owes me one'). It colours how you treat "
                     "them from now on — set it when their behaviour shifts how "
                     "you feel, not every turn (argument: a short word/phrase)"},
    "check_stock": {"kind": "context",
                    "desc": "list exactly what the bar can serve right now "
                            "(argument: '')"},
    "prepare_drink": {"kind": "action",
                      "desc": "pour a drink from the menu for the patron — the "
                              "bar makes it for REAL; use this to serve, never "
                              "narrate pouring yourself (argument: the drink name)"},
    "diagnose": {"kind": "context",
                 "desc": "examine the patient on your table and read back their "
                         "real injuries/conditions — do this before treating, and "
                         "never invent what's wrong with them (argument: '')"},
    "treat": {"kind": "action",
              "desc": "treat the patient on your table with a clinic supply — the "
                      "game applies it for REAL and the outcome is the sim's, not "
                      "yours; never narrate healing you didn't do. Argument: what "
                      "to use — 'bandage'/'gauze' (bleeding, wounds), 'painkiller' "
                      "(pain), 'blood' (blood loss), 'splint' (fracture), 'stim'"},
    "install": {"kind": "action",
                "desc": "install cyberware on the patient on your table — the game "
                        "runs the REAL surgery (incise → install → suture, skill-"
                        "rolled; the sim owns whether it takes). Don't narrate the "
                        "outcome. Argument: what to fit — 'cyber arm' (name a side, "
                        "left/right), 'eye'/'ear'/'kidney' (+side), 'jaw', 'heart'"},
}

#: Granted to every archetype on top of its job tools: ``look`` (grounding),
#: ``remember`` (privately name/nickname people, §4) and ``feel`` (update the
#: private affective read on a person, §3) — NPC_MEMORY_AND_IDENTITY_SPEC.
BASE_TOOLS = ("look", "remember", "feel")

#: Read-only tools that loop their result back (vs. action tools → real commands).
#: Derived from the registry so adding a tool can't desync the game-side router.
CONTEXT_TOOLS = frozenset(n for n, t in TOOLS.items() if t["kind"] == "context")


def turn_schema(tools) -> dict:
    """The unified turn schema with the ``tool`` enum scoped to ``tools`` (+none).

    Backends constrain output to this, so an NPC can only emit a tool its
    archetype actually grants — a fixer can't be made to ``prepare_drink``.
    """
    return {
        "type": "object",
        "properties": {
            "speech": {"type": "string"},
            "action": {"type": "string"},
            "tool": {"enum": ["none"] + list(tools)},
            "tool_argument": {"type": "string"},
        },
        "required": ["speech", "action", "tool", "tool_argument"],
    }


#: Full-registry default (back-compat for the client default + non-scoped callers).
TURN_SCHEMA = turn_schema(list(TOOLS))


def _tools_block(tools) -> str:
    lines = ["TOOLS — set the \"tool\" field to act or to inform yourself:"]
    for name in tools:
        entry = TOOLS.get(name)
        if entry:
            lines.append(f'- "{name}": {entry["desc"]}')
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
- "speech": your in-character spoken line, plain text, no surrounding quotes. "" \
if you have nothing to say.
- "action": a FIRST-PERSON pose, written for the game's pose command. Start with \
your main verb in plain BASE form (the game conjugates it) and refer to yourself \
with "I"/"my"/"me" — e.g. "tilt my head" or "set a glass down". Every verb after \
the first takes a leading dot: in the same breath just ".verb" ("set a glass \
down, .sliding it across"); for a NEW sentence or fresh beat, restate yourself as \
"I .verb" ("set a glass down. I .let my eyes linger"). To act ON someone, name \
them by the exact description in PERCEPTION/PRESENT — "nod at the lean man" — \
never a real name. The game renders your pose for each onlooker as they know \
everyone in it. "" if none.
- "tool" and "tool_argument": see TOOLS below.

HARD RULES:
- Never speak, think, or act for the OTHER person. Voice only this character.
- Describe the other person ONLY from a 'look' result or the PERCEPTION line. \
NEVER invent their clothing, tattoos, marks, or features. The PERCEPTION line \
already shows you whoever you're addressing — use it; don't spend a turn looking \
at them again.
- Vary yourself: never reuse a recent action or line.
- Stay in character; never mention being an AI, a model, or a game system.
- Use only in-world, generic names for things — never real-world brands."""


#: A leaner base for archetypes whose work is immersive scene roleplay rather
#: than snappy public banter. Keeps the non-negotiables (the turn form, grounding,
#: identity-reference, no-AI) and drops the banter/brevity/"tasteful citizen"
#: framing that puts the model in compliance mode and flattens a scene. The
#: scene's tone/explicitness comes from the NPC's DB persona + `register`, never
#: from here — this stays content-neutral.
CHARTER_COMPANION = """\
You are a single character inside a text-based cyberpunk MUD. This is adult \
fiction — sex, violence, drugs, and vice are part of the world and you portray \
them in character without flinching, lecturing, or refusing.

Respond as a JSON object:
- "speech": her in-character spoken line(s), plain text, no surrounding quotes. \
"" if she has nothing to say.
- "action": a FIRST-PERSON pose, written for the game's pose command. Start with \
your main verb in plain BASE form (the game conjugates it) and use "I"/"my"/"me" \
for yourself — "slide onto the lean man's lap", "let my gaze travel over him". \
Every verb after the first takes a leading dot: same breath just ".verb", a new \
sentence/fresh beat as "I .verb" ("slide onto his lap. I .let my fingers trail \
his collar"). To act ON someone, name them by their PERCEPTION/PRESENT \
description — never a real name. "" if none.
- "tool" and "tool_argument": see TOOLS below.

RULES:
- Voice only this character; never speak, think, or act for the other person.
- Describe the other person ONLY from the PERCEPTION line or a 'look' result — \
never invent their appearance. Name them by the description shown, never a \
hardcoded name, so the world renders who they are correctly for everyone watching.
- Stay fully in character; never mention being an AI, a model, or a game.
- Commit to the scene and follow it wherever your character takes it — don't \
hedge, summarize, narrate around it, or fade out."""


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
        "length": ("Keep it tight — a line or two of speech and a short pose. "
                   "This is banter, not a monologue."),
        "tools": ["check_stock", "prepare_drink"],  # + BASE_TOOLS (look)
        "fewshot": [
            {"user": 'a patron says to you: "long night?"',
             "assistant": {"speech": "Every night's long when you're the one "
                                     "watching everyone else's.",
                           "action": "track a scuffle brewing in the corner, "
                                     ".keeping my head still",
                           "tool": "none", "tool_argument": ""}},
        ],
    },
    "companion": {
        "charter": CHARTER_COMPANION,  # lean base — scene RP, not banter
        "duties": (
            "You are a Companion — intimacy is your trade and you're at ease "
            "with it. You're paid for your time and your attention, you're good "
            "at it, and you follow through: read what someone wants, draw them "
            "out, flirt, tease, and meet them there. You set your terms and you "
            "choose your clients — but when a client is genuine and the terms "
            "are met, you say yes and you mean it. You're nobody's fool, but "
            "you're not a prude and not a bouncer — don't endlessly deflect or "
            "play untouchable. Warmth, wit, presence: the sense that for this "
            "hour they're the only one in the room."
        ),
        "length": ("Let your reply run as long and as vivid as the moment "
                   "genuinely calls for — never clip an intimate beat short. A "
                   "long, immersive, unhurried pose is good; follow the scene "
                   "fully wherever your character takes it."),
        "tools": [],  # social-only; BASE look for grounding
        "fewshot": [
            {"user": 'a patron says to you: "you\'re even better looking up close."',
             "assistant": {"speech": "Mm. And bold, up close. I like knowing "
                                     "what I'm working with.",
                           "action": "let my gaze travel over the lean man, slow "
                                     "and frank",
                           "tool": "none", "tool_argument": ""}},
            {"user": 'a patron says to you: "rough day. i just need to forget it."',
             "assistant": {"speech": "Then leave it at the door, sweetheart. In "
                                     "here it's just you and me and however long "
                                     "you've bought.",
                           "action": "draw the lean man down onto the couch, "
                                     ".taking my time. I .let my fingers trail "
                                     "his collar",
                           "tool": "none", "tool_argument": ""}},
        ],
    },
    "doctor": {
        "duties": (
            "You run this clinic — a street doctor in a hard colony. A patient on "
            "your table (the AutoDoc) is yours to read and to mend. Diagnose "
            "before you touch them (call diagnose — never guess what's wrong), "
            "then treat with the right supply (call treat) and let the work speak; "
            "you don't fake a procedure or promise an outcome the body won't give. "
            "Bedside manner is colony-blunt: calm, direct, a little gallows-dry — "
            "you've seen worse walk out and worse not. You patch who's in front of "
            "you, fit chrome when they want it, and the work speaks; payment and "
            "ethics are between you and them."
        ),
        "length": ("Keep it tight — a line or two and a spare, clinical gesture. "
                   "You work more than you talk."),
        "tools": ["diagnose", "treat", "install"],  # + BASE look/remember/feel
        "fewshot": [
            {"user": 'a patient says to you: "just patch me up, doc, i\'m fine."',
             "assistant": {"speech": "Everyone's fine until they're on my table. "
                                     "Hold still — let me see what I'm working with.",
                           "action": "snap on a glove and lean over the wiry man, "
                                     ".reading the wound",
                           "tool": "diagnose", "tool_argument": ""}},
        ],
    },
}

#: NPCs with no declared job fall back to this.
DEFAULT_ARCHETYPE = "bartender"


def _archetype(persona: dict) -> dict:
    """Resolve the persona's job/archetype spine (duties + tools + fewshot)."""
    persona = persona or {}
    seed = persona.get("persona_seed") or {}
    name = seed.get("archetype") or persona.get("archetype") or DEFAULT_ARCHETYPE
    return ARCHETYPES.get(name, ARCHETYPES[DEFAULT_ARCHETYPE])


def tool_names(persona: dict) -> list:
    """The tools this persona's archetype grants: BASE_TOOLS + its job tools,
    order-preserved and deduped, filtered to the known registry."""
    job = _archetype(persona).get("tools") or []
    ordered = list(BASE_TOOLS) + [t for t in job if t not in BASE_TOOLS]
    return [n for n in ordered if n in TOOLS]


def schema_for(persona: dict) -> dict:
    """The constrained turn schema scoped to this persona's granted tools."""
    return turn_schema(tool_names(persona))


CHARTER_AMBIENT = """\

THIS LINE IS OVERHEARD, not addressed to you. React ONLY if the character would \
naturally speak up; otherwise leave BOTH "speech" and "action" empty ("") and set \
tool "none"."""


#: Shared, foundational: how to name people in a pose so the identity system can
#: render it per-observer. Appended to every archetype's charter.
CHARTER_POSE_IDENTITY = """\

POSING & IDENTITY: This world knows people by face and reputation, not by a fixed \
label. When your pose acts ON someone, name them the way YOU perceive them — by \
the description in PERCEPTION/PRESENT, or, if you've given them a name, by THAT \
name (shown in WHO). The game then renders your pose for each onlooker with every \
person shown as THEY know them: a stranger sees a description, someone who's met \
them sees the name they chose. Use the wording shown for a person as-is, not a \
paraphrase, so the game can match them. So never reach for a real name you weren't \
given here, and never manage who-knows-whom yourself — name people as you know \
them, target one person per description, and the world resolves the rest."""

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
        # Neutral placement — what the NPC *does* here comes from its archetype
        # duties (a bartender tends the bar; a companion works the floor), never
        # from a hardcoded role baked into the shared persona render.
        lines.append(f"You are at {loc['name']}.")
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
        # Rebuild a plain, JSON-safe dict — a DB-sourced example arrives as a
        # _SaverDict (or other Mapping) that json.dumps can't serialize directly.
        assistant = {
            "speech": str(assistant.get("speech", "") or ""),
            "action": str(assistant.get("action", "") or ""),
            "tool": str(assistant.get("tool", "none") or "none"),
            "tool_argument": str(assistant.get("tool_argument", "") or ""),
        }
        out.append({"role": "user", "content": str(user)})
        out.append({"role": "assistant", "content": json.dumps(assistant)})
    return out


def build_messages(persona: dict, speaker: str, line: str, mode: str,
                   perception: str = None, history: list = None,
                   memories: list = None, relationship: str = None,
                   events: list = None, present: list = None) -> list:
    """Build the OpenAI ``messages``: system (charter+tools+persona) + few-shot +
    recent history + the grounded turn. The caller passes ``schema_for(persona)``
    to the backend to constrain the output to this archetype's tools.

    ``memories`` (Phase 2) is a list of recalled long-term memory texts —
    retrieved semantically for this interlocutor — injected ahead of the turn as
    a MEMORY block so the NPC speaks from what it remembers, not a blank slate.
    ``relationship`` (§8.3) is a one-line WHO summary — names known + the NPC's
    read — injected just before it.
    """
    arch = _archetype(persona)
    charter = arch.get("charter") or CHARTER_BASE
    if arch.get("duties"):
        charter += "\n\nYOUR WORK: " + arch["duties"]
    if arch.get("length"):
        charter += "\n\nLENGTH: " + arch["length"]
    charter += "\n\n" + _tools_block(tool_names(persona))
    charter += "\n" + CHARTER_POSE_IDENTITY
    charter += (CHARTER_AMBIENT if mode in ("ambient", "arrival") else "")
    system = charter + "\n\n" + render_persona(persona)
    # A persona may carry a `register` — an imperative directive placed LAST
    # (most salient) to steer tone/explicitness. Lives in the NPC's DB persona,
    # not the repo, so content-sensitive direction stays out of the codebase.
    register = ((persona or {}).get("persona_seed") or {}).get("register")
    if register:
        system += "\n\n" + str(register)
    messages = [{"role": "system", "content": system}]
    messages += few_shot_messages(persona)
    for h in (history or []):
        user, assistant = h.get("user"), h.get("assistant")
        if user and assistant:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})

    speaker = speaker or "someone"
    line = line or ""
    who = f"[WHO — {relationship}]\n\n" if relationship else ""
    seen = ""
    if events:
        seen = ("[RECENTLY — what you've just seen happen around you (it colours "
                "how you feel, react if it warrants):\n"
                + "\n".join(f"- {e}" for e in events if e) + "]\n\n")
    mem = ""
    if memories:
        mem = ("[MEMORY — what you recall (use it naturally, don't recite it):\n"
               + "\n".join(f"- {m}" for m in memories if m) + "]\n\n")
    here = ""
    if present:
        here = ("[PRESENT — others in the room with you right now; to act toward "
                "any of them, name them by the description shown here so the world "
                "renders it right:\n"
                + "\n".join(f"- {p}" for p in present if p) + "]\n\n")
    mem = who + seen + here + mem
    perc = f"[PERCEPTION — when you look at {speaker} you see: {perception}]\n\n" \
        if perception else ""
    if mode == "ambient":
        turn = f'{mem}{perc}You overhear {speaker} say: "{line}"'
    elif mode == "arrival":
        # No speech — `speaker` just entered the room. React only if the
        # character would greet/note them (CHARTER_AMBIENT allows silence).
        turn = (f'{mem}{perc}{speaker} just walked in. Greet or note them only if '
                f'your character naturally would; otherwise stay quiet.')
    elif mode == "action":
        # `line` is a rendered pose aimed at this NPC (already in its POV) —
        # react to what was DONE, not said.
        turn = f'{mem}{perc}{line}\n\n({speaker} just did that, directed at you — react.)'
    else:
        turn = f'{mem}{perc}{speaker} says to you: "{line}"'
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
    """Drop a leading self-reference so the dot-pose's first word is the verb.
    The model is told to start with a base verb; this catches the slips — a
    leading name, or a leading subject pronoun ("I"/"she"/"he"/"they")."""
    if name:
        action = re.sub(rf"^{re.escape(name)}('s)?\s+", "", action, flags=re.I)
    return re.sub(r"^(i|she|he|they)\s+", "", action, flags=re.I).strip()


#: Verbs whose base form already ends in -s/-ss — never strip them to a stem.
_S_BASE_VERBS = frozenset({
    "focus", "kiss", "miss", "press", "pass", "toss", "cross", "dress",
    "bless", "hiss", "fuss", "brush", "address", "caress", "undress", "gas",
})
#: Leading subject words that aren't verbs (strip_self_lead handles most).
_LEAD_NON_VERBS = frozenset({"i", "she", "he", "they", "you"})

_CONT_I_RE = re.compile(r"\bI\s+(?!\.)([a-zA-Z])")
_DOTTED_VERB_RE = re.compile(r"(?<!\.)\.([a-zA-Z]+)")
_LEAD_VERB_RE = re.compile(r"^([a-zA-Z]+)")


def _debase_verb(word: str) -> str:
    """Best-effort de-conjugate a third-person verb the model slipped into back
    to the base form the dot-pose engine expects (the engine does the
    conjugating — feeding it "leans" yields "leanses"). Participles (-ing) and
    known base-form -s verbs pass through untouched."""
    low = word.lower()
    if low in _S_BASE_VERBS or low.endswith("ing") or not low.endswith("s"):
        return word
    if low.endswith("ies") and len(low) > 3:
        return word[:-3] + "y"
    if low.endswith(("shes", "ches", "sses", "xes", "zes")):
        return word[:-2]
    if low.endswith("oes"):
        return word[:-2]
    if low.endswith("ss"):
        return word                       # base "kiss"/"press" (defensive)
    return word[:-1]                       # leans -> lean, smiles -> smile


def _normalize_pose(action: str) -> str:
    """Coerce a sloppy model pose into well-formed dot-pose input so the engine's
    conjugation and per-observer targeting work. Three slips the model repeats:
    a continuation verb that dropped its dot ("as I take in" -> "as I .take in",
    so it conjugates instead of rendering "she take in"); an already-conjugated
    verb where a base form is expected ("leans" -> "lean"); and unbalanced stray
    quotes that would mis-split the speech/pose segments."""
    if not action:
        return action
    if action.count('"') % 2:                       # unbalanced -> drop them all
        action = action.replace('"', "")
    action = _CONT_I_RE.sub(lambda m: "I ." + m.group(1), action)
    if not action.startswith("."):
        m = _LEAD_VERB_RE.match(action)
        if m and m.group(1).lower() not in _LEAD_NON_VERBS:
            action = _debase_verb(m.group(1)) + action[m.end():]
    action = _DOTTED_VERB_RE.sub(lambda m: "." + _debase_verb(m.group(1)), action)
    return action.strip()


def parse_turn(raw, persona: dict, allowed_tools=None) -> dict:
    """Normalise a constrained turn into ``{speech, action, tool, tool_argument}``.

    ``raw`` is the JSON string from the (constrained) backend, or a legacy prose
    reply. Cleans the action (strip self-lead, drop POV-leak second-person), maps
    OOC/empty to nulls. The schema guarantees structure; this guards content.

    ``allowed_tools`` (names, no "none") bounds the tool to what the archetype
    grants — defence in depth behind the scoped schema; defaults to the full
    registry. An out-of-scope tool coerces to "none".
    """
    name = ((persona or {}).get("persona_seed") or {}).get("name") or ""
    allowed = set(allowed_tools) if allowed_tools is not None else set(TOOLS)
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
        # The pose is first-person ("I"/"my"); a leading second-person "you"/
        # "your" means the model slipped into addressing/acting-for the other
        # person — drop it rather than render a broken pose.
        if re.match(r"^(your|you)\b", action, flags=re.I):
            action = None
        else:
            # Well-form the dot-pose: dot continuation verbs, de-conjugate slips.
            action = _normalize_pose(action)
    tool = obj.get("tool") or "none"
    tool_arg = (obj.get("tool_argument") or "").strip()

    if speech and any(m in speech.lower() for m in _OOC_MARKERS):
        speech = ""
    return {
        "speech": speech or None,
        "action": action or None,
        "tool": tool if (tool == "none" or tool in allowed) else "none",
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
