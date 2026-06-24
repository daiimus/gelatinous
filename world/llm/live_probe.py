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


def lint_action(action: str) -> list[str]:
    """Heuristic flags for dot-pose DSL adherence. Empty list == looks clean."""
    flags = []
    if not action:
        return flags
    words = action.split()
    first = words[0].strip(".,").lower()
    if first in ("i", "she", "he", "they"):
        flags.append(f"leading pronoun '{first}' (parse_turn strips it)")
    elif first.endswith("ing"):
        flags.append(f"first word '{first}' is a participle, not a base verb")
    elif first.endswith("s") and first not in _BASE_S_VERBS:
        flags.append(f"first word '{first}' looks conjugated (want base form)")
    if re.search(r"\byou\b|\byour\b", action, re.I):
        flags.append("second-person 'you/your' in pose (should be 3rd-person/sdesc)")
    return flags


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


def main():
    ap = argparse.ArgumentParser(description="Probe the live LLM sidecar.")
    ap.add_argument("--scenario", default="companion", choices=list(SCENARIOS))
    ap.add_argument("--n", type=int, default=5, help="samples to draw")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--render", action="store_true",
                    help="render poses + report targeting resolution (needs Evennia)")
    args = ap.parse_args()
    run(args.scenario, args.n, args.url, args.render)


if __name__ == "__main__":
    main()
