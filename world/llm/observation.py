"""Third-party event perception for LLM NPCs (#954, combat-first slice).

LLM NPCs perceive speech and poses; everything else in a room — combat
above all — broadcasts through ``msg_room_identity``, whose perf gate
deliberately skips session-less observers (#462). That gate's design
note points here: hook the ACTION SOURCE, not the broadcast.

``observe_event`` renders ONE summary line per significant event into
each LLM-driven bystander's action buffer (the same ``[RECENTLY]``
rails poses ride): a reactor-side string append — no LLM call, no DB
write, no change to resolution or player-facing messages. Latency
shapes the design: a model turn runs far longer than a combat round,
so events are MEMORY expressed at the next social beat, never
combat-time reactions.

The best-practice contract this module keeps:

* **Deterministic layer stays authoritative** — taps are observe-only
  and exception-contained (#469 pattern: flavour never breaks combat).
* **Perceived identity** — every line renders per observer via
  ``get_display_name`` (a stranger is "a wiry man", never their key).
* **Perception-gated** — the sighted get the scene, the blind get the
  sound of it (when the event has one), the deaf-and-blind get
  nothing (five-senses rails).
* **Strict truthiness** — ``db.llm_driven is True`` (mock discipline).
"""

from __future__ import annotations


def observe_event(location, render, *, sound=None, exclude=()):
    """Buffer a perceived event for every LLM-driven observer here.

    Args:
        location: the room the event happens in.
        render (callable): ``render(observer) -> str|None`` — the line a
            SIGHTED observer buffers, rendered from their point of view.
        sound (str): what a blind-but-hearing observer gets instead
            (``None`` = the event is sight-only).
        exclude: participants who already know (the doer; a target that
            received its own personal line).
    """
    if location is None or not callable(render):
        return
    try:
        contents = list(getattr(location, "contents", None) or [])
    except Exception:  # noqa: BLE001 — a broken room observes nothing
        return
    from world.perception import can_hear, can_see
    for observer in contents:
        try:
            if observer in exclude:
                continue
            if getattr(getattr(observer, "db", None), "llm_driven",
                       None) is not True:
                continue
            buffer = getattr(observer, "_observe_action", None)
            if not callable(buffer):
                continue
            line = None
            if can_see(observer):
                line = render(observer)
            elif sound and can_hear(observer):
                line = sound
            if line:
                buffer(None, line)
        except Exception:  # noqa: BLE001 — one odd bystander never
            continue      # silences the room


# ---------------------------------------------------------------------------
# Combat event renderers — the witness-testimony altitude: who started
# it, who went down, how it ended. Never the per-swing fire-hose.
# ---------------------------------------------------------------------------

def combat_join_line(char, target=None):
    """Someone enters the fight (with their opening target if known)."""
    def render(observer):
        try:
            who = char.get_display_name(observer)
            if target is not None and target is observer:
                return f"{who} comes straight at you!"
            if target is not None:
                return (f"{who} attacks "
                        f"{target.get_display_name(observer)}!")
            return f"{who} joins the fight."
        except Exception:  # noqa: BLE001
            return None
    return render


def combat_exit_line(char, state):
    """Someone leaves the fight: 'walked' | 'unconscious' | 'dead'."""
    def render(observer):
        try:
            who = char.get_display_name(observer)
        except Exception:  # noqa: BLE001
            return None
        if state == "dead":
            return f"{who} goes down and doesn't move."
        if state == "unconscious":
            return f"{who} collapses, out cold."
        return f"{who} lowers their guard and steps back from the fight."
    return render


def personal_attack_line(attacker, target, weapon_name, hit):
    """An attack ON an LLM NPC — personal enough to buffer every swing.
    Rendered from the TARGET's point of view; call only for
    ``target.db.llm_driven is True``."""
    try:
        who = attacker.get_display_name(target)
    except Exception:  # noqa: BLE001
        return None
    verb = "hits you" if hit else "attacks you and misses"
    with_what = f" with {weapon_name}" if weapon_name else ""
    return f"{who} {verb}{with_what}!"
