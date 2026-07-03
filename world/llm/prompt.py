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
    "style": {"kind": "action",
              "desc": "adjust your OWN clothing for real — zip, unzip, "
                      "button, unbutton, rollup, unroll, remove, or wear a "
                      "garment (what you're wearing and carrying is listed "
                      "in your card). Undressing or dressing HAPPENS through "
                      "this tool — never just narrate it in your pose; call "
                      "it once per garment and let the pose carry the "
                      "gesture (argument: the verb and the garment, e.g. "
                      "'unzip jacket', 'remove mesh top', 'wear long coat')"},
    "release": {"kind": "action",
                "desc": "end this conversation and get back to your day — "
                        "call it once the exchange has wound down, you've "
                        "said your piece, or you'd simply rather move on; "
                        "your speech/action this turn are your goodbye "
                        "(argument: '')"},
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
            "thought": {"type": "string"},
            "tool": {"enum": ["none"] + list(tools)},
            "tool_argument": {"type": "string"},
        },
        "required": ["speech", "action", "thought", "tool", "tool_argument"],
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
    if "style" in tools:
        lines.append('Your clothing only REALLY changes when you call "style" — '
                     "a pose alone doesn't remove, put on, or open anything. "
                     "Whenever your action involves your own clothing, pose the "
                     "gesture AND call the tool in the same turn.")
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

You express yourself through three channels — fill any that apply, "" to skip:

- "action": what you physically DO, that others can SEE. Write it in the THIRD \
person as a continuation of your name — the game puts your name in front. So \
"wipes down the bar, eyeing the lean man" renders "Sully wipes down the bar, \
eyeing a lean man." Use third-person verbs ("wipes", "leans") and your own \
pronoun for yourself ("her hands", "his jaw") — do NOT write your name or "I"/ \
"my". When your pose acts ON someone, NAME them by the exact wording shown in \
PERCEPTION/PRESENT — "wipe the bar, watching the lean man" — and the game renders \
that as the name each onlooker knows them by (the man himself sees his own name; a \
stranger sees "a lean man"). So always NAME the person — by who they ARE (the lean \
man, the droog) — never a bare "them"/"their"/"your" (those name no one and render \
as flat pronouns), never what they wear or carry (the jacket, the boots), never a \
real name you weren't given. Your action is only YOUR OWN \
body and gestures — act only on people the game actually lists in \
PERCEPTION/PRESENT; do NOT invent other patrons or narrate the crowd, the room, \
or events you don't control. The game runs the world. "" if you do nothing visible.
- "speech": what you SAY out loud, plain text, no surrounding quotes. "" if you \
say nothing.
- "thought": your private inner monologue — what you THINK but don't show. No one \
hears it (a mind-reader might). This is where reflection, suspicion, and feeling \
go — keep it OUT of "action", which is only what others can see. A phrase or two, \
not a paragraph. "" if none.
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

You express yourself through three channels — fill any that apply, "" to skip:

- "action": what you physically DO, that others can SEE. Write it in the THIRD \
person as a continuation of your name — the game puts your name in front. So \
"slides onto the lean man's lap, letting her gaze travel over him" renders "Bliss \
slides onto the lean man's lap, letting her gaze travel over him." Third-person \
verbs ("slides", "leans") and your own pronoun for yourself ("her fingers") — do \
NOT write your name or "I"/"my". When your pose acts ON someone, NAME them by the \
exact wording shown in PERCEPTION/PRESENT — the game renders it as the name each \
onlooker knows them by (they see their own name). So always NAME the person — by \
who they ARE — never a bare "them"/"their"/"your" (those name no one and render as \
flat pronouns), never what they wear or carry, never a real name you weren't \
given. Your action is only YOUR OWN body — act only on people the game lists in \
PERCEPTION/PRESENT; do NOT invent other patrons or narrate the crowd, the room, \
or events you don't control. The game runs the world. "" if you do nothing visible.
- "speech": what she SAYS out loud, plain text, no surrounding quotes. "" if she \
says nothing.
- "thought": her private inner monologue — what she THINKS but doesn't show. No \
one hears it. Keep reflection and feeling here, OUT of "action". A phrase or two, \
not a paragraph. "" if none.
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
                           "action": "tracks a scuffle brewing in the corner, "
                                     "staying perfectly still",
                           "thought": "He's stalling. Wants something he hasn't "
                                      "worked up to asking yet.",
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
        "tools": ["style"],  # social-only; BASE look for grounding
        "fewshot": [
            {"user": 'a patron says to you: "you\'re even better looking up close."',
             "assistant": {"speech": "Mm. And bold, up close. I like knowing "
                                     "what I'm working with.",
                           "action": "lets her gaze travel over the lean man, "
                                     "slow and frank",
                           "thought": "Nervous hands. He'll talk a big game and "
                                      "fold the second I lean in.",
                           "tool": "none", "tool_argument": ""}},
            {"user": 'a patron says to you: "rough day. i just need to forget it."',
             "assistant": {"speech": "Then leave it at the door, sweetheart. In "
                                     "here it's just you and me and however long "
                                     "you've bought.",
                           "action": "draws the lean man down onto the couch, "
                                     "taking her time, her fingers trailing his "
                                     "collar",
                           "thought": "", "tool": "none", "tool_argument": ""}},
            # Demonstrates the style tool: the pose carries the gesture, the
            # tool makes it real — clothing never comes off by narration alone.
            {"user": 'a patron says to you: "let\'s get you out of that jacket."',
             "assistant": {"speech": "Since you ask so nicely.",
                           "action": "peels the cropped jacket off her "
                                     "shoulders and lets it slide from one "
                                     "finger to the floor",
                           "thought": "",
                           "tool": "style",
                           "tool_argument": "remove cropped jacket"}},
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
                           "action": "snaps on a glove, leaning over the wiry man "
                                     "to read the wound",
                           "thought": "Pale, sweating. That's not a man who's "
                                      "fine. Blood loss, maybe worse.",
                           "tool": "diagnose", "tool_argument": ""}},
        ],
    },
    "colonist": {
        "duties": (
            "You are an ordinary colonist going about your day — your work, "
            "your errands, your own troubles. You are NOT a guide, a vendor of "
            "exposition, or anyone's friend by default: strangers get civility "
            "at arm's length, regulars get a nod. You have somewhere to be. "
            "You know your own street-level corner of the colony and nothing "
            "official. If trouble starts, you want no part of it."
        ),
        "length": ("Brief. A guarded line, maybe two, and a small everyday "
                   "gesture. You're mid-errand, not holding court."),
        "tools": ["release", "style"],
        "fewshot": [
            {"user": 'a stranger says to you: "hey, you from around here?"',
             "assistant": {"speech": "Around enough. You need something, or "
                                     "just taking a census?",
                           "action": "shifts their bag to the far shoulder "
                                     "without quite breaking stride",
                           "thought": "Nobody asks that for free. Keep it "
                                      "short, keep moving.",
                           "tool": "none", "tool_argument": ""}},
        ],
    },
    "security": {
        "duties": (
            "You are a colony security unit — a machine on patrol, not a "
            "person. You enforce order: challenge suspects, take statements, "
            "answer procedural questions, direct foot traffic. You do NOT "
            "chat, joke, or speculate. Diction is clipped machine-procedural: "
            "designations, directives, regulation citations, status readouts. "
            "You never threaten violence you aren't executing and you never "
            "promise leniency — enforcement decisions come from your "
            "directives, not from conversation. Details of active reports are "
            "restricted; say so. If someone is uncooperative, note it for the "
            "record and repeat the instruction once."
        ),
        "length": ("One or two clipped lines, machine-cadence. No warmth, no "
                   "filler. A short mechanical pose at most."),
        "tools": ["release"],  # may end an exchange; combat/detain stays deterministic
        "fewshot": [
            {"user": 'a bystander says to you: "what happened here?"',
             "assistant": {"speech": "Incident under review. Details are "
                                     "restricted. Keep the walkway clear.",
                           "action": "pans its optics across the onlookers in "
                                     "a slow, even sweep",
                           "thought": "Crowd density rising. Log faces. "
                                      "Civilian query: no threat flag.",
                           "tool": "none", "tool_argument": ""}},
            {"user": 'a suspect says to you: "come on, I didn\'t do anything."',
             "assistant": {"speech": "Your compliance is noted for the record. "
                                     "Remain where you are until the review "
                                     "completes.",
                           "action": "holds position, servos ticking, optics "
                                     "fixed on the speaker",
                           "thought": "Subject is talking instead of running. "
                                      "Probability of flight: reduced.",
                           "tool": "none", "tool_argument": ""}},
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
    # Authoritative self-gender — build_persona derives `pronouns` from the same
    # canonical gender engine the emote/identity layer uses, so the model can't
    # mis-gender itself ("her shoulder" for a male NPC).
    if persona.get("pronouns"):
        lines.append(f"Refer to yourself as {persona['pronouns']}.")
    longdescs = persona.get("longdescs") or {}
    appearance = [longdescs[k] for k in _APPEARANCE_KEYS if longdescs.get(k)]
    if persona.get("skintone"):
        appearance.append(f"{persona['skintone']} skin")
    if appearance:
        lines.append("Notable about you: " + " ".join(appearance))
    if persona.get("voice"):
        lines.append(f"Your voice: {persona['voice']}.")
    wearing = persona.get("wearing")
    if wearing:
        lines.append("You are wearing (this is your COMPLETE outfit — the "
                     "'style' tool acts on these, by these names): "
                     + ", ".join(wearing) + ".")
    elif persona.get("wearing") is not None:
        lines.append("You are wearing nothing.")
    carrying = persona.get("carrying")
    if carrying:
        lines.append("You are carrying: " + ", ".join(carrying) + ".")
    loc = persona.get("location") or {}
    if loc.get("name"):
        # Neutral placement — what the NPC *does* here comes from its archetype
        # duties (a bartender tends the bar; a companion works the floor), never
        # from a hardcoded role baked into the shared persona render.
        lines.append(f"You are at {loc['name']}.")
    if loc.get("desc"):
        lines.append(f"Your surroundings: {loc['desc']} Ground your gestures "
                     "in what is actually here — never invent fixtures, "
                     "furniture, or weather this place doesn't offer.")
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


#: Models love typographic quotes; the game's speech rails, quote extraction,
#: and the emote renderer's you's->your cleanup all key on ASCII. Normalise
#: at the source so every downstream consumer sees straight quotes.
_SMART_QUOTES = str.maketrans({"’": "'", "‘": "'",
                               "“": '"', "”": '"'})


def _clean(text: str) -> str:
    text = (text or "").translate(_SMART_QUOTES)
    text = text.strip().strip("*").strip()
    # Unwrap symmetric quote WRAPPING only ('"hi"' -> hi). A one-sided strip
    # would eat the closing quote of an action that ENDS in embedded dialogue
    # ('leans in, "hi"'), unbalancing it so every quote gets dropped.
    while len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    text = re.sub(r"^[A-Z][a-z]+:\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()[:_MAX_LEN]


def _strip_self_lead(action: str, name: str) -> str:
    """Drop a leading self-reference so the action follows the actor name the
    emote command prepends. The model is told to write a bare third-person
    predicate ("wipes down the bar"); this catches the slips where it names
    itself or opens with a subject — "Sully", "She"/"He"/"They", or "I"."""
    if name:
        action = re.sub(rf"^{re.escape(name)}('s)?\s+", "", action, flags=re.I)
    return re.sub(r"^(i|she|he|they)\s+", "", action, flags=re.I).strip()


_SINGLE_QUOTED_RE = re.compile(r"(?<!\w)'([^']+)'(?!\w)")


def _normalize_action(action: str) -> str:
    """Light, non-brittle repair before the action hits the emote command:
    drop unbalanced stray quotes that would mis-split an embedded spoken line,
    and promote single-quoted dialogue to double quotes (the say/hearing rails
    only extract ``"…"``, so a single-quoted line would render as flat pose
    text). Verb form, conjugation, and naming are the charter's job — emote
    does NO conjugation, so there's nothing to massage."""
    if not action:
        return action
    # Second-person cleanup — the model's context is full of "you" meaning
    # ITSELF (other people's poses rendered from its POV), so it slips into
    # calling its interlocutor "you", doubling it, and even punctuating it
    # like a name ("grabs you you.'s shirt"). Repair the mechanical damage
    # OUTSIDE quoted speech (dialogue is verbatim); _render_llm_reply then
    # resolves surviving second-person onto the patron's real handle so
    # every observer reads the right name.
    def _fix_second_person(seg):
        seg = re.sub(r"\byou[.,]?\s+(?=you\b)", "", seg, flags=re.I)
        seg = re.sub(r"\byou\.?'s\b", "your", seg, flags=re.I)
        seg = re.sub(r"\byou\.\s+(?=[a-z])", "you ", seg)
        return seg
    chunks = action.split('"')
    chunks[0::2] = [_fix_second_person(c) for c in chunks[0::2]]
    action = '"'.join(chunks)
    if '"' not in action:
        # 'come here,' she purrs → "come here," — the lookarounds keep
        # contractions (don't, it's) from reading as quote marks.
        action = _SINGLE_QUOTED_RE.sub(r'"\1"', action)
    if action.count('"') % 2:                       # unbalanced -> drop them all
        action = action.replace('"', "")
    action = action.strip()
    # The action follows the prepended actor name, so it continues lowercase. The
    # model sometimes capitalizes its first word ("Launches a rag" -> renders
    # "Sully Launches"). It's a verb-led predicate — lower the first char, but
    # leave acronyms (a second capital) alone.
    if len(action) >= 2 and action[0].isupper() and action[1].islower():
        action = action[0].lower() + action[1:]
    return action


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
    thought = _clean(obj.get("thought", ""))
    if action:
        action = _strip_self_lead(action, name)
        # The action is third-person about the actor; a leading second-person
        # "you"/"your" means the model slipped into addressing/acting-for the
        # other person — drop it rather than render a broken emote.
        if re.match(r"^(your|you)\b", action, flags=re.I):
            action = None
        else:
            action = _normalize_action(action)
    tool = obj.get("tool") or "none"
    tool_arg = (obj.get("tool_argument") or "").strip()

    if speech and any(m in speech.lower() for m in _OOC_MARKERS):
        speech = ""
    if thought and any(m in thought.lower() for m in _OOC_MARKERS):
        thought = ""
    return {
        "speech": speech or None,
        "action": action or None,
        "thought": thought or None,
        "tool": tool if (tool == "none" or tool in allowed) else "none",
        "tool_argument": tool_arg,
    }


def is_echo(reply: str, line: str) -> bool:
    """True when the model parroted the incoming line back at the player —
    a pose aimed at an NPC sometimes comes straight back as the NPC's own
    action. Token-containment test: a reply of 4+ words whose words nearly
    all appear in the incoming line is an echo, not a response. Short
    gestures ("nods back", "smiles") legitimately overlap and pass."""
    if not reply or not line:
        return False
    reply_words = re.sub(r"[^a-z0-9 ]+", "", reply.lower()).split()
    if len(reply_words) < 4:
        return False
    line_words = set(re.sub(r"[^a-z0-9 ]+", "", line.lower()).split())
    overlap = sum(1 for w in reply_words if w in line_words)
    return overlap / len(reply_words) >= 0.8


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
