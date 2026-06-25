"""NPC console — drive an LLM NPC through the REAL player pipeline, no human.

A standing problem testing LLM NPCs: the only way to see what a *player* sees
was to BE the player — type at the live game and read the result. This harness
removes the human from the loop. It stands up an ephemeral scene (a room, a real
LLM NPC of the chosen archetype, and a puppet PC with a real identity), then for
each scripted line it makes the puppet **actually `say`** it through the real
command pipeline — so the NPC's `at_msg_receive` → classify → persona build →
sidecar → `parse_turn` → `_render_llm_reply` → `.pose` all run exactly as in
game — and prints what the puppet PC *receives back*. That is the player
experience, reproduced.

The reactor is not running here, so the two async seams are run INLINE:
`run_async` (the sidecar call) executes in-thread and fires its callback at once,
and `delay(...)` runs immediately. Everything else is the untouched game code.

This is an OBSERVATION tool (the model is non-deterministic) — it shows real
rendered output to eyeball format/targeting/voice after a prompt or render
change. The deterministic assertions live in world/tests/. Not imported by the
game.

Run (throwaway container, reaches the host sidecar via host.docker.internal):

    docker run --rm --entrypoint bash -v "$PWD":/usr/src/game -w /usr/src/game \
      evennia/evennia:latest -lc 'evennia migrate --settings settings.py \
      >/tmp/m.log 2>&1; PYTHONPATH=/usr/src/game LLM_GM_MODEL=cydonia-24b-v3.1 \
      python world/llm/npc_console.py --archetype bartender --raw \
      --say "rough night?" --say "what do you recommend I drink?"'

    # interactive: drop --say and pass --repl, then type lines (Ctrl-D to end).

REACTIVE puppeting (roleplay AGAINST the sidecar NPC, turn by turn): pass --state
<file> and ONE --say per call; the NPC's conversation + memory persist to <file>
across the throwaway-DB invocations, so it remembers between your turns. Read its
reply, craft the next line off it, call again. --as-name / --as-keyword choose who
you play (so the NPC perceives you as e.g. a "fixer" named "Vince"):

    ...python world/llm/npc_console.py --raw --state /usr/src/game/.rp_state.json \
      --as-name "Vince" --as-keyword "fixer" --say "<your next line>"'

The state file lands in the mounted repo dir (gitignored). Delete it to start fresh.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


# --------------------------------------------------------------------------
# Bootstrap (mirrors live_probe): app registry, then evennia internals.
# --------------------------------------------------------------------------
def bootstrap():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django
    django.setup()
    import evennia
    evennia._init()


# --------------------------------------------------------------------------
# Collapse the two async seams so the whole pipeline completes in-call.
# --------------------------------------------------------------------------
def make_synchronous():
    """Patch `run_async` (sidecar call) and `delay` (scheduling) to run inline,
    so a single `say` drives the NPC's reply to completion before we return."""
    from twisted.python.failure import Failure

    def inline_run_async(func, at_return=None, at_err=None, **kwargs):
        try:
            result = func()
        except Exception:  # noqa: BLE001 — mirror the reactor's at_err path
            if at_err:
                at_err(Failure())
            return
        if at_return:
            at_return(result)

    def inline_delay(_seconds, func, *args, **kwargs):
        return func(*args, **kwargs)

    import world.llm.client as client
    import typeclasses.llm_npc as llm_npc
    import typeclasses.bar as bar
    client.run_async = inline_run_async
    llm_npc.delay = inline_delay
    bar.delay = inline_delay


def enable_llm(model, url, timeout):
    """Flip the deployment gate on and point at the sidecar for this process."""
    from django.conf import settings
    settings.LLM_GM_ENABLED = True
    # A bare `migrate` db has no Limbo (#2); without this create_object fails
    # looking up the (nonexistent) DEFAULT_HOME. Ephemeral scene needs no home.
    settings.DEFAULT_HOME = None
    if url:
        settings.LLM_GM_URL = url
    if model:
        settings.LLM_GM_MODEL = model
    if timeout:
        settings.LLM_GM_TIMEOUT = timeout


# --------------------------------------------------------------------------
# Surface what the MODEL produced vs what got RENDERED (the debugging view).
# --------------------------------------------------------------------------
_LAST = {}


def trace_parse():
    """Wrap parse_turn so each turn records the raw model reply and the parsed
    (normalized) speech/action — the before/after that explains a render."""
    import typeclasses.llm_npc as llm_npc
    real = llm_npc.parse_turn

    def traced(raw, persona, allowed=None):
        result = real(raw, persona, allowed)
        _LAST["raw"] = raw
        _LAST["parsed"] = dict(result)
        return result

    llm_npc.parse_turn = traced


# --------------------------------------------------------------------------
# Scene: a room, an LLM NPC of the archetype, a puppet PC that captures msgs.
# --------------------------------------------------------------------------
DEFAULT_PERSONAS = {
    "bartender": {
        "archetype": "bartender",
        "name": "Sully",
        "manner": "dry, watchful, unhurried; talks like every word costs a token",
        "wants": "a quiet shift and no broken glass",
        "boundaries": "won't be pushed around; cuts off anyone spoiling for trouble",
    },
    "doctor": {
        "archetype": "doctor",
        "name": "Nikolai Kasparov",
        "manner": "colony-blunt, gallows-dry, economical",
        "wants": "to patch who's in front of him and move on",
        "boundaries": "no promises the body won't keep",
    },
    "companion": {
        "archetype": "companion",
        "name": "Vesper",
        "manner": "warm, unhurried, frankly attentive",
        "wants": "to make the hour feel like it's only the two of you",
        "boundaries": "sets her own terms; nobody's fool",
    },
}

# Which NPC typeclass hosts each archetype.
ARCHETYPE_TYPECLASS = {
    "bartender": "typeclasses.bar.Bartender",
    "doctor": "typeclasses.clinic.Doctor",
    "companion": "typeclasses.llm_npc.LLMNpc",
}


def build_scene(archetype, persona_seed, with_bar=True):
    from evennia import create_object

    transcript = []

    room = create_object("typeclasses.rooms.Room", key="probe room")
    typeclass = ARCHETYPE_TYPECLASS.get(archetype, "typeclasses.llm_npc.LLMNpc")
    npc = create_object(typeclass, key=persona_seed["name"], location=room)
    npc.db.llm_driven = True
    npc.db.llm_persona = persona_seed
    # Give the NPC a real presentation so it renders as a person, not its key.
    npc.height, npc.build, npc.sex = "tall", "lean", "male"
    # Stable identity UID so recognition/memory keying survives a fresh-DB rebuild
    # across `--state` session turns (apparent_uid derives from the sleeve).
    npc.sleeve_uid = "harness-npc"
    if archetype == "bartender" and with_bar:
        bar = create_object("typeclasses.bar.BarCounter",
                            key="the hull-slab bar", location=room)
        bar.db.menu = [
            {"name": "rotgut", "price": 0, "craft": "fixes a rotgut"},
            {"name": "black recyc", "price": 0, "craft": "pours a black recyc"},
        ]

    puppet = create_object("typeclasses.characters.Character",
                           key="Laszlo", location=room)
    puppet.height, puppet.build, puppet.sex = "above-average", "stocky", "male"
    puppet.sdesc_keyword = "droog"
    puppet.sleeve_uid = "harness-puppet"   # stable, for cross-turn recognition
    # Builder perm so the harness PERCEIVES the NPC's `think` output (v1 gate),
    # letting us watch its interiority alongside the visible emote.
    puppet.permissions.add("Builder")

    # Capture everything the PUPPET receives — that is the player's screen.
    def capture(*args, **kwargs):
        text = kwargs.get("text", args[0] if args else "")
        if isinstance(text, (tuple, list)):
            text = text[0]
        if text:
            transcript.append(str(text))

    puppet.msg = capture
    return room, npc, puppet, transcript


# --------------------------------------------------------------------------
# Session persistence — carry the NPC's memory across throwaway-DB invocations
# so I can puppet REACTIVELY: send a line, read the reply, craft the next, and
# the NPC remembers the conversation between my turns. (ndb/db are wiped with
# the container; we serialise the bits that make a conversation continuous.)
# --------------------------------------------------------------------------
def restore_state(npc, puppet, path):
    if not path or not os.path.exists(path):
        return
    with open(path) as fh:
        state = json.load(fh)
    if state.get("history"):
        npc.ndb.llm_history = {npc._hist_key(puppet): state["history"]}
    if state.get("recognition"):
        npc.recognition_memory = state["recognition"]
    if state.get("memories"):
        npc.db.llm_memories = state["memories"]


def save_state(npc, puppet, path):
    if not path:
        return
    from evennia.utils.dbserialize import deserialize   # _Saver* -> plain py
    state = deserialize({
        "history": (npc.ndb.llm_history or {}).get(npc._hist_key(puppet), []),
        "recognition": npc.recognition_memory or {},
        "memories": npc.db.llm_memories or [],
    })
    with open(path, "w") as fh:
        json.dump(state, fh)


# --------------------------------------------------------------------------
# One exchange: the puppet really `say`s the line; we print what comes back.
# --------------------------------------------------------------------------
def exchange(npc, puppet, line, show_raw):
    print(f"\n\033[1m> say {line}\033[0m")
    npc.ndb.last_llm = 0          # clear the directed cooldown between lines
    _LAST.clear()
    puppet.execute_cmd(f"say {line}")
    if show_raw and _LAST:
        raw = _LAST.get("raw")
        parsed = _LAST.get("parsed", {})
        print(f"  \033[2mmodel.raw   : {raw!r}\033[0m")
        print(f"  \033[2mnormalized  : speech={parsed.get('speech')!r} "
              f"action={parsed.get('action')!r} "
              f"thought={parsed.get('thought')!r}\033[0m")


def drain(transcript):
    for line in transcript:
        print(f"  {line}")
    transcript.clear()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archetype", default="bartender",
                    choices=sorted(ARCHETYPE_TYPECLASS))
    ap.add_argument("--persona", help="JSON persona-seed override")
    ap.add_argument("--say", action="append", default=[],
                    help="a player line (repeatable)")
    ap.add_argument("--repeat", type=int, default=1,
                    help="run each --say line N times (surface intermittent slips)")
    ap.add_argument("--repl", action="store_true",
                    help="interactive: read lines from stdin")
    ap.add_argument("--raw", action="store_true",
                    help="also show the raw model reply + normalized action")
    ap.add_argument("--model", default=os.environ.get("LLM_GM_MODEL", ""))
    ap.add_argument("--url", default=os.environ.get("LLM_GM_URL", ""))
    ap.add_argument("--timeout", type=int, default=0)
    ap.add_argument("--state", help="persist/restore the NPC's conversation + "
                    "memory to this file, so REACTIVE turn-by-turn play (one "
                    "--say per call) continues across invocations")
    ap.add_argument("--as-name", help="the puppet's display name (who I play)")
    ap.add_argument("--as-keyword",
                    help="the puppet's sdesc keyword (e.g. 'medic', 'courier')")
    args = ap.parse_args()

    bootstrap()
    make_synchronous()
    trace_parse()
    enable_llm(args.model, args.url, args.timeout)

    seed = dict(DEFAULT_PERSONAS.get(args.archetype, DEFAULT_PERSONAS["bartender"]))
    if args.persona:
        seed.update(json.loads(args.persona))
    seed.setdefault("archetype", args.archetype)

    room, npc, puppet, transcript = build_scene(args.archetype, seed)
    if args.as_name:
        puppet.key = args.as_name
    if args.as_keyword:
        puppet.sdesc_keyword = args.as_keyword
    restore_state(npc, puppet, args.state)
    turns = len((npc.ndb.llm_history or {}).get(npc._hist_key(puppet), []))
    print(f"scene: {npc.key} ({args.archetype}) and {puppet.key} in {room.key}"
          + (f"  [resumed, {turns} prior turns]" if turns else ""))

    try:
        for line in args.say:
            for _ in range(max(1, args.repeat)):
                exchange(npc, puppet, line, args.raw)
                drain(transcript)
        if args.repl or not args.say:
            print("\n[repl] type a line (Ctrl-D to quit):")
            for raw in sys.stdin:
                line = raw.strip()
                if not line:
                    continue
                exchange(npc, puppet, line, args.raw)
                drain(transcript)
    finally:
        save_state(npc, puppet, args.state)   # persist before tearing down
        # Ephemeral scene — leave no objects behind (matters if ever run on a
        # real db; harmless in the throwaway).
        for obj in (puppet, npc, room):
            try:
                obj.delete()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    main()
