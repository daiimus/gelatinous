"""Live model probe — exercise the REAL sidecar with the REAL prompt, offline.

A dev harness (not imported by the game) for validating what the local LLM
actually returns for a turn — chiefly: does it emit a well-formed first-person
dot-pose (base-form first verb, dotted later verbs, ``I .verb`` continuations,
targets by description)? That can only be answered against the live model, so
this builds the production prompt via :func:`world.llm.prompt.build_messages`,
POSTs it to the sidecar, and parses + lints the turn the way the game does.

Two modes:

* **lint** (default, HOST, stdlib only) — ``prompt.py`` imports just json/re, so
  this runs on the host with no Evennia. Inspects the raw action string::

      python3 world/llm/live_probe.py --scenario companion --n 5

* **render** (``--render``, needs Evennia → run in the throwaway container) —
  builds real character mocks, derives the handles THEY perceive each other by,
  feeds those into the prompt, then pushes the model's pose through the actual
  ``tokenize_dot_pose`` + ``render_for_observer`` and reports the **targeting
  resolution rate** (how often a referenced person resolves to a per-observer
  char ref vs. falls to literal prose)::

      docker run --rm --entrypoint bash -v "$PWD":/usr/src/game -w /usr/src/game \\
        evennia/evennia:latest -lc \\
        'LLM_PROBE_URL=http://host.docker.internal:8765/v1/chat/completions \\
         python3 world/llm/live_probe.py --scenario companion_bystander --render'
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request

from world.llm.prompt import build_messages, parse_turn, schema_for, tool_names

DEFAULT_URL = os.environ.get(
    "LLM_PROBE_URL", "http://127.0.0.1:8765/v1/chat/completions"
)

# --- representative scenarios (personas mirror the DB-seeded shape) -----------
# These are dev fixtures, not the live personas (those live in the DB, off-repo).
# Each carries string handles (lint mode) AND `chars` specs (render mode, which
# derives the handles from real mock characters so targeting can actually
# resolve). `chars.speaker.known_as` sets the NPC's remembered name for them.

SCENARIOS = {
    "bartender": {
        "persona": {
            "sdesc": "a lean woman with a catgirl mod",
            "location": {"name": "the Rotgut bar"},
            "menu": ["rotgut", "synthahol", "battery acid"],
            "persona_seed": {
                "name": "Sable",
                "archetype": "bartender",
                "manner": "dry, watchful, quick with a barb",
                "description": "Runs the Rotgut. Seen it all, says half of it.",
            },
        },
        "speaker": "a lean man",
        "line": "rough night?",
        "mode": "directed",
        "present": ["a stocky droog hunched over the dice"],
        "chars": {
            "speaker": {"sex": "male", "height": "tall", "build": "lean",
                        "sdesc_keyword": "man"},
            "present": [{"sex": "male", "height": "average", "build": "stocky",
                         "sdesc_keyword": "droog"}],
        },
    },
    "doctor": {
        "persona": {
            "sdesc": "a rangy man in a blood-flecked apron",
            "location": {"name": "a back-alley clinic"},
            "persona_seed": {
                "name": "Sawbones",
                "archetype": "doctor",
                "manner": "colony-blunt, dry, unsentimental; patches who's in "
                          "front of him, no lectures",
            },
        },
        "speaker": "a wiry courier, jaw scarred",
        "line": "took a knife to the ribs, doc. can you fix it?",
        "mode": "directed",
        "present": [],
        "chars": {
            "speaker": {"sex": "male", "height": "tall", "build": "lean",
                        "sdesc_keyword": "courier"},
            "present": [],
        },
    },
    "doctor_install": {
        "persona": {
            "sdesc": "a rangy man in a blood-flecked apron",
            "location": {"name": "a back-alley clinic"},
            "persona_seed": {
                "name": "Sawbones",
                "archetype": "doctor",
                "manner": "colony-blunt, dry; fits chrome without the sermon",
            },
        },
        "speaker": "a wiry courier, jaw scarred",
        "line": "i want a cyber arm, doc. right side. i've got the tokens.",
        "mode": "directed",
        "present": [],
        "chars": {"speaker": {"sex": "male", "height": "tall", "build": "lean",
                              "sdesc_keyword": "courier"}, "present": []},
    },
    "companion": {
        "persona": {
            "sdesc": "a slender doll in a cropped vinyl top",
            "location": {"name": "a curtained back-alley nook"},
            "persona_seed": {
                "name": "Bliss",
                "archetype": "companion",
                "manner": "warm, knowing, unhurried; meets a client where they are",
                "register": "Be vivid and physical; commit to the scene.",
            },
        },
        "speaker": "a wiry courier, jaw scarred",
        "line": "how's this work, then?",
        "mode": "directed",
        "present": [],
        "chars": {
            "speaker": {"sex": "male", "height": "tall", "build": "lean",
                        "sdesc_keyword": "courier"},
            "present": [],
        },
    },
    "companion_known": {
        "persona": {
            "sdesc": "a slender doll in a cropped vinyl top",
            "location": {"name": "a curtained back-alley nook"},
            "persona_seed": {
                "name": "Bliss",
                "archetype": "companion",
                "manner": "warm, knowing, unhurried",
                "register": "Be vivid and physical; commit to the scene.",
            },
        },
        "speaker": "Roony",
        "line": "missed you, doll.",
        "mode": "directed",
        "relationship": "you know them as 'Roony'; your read on them: a regular "
                        "you've grown fond of",
        "present": [],
        "chars": {
            "speaker": {"sex": "male", "height": "tall", "build": "lean",
                        "sdesc_keyword": "courier", "known_as": "Roony"},
            "present": [],
        },
    },
    "companion_bystander": {
        "persona": {
            "sdesc": "a slender doll in a cropped vinyl top",
            "location": {"name": "a curtained back-alley nook"},
            "persona_seed": {
                "name": "Bliss",
                "archetype": "companion",
                "manner": "warm, knowing, unhurried",
                "register": "Be vivid and physical; commit to the scene.",
            },
        },
        "speaker": "a wiry courier, jaw scarred",
        "line": "don't mind her, she's with me.",
        "mode": "directed",
        "present": ["a tall woman leaning by the doorway"],
        "chars": {
            "speaker": {"sex": "male", "height": "tall", "build": "lean",
                        "sdesc_keyword": "courier"},
            "present": [{"sex": "female", "height": "tall", "build": "athletic",
                         "sdesc_keyword": "woman"}],
        },
    },
}

# Verbs that legitimately end in -s in base form (won't be flagged as conjugated).
_BASE_S_VERBS = {"focus", "kiss", "press", "toss", "brush", "caress", "dress",
                 "pass", "miss", "cross", "address", "undress", "guess"}

#: Common base-form pose/action verbs. Used to spot an UNDOTTED continuation
#: verb — a verb opening a later clause without the leading dot the DSL needs
#: (it renders raw, e.g. "...and set it aside" instead of "...and sets it
#: aside"). Base forms only (plurals like "eyes" are nouns here, kept OUT so
#: "eyes fixed on him" isn't a false flag). Not exhaustive — tuned for recall on
#: the verbs the model actually reaches for; consistent enough to compare
#: charters against each other.
_VERB_LEXICON = frozenset({
    "lean", "wipe", "set", "take", "start", "pour", "nod", "stare", "fold",
    "cross", "glance", "tilt", "slide", "draw", "watch", "fix", "let", "raise",
    "drag", "prop", "shake", "press", "turn", "slap", "grab", "reach", "gesture", "smile", "frown", "sigh", "shrug", "lift", "drop", "push", "pull",
    "tap", "rap", "flick", "snap", "wave", "cock", "narrow", "roll", "rub",
    "scratch", "wipe", "swipe", "scan", "study", "eye", "lock",
    "settle", "fold", "cross", "plant", "lay", "place", "put", "pick",
    "hold", "grip", "clutch", "release", "loosen", "tighten", "twist", "spin",
    "step", "shift", "ease", "sink", "slump", "straighten", "stand", "crouch",
    "kneel", "perch", "settle", "swing", "duck", "dodge", "edge",
    "stride", "saunter", "amble", "pace", "circle", "lean", "tip", "dip", "bow",
    "jut", "thrust", "jab", "swat", "smack", "knock", "bang", "pound", "wipe",
    "mop", "polish", "scrub", "rinse", "splash", "tip", "slosh",
    "sip", "swig", "knock", "savor", "spark", "puff", "exhale",
    "inhale", "breathe", "spit", "swallow", "lick", "bite", "chew", "smirk",
    "grin", "scowl", "sneer", "grimace", "wince", "squint", "blink", "glare",
    "peer", "look", "regard", "consider", "weigh", "measure", "count", "check",
    "test", "feel", "trace", "brush", "stroke", "caress", "graze", "skim",
    "hook", "catch", "snag", "tug", "yank", "haul", "heave", "hoist", "toss",
    "fling", "hurl", "chuck", "lob", "roll", "deal", "slap", "slide", "push",
    "nudge", "elbow", "shoulder", "bump", "shove", "kick", "stomp", "stamp",
    "tread", "tiptoe", "creep", "slink", "prowl", "mutter", "murmur", "whisper",
    "hum", "chuckle", "laugh", "snort", "huff", "exhale", "cough", "clear",
    "jerk", "twitch", "flinch", "recoil", "stiffen", "tense", "relax", "soften",
    "harden", "set", "clench", "unclench", "curl", "uncurl", "splay", "spread",
    "flex", "ball", "fist", "open", "close", "shut", "shield", "guard",
    "wipe", "dry", "wring", "wave", "beckon", "summon", "dismiss", "shoo",
})


def score_pose(action: str) -> list[tuple[str, str]]:
    """Categorized dot-pose adherence flags for the (already normalized) action.

    Returns ``(category, detail)`` pairs; empty == clean. Scoring the
    post-``parse_turn`` action means we measure what actually RENDERS:
    ``double_conj`` — a verb fed already-conjugated, which the engine conjugates
    AGAIN ("leans" -> "leanses"); ``undotted_cont`` — a later-clause verb with no
    leading dot, which renders raw ("...and set it aside"); plus the older
    leading-token and second-person checks.
    """
    flags: list[tuple[str, str]] = []
    if not action:
        return flags
    first = action.split()[0].strip(".,").lower()
    if first in ("i", "she", "he", "they"):
        flags.append(("lead_pronoun", f"leading pronoun '{first}'"))
    elif first.endswith("ing"):
        flags.append(("lead_participle", f"first word '{first}' is a participle"))
    elif first.endswith("s") and first not in _BASE_S_VERBS:
        flags.append(("double_conj", f"leading verb '{first}' already conjugated"))
    # Dotted verbs the model conjugated -> engine doubles it.
    for m in re.finditer(r"(?<!\.)\.([a-zA-Z]+)", action):
        w = m.group(1).lower()
        if w.endswith("s") and not w.endswith("ss") and w not in _BASE_S_VERBS \
                and not w.endswith("ing"):
            flags.append(("double_conj", f"dotted verb '.{w}' already conjugated"))
    # A later clause whose first word is a verb but isn't dotted -> renders raw.
    clauses = re.split(r"[,.;:]\s+|\s+(?:and|then|as|while|but|before|after)\s+",
                       action, flags=re.I)
    for seg in clauses[1:]:
        seg = seg.strip()
        if not seg or seg.startswith(".") or seg.lower().startswith("i "):
            continue
        m = re.match(r"([a-zA-Z]+)", seg)
        if m and m.group(1).lower() in _VERB_LEXICON:
            flags.append(("undotted_cont",
                          f"continuation verb '{m.group(1).lower()}' not dotted"))
    if re.search(r"\byou\b|\byour\b", action, re.I):
        flags.append(("second_person", "second-person 'you/your' in pose"))
    return flags


def lint_action(action: str) -> list[str]:
    """Back-compat: just the human-readable details (render-mode caller)."""
    return [detail for _cat, detail in score_pose(action)]


def post(messages, schema, url, max_tokens=160):
    body = json.dumps({
        "messages": messages, "json_schema": schema, "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.load(resp)
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")


# --- render mode (Evennia) ----------------------------------------------------

def _evennia_bootstrap():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django
    django.setup()           # load the app registry (models importable)
    import evennia
    evennia._init()          # populate evennia.DefaultScript/Object/etc


def _build_scene(sc):
    """Real mock characters for the scene; handles derived from THEIR sdescs so
    the prompt and the resolver agree. Returns (npc, all_chars, stranger,
    speaker_label, present_labels)."""
    from world.tests._identity_helpers import apparent_uid_for
    from world.tests.test_emote import _make_character

    seed = sc["persona"]["persona_seed"]
    npc = _make_character(key=seed["name"], sex="female", height="short",
                          build="slight", sdesc_keyword="doll",
                          sleeve_uid="uid-npc")
    chars = sc.get("chars", {})
    sp = dict(chars.get("speaker") or {"sex": "male", "height": "tall",
                                       "build": "lean", "sdesc_keyword": "stranger"})
    known_as = sp.pop("known_as", None)
    speaker = _make_character(key="Speaker", sleeve_uid="uid-speaker", **sp)
    if known_as:
        npc.recognition_memory = {
            apparent_uid_for(speaker): {"assigned_name": known_as}}
    present_chars = [
        _make_character(key=f"Present{i}", sleeve_uid=f"uid-present-{i}", **pc)
        for i, pc in enumerate(chars.get("present", []))
    ]
    stranger = _make_character(key="Stranger", sex="male", height="average",
                               build="average", sdesc_keyword="figure",
                               sleeve_uid="uid-stranger", recognition_memory={})
    speaker_label = speaker.get_display_name(npc)
    present_labels = [c.get_display_name(npc) for c in present_chars]
    return npc, [npc, speaker] + present_chars, stranger, speaker_label, present_labels


def run(scenario_name, n, url, do_render):
    sc = SCENARIOS[scenario_name]
    persona = sc["persona"]
    npc = all_chars = stranger = None
    if do_render:
        _evennia_bootstrap()
        npc, all_chars, stranger, speaker_label, present_labels = _build_scene(sc)
    else:
        speaker_label = sc["speaker"]
        present_labels = sc.get("present")

    messages = build_messages(
        persona, speaker_label, sc["line"], sc["mode"],
        perception=f"when you look at {speaker_label} you see them plainly",
        present=present_labels, relationship=sc.get("relationship"),
    )
    schema = schema_for(persona)
    print(f"=== scenario '{scenario_name}' | mode={'render' if do_render else 'lint'}"
          f" | tools={tool_names(persona)} | {n}x @ {url} ===")
    if do_render:
        print(f"    handles: speaker={speaker_label!r} present={present_labels}")
    print()

    clean = targeted = resolved = 0
    for i in range(1, n + 1):
        try:
            raw = post(messages, schema, url)
        except Exception as e:  # noqa: BLE001 — dev tool, surface the error
            print(f"[{i}] REQUEST FAILED: {e}")
            continue
        turn = parse_turn(raw, persona, tool_names(persona))
        action = turn["action"] or ""
        flags = lint_action(action)
        if not flags:
            clean += 1
        print(f"[{i}] {'OK ' if not flags else 'FLAG'} speech: {turn['speech']!r}")
        print(f"      pose : {action!r}")
        if do_render and action:
            from world.emote import (
                CharRefToken, render_for_observer, tokenize_dot_pose)
            tokens = tokenize_dot_pose(action, npc, all_chars)
            refs = {id(t.character) for t in tokens
                    if isinstance(t, CharRefToken)}
            # Did the pose seem to aim at someone (a present/speaker keyword)?
            kws = [lbl.split()[-1].lower()
                   for lbl in [speaker_label, *present_labels] if lbl]
            aimed = any(re.search(rf"\b{re.escape(k)}\b", action, re.I)
                        for k in kws)
            if aimed:
                targeted += 1
            if refs:
                resolved += 1
            rendered = render_for_observer(tokens, npc, stranger)
            tag = "resolved" if refs else ("MISSED" if aimed else "no target")
            print(f"      render(stranger): {rendered}")
            print(f"      targeting: {tag} ({len(refs)} char-ref(s))")
        if turn["tool"] and turn["tool"] != "none":
            print(f"      tool : {turn['tool']}({turn['tool_argument']!r})")
        for f in flags:
            print(f"      ! {f}")
        print()

    print(f"=== DSL lint: {clean}/{n} clean", end="")
    if do_render:
        print(f" | targeting: {resolved}/{n} poses resolved a char-ref"
              f" ({targeted}/{n} appeared to aim at someone)", end="")
    print(" ===")


# A bank of varied DIRECTED player lines, rotated across a volume run so the
# samples exercise different poses instead of one repeated prompt. Content-
# neutral; the model's pose FORMAT (not the topic) is what we're scoring.
SCORE_LINES = [
    "rough night?", "what should I drink?", "you been here long?",
    "quiet in here tonight.", "you hear about the riot on 3rd?",
    "what do you recommend?", "long shift?", "seen anyone come through here?",
    "this place have a name?", "you always work alone?", "busy week?",
    "got anything stronger?", "what's the story with the scar?",
    "you from around here?", "looks like trouble outside.", "how's business?",
    "what's good tonight?", "you look like you've had a day.",
    "anyone else asking about me?", "mind if I sit a while?",
]


def run_score(scenario_name, n, url):
    """Volume mode: draw N poses over rotated lines and report a CATEGORIZED
    dot-pose format pass rate (the charter-refinement metric). Prints only the
    failing samples + a per-category breakdown so a 100-1000 run stays readable."""
    sc = SCENARIOS[scenario_name]
    persona = sc["persona"]
    schema = schema_for(persona)
    speaker_label = sc["speaker"]
    present_labels = sc.get("present")
    perception = f"when you look at {speaker_label} you see them plainly"

    print(f"=== score '{scenario_name}' | {n}x @ {url} ===\n")
    clean = empty = fails = 0
    by_cat: dict[str, int] = {}
    examples: list[str] = []
    for i in range(1, n + 1):
        line = SCORE_LINES[(i - 1) % len(SCORE_LINES)]
        messages = build_messages(persona, speaker_label, line, sc["mode"],
                                  perception=perception, present=present_labels,
                                  relationship=sc.get("relationship"))
        try:
            raw = post(messages, schema, url)
        except Exception as e:  # noqa: BLE001 — dev tool
            print(f"[{i}] REQUEST FAILED: {e}")
            continue
        action = parse_turn(raw, persona, tool_names(persona))["action"] or ""
        if not action:
            empty += 1
            continue
        flags = score_pose(action)
        if not flags:
            clean += 1
        else:
            fails += 1
            for cat, _detail in flags:
                by_cat[cat] = by_cat.get(cat, 0) + 1
            if len(examples) < 25:
                cats = ",".join(sorted({c for c, _ in flags}))
                examples.append(f"[{i}] ({cats}) {action!r}")
        # Streaming tally so a long run is observable (1000 samples shouldn't go
        # dark for an hour). Flush — output is piped to a file in the background.
        if i % 10 == 0 or i == n:
            done = clean + fails
            rate = f"{100*clean/done:.0f}%" if done else "—"
            print(f"  …{i}/{n}  clean={clean} fail={fails} empty={empty} "
                  f"({rate})", flush=True)

    scored = clean + fails
    print("--- failing samples ---")
    for ex in examples:
        print(ex)
    print(f"\n=== {clean}/{scored} clean "
          f"({100*clean/scored:.1f}%) | {empty} empty (no pose) ===")
    print("failures by category:")
    for cat in sorted(by_cat, key=lambda c: -by_cat[c]):
        print(f"  {cat:16} {by_cat[cat]}")


def main():
    ap = argparse.ArgumentParser(description="Probe the live LLM sidecar.")
    ap.add_argument("--scenario", default="companion", choices=list(SCENARIOS))
    ap.add_argument("--n", type=int, default=5, help="samples to draw")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--render", action="store_true",
                    help="render poses + report targeting resolution (needs Evennia)")
    ap.add_argument("--score", action="store_true",
                    help="VOLUME pose-format pass rate over rotated lines "
                         "(host, stdlib; the charter-refinement metric)")
    args = ap.parse_args()
    if args.score:
        run_score(args.scenario, args.n, args.url)
    else:
        run(args.scenario, args.n, args.url, args.render)


if __name__ == "__main__":
    main()
