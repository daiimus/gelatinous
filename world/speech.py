"""
Speech backbone shared by ``say``, ``to``, and pose/emote.

All three verbs put spoken words into a room, and all three should reach
listeners — players and NPCs alike — through one channel rather than three
near-duplicate ones. This module is that channel. It owns:

  - :func:`render_speech_line` — the per-observer attribution line for
    ``say``/``to`` (sight vs. voice attribution, hearing-gated content, voice
    flavour), so the two commands share rendering instead of copying it.
  - :func:`broadcast_speech` — the room loop ``say``/``to`` both call.
  - :func:`speech_payload` — the *structured speech payload* attached to each
    hearing listener's ``msg``, so reaction code (an NPC's ``at_msg_receive``)
    reads one shape regardless of which verb carried the words.

The payload travels as ``msg(..., speech=<words>, addressed=<bool>)``:

  - ``speech`` — the raw spoken words. Delivered only to listeners who can hear
    the speaker; a deaf listener receives no words to react to.
  - ``addressed`` — whether *this* listener was the one spoken to: ``to <them>``,
    or a pose that references them (``.nod at <them>, "..."``). Lets an NPC tell
    "ordered me a drink" from "said something in the room".

Pose/emote *rendering* stays in :mod:`world.emote`; it imports
:func:`speech_payload` so an embedded quote rides the same rails as ``say``.
"""

from __future__ import annotations

from random import random

from world.grammar import capitalize_first
from world.perception import can_hear, can_see
from world.voice import (
    VOICE_FLAVOR_SPRINKLE_CHANCE,
    garbled_voice_phrase,
    resolve_speaker_attribution,
    voice_phrase,
)


def visible_voice_flavor(speaker):
    """Voice flavour shown to observers who can SEE the speaker.

    A garbled voice always renders (a wrecked voice is conspicuous); otherwise a
    sporadic, low-frequency sprinkle, rolled once per utterance so every observer
    reads it consistently. Returns the flavour string or ``None``.
    """
    flavor = garbled_voice_phrase(speaker)
    if flavor is None:
        phrase = voice_phrase(speaker)
        if phrase and random() < VOICE_FLAVOR_SPRINKLE_CHANCE:
            flavor = phrase
    return flavor


def speech_payload(observer, speaker, words, *, addressed=False):
    """The structured speech kwargs to attach to a listener's ``msg``.

    Empty (no payload) when there are no words, the listener is the speaker, or
    the listener can't hear — a deaf NPC shouldn't react to content it never
    received. Otherwise ``{"speech": words, "addressed": bool}``.
    """
    if not words or observer is speaker:
        return {}
    if not can_hear(observer):
        return {}
    return {"speech": words, "addressed": bool(addressed)}


def render_speech_line(speaker, observer, speech, *, target=None, flavor=None,
                       verb="says"):
    """The per-observer ``say``/``to``/``whisper`` line.

    Hearing gates the *content* (the words); sight + the voice channel gate the
    *attribution* (who) — including stealth: a speaker hidden from the observer
    attributes by VOICE, not sight (world.voice). Mirrors the sight/hearing
    chain (CAPACITY_CONSUMERS §4.5). Passing ``target`` makes it a directed
    line ("... says to you/<name>, ..."); ``verb`` swaps the register
    ("whispers"). The caller is responsible for skipping observers with no
    channel at all.
    """
    heard = can_hear(observer)
    seen = can_see(observer)
    speaker_name = capitalize_first(
        resolve_speaker_attribution(speaker, observer)
    )

    target_ref = None
    if target is not None:
        target_ref = (
            "you" if observer is target else target.get_display_name(observer)
        )

    if heard:
        if target is None:
            rendered_verb = (f"{verb}, |x*{flavor}*|n"
                             if (seen and flavor) else f"{verb},")
        else:
            rendered_verb = (
                f"{verb} to {target_ref}, |x*{flavor}*|n"
                if (seen and flavor)
                else f"{verb} to {target_ref},"
            )
        return f'{speaker_name} {rendered_verb} "{speech}"'

    # Deaf but watching: the act is visible, the content is not.
    if target is None:
        return f"{speaker_name} {verb} something you can't make out."
    return (
        f"{speaker_name} {verb} something to {target_ref}, "
        f"but you can't make it out."
    )


def broadcast_speech(speaker, speech, location, *, target=None, speech_type="say"):
    """Render and broadcast a spoken line to a room.

    Shared by ``say`` (``target=None``) and ``to`` (``target=<character>``).
    Each observer gets the sight/voice-attributed, hearing-gated line plus the
    structured speech payload (for those who can hear). Observers with no
    channel at all — deaf *and* blind — are skipped entirely; the speaker is
    expected to have already received their own copy.
    """
    flavor = visible_voice_flavor(speaker)
    for observer in location.contents:
        if observer is speaker or not hasattr(observer, "msg"):
            continue
        if not can_hear(observer) and not can_see(observer):
            continue  # no channel — suppressed
        text = render_speech_line(
            speaker, observer, speech, target=target, flavor=flavor
        )
        payload = speech_payload(
            observer, speaker, speech, addressed=(observer is target)
        )
        observer.msg(text=text, type=speech_type, from_obj=speaker, **payload)
