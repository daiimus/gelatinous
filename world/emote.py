"""
Dot-Pose Emote Engine

Tokenizer and per-observer renderer for the first-person dot-pose system.
Converts first-person natural writing into per-observer third-person messages.

Example::

    Player types:    .lean back and .sigh. "What a day," I .mutter.
    Actor sees:      You lean back and sigh. "What a day," you mutter.
    Observer (known): Jorge leans back and sighs. "What a day," he mutters.
    Observer (sdesc): A lanky man leans back and sighs. "What a day," he mutters.

The engine has no side effects and depends only on ``world.grammar`` for
conjugation/pronoun tables.  Room broadcasting is handled by
:func:`render_dot_pose`, which calls ``observer.msg()`` on each room
occupant.

See specs/EMOTE_POSE_SPEC.md for the full specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from world.grammar import (
    GENDER_MAP,
    capitalize_first,
    conjugate_third_person,
    transform_pronoun,
)

if TYPE_CHECKING:
    from typeclasses.characters import Character


# =========================================================================
# Token Dataclasses
# =========================================================================


@dataclass
class TextToken:
    """Literal text passed through unchanged."""

    text: str


@dataclass
class VerbToken:
    """A marked verb requiring conjugation."""

    base_form: str


@dataclass
class PronounToken:
    """A first-person pronoun requiring perspective transformation."""

    original: str
    case: str  # "subject", "object", "possessive_adj", "possessive_pro", "reflexive"


@dataclass
class SpeechToken:
    """Quoted speech content, preserved as structured data."""

    text: str
    speaker: "Character"
    language: str | None = None


@dataclass
class CharRefToken:
    """Reference to another character, resolved per-observer."""

    character: "Character"
    original_text: str


# =========================================================================
# Speech Processing Hook
# =========================================================================


def process_speech(
    text: str,
    speaker: "Character",
    observer: "Character",
    language: str | None = None,
) -> str:
    """Process speech content for a specific observer.

    Default implementation returns text unchanged, wrapped in quotes.
    Future language system overrides this to apply comprehension
    filtering based on speaker's language and observer's skills.

    Args:
        text: Raw speech content.
        speaker: Character speaking.
        observer: Character hearing.
        language: Language identifier or ``None`` for common/default.

    Returns:
        Rendered speech string including quotes.
    """
    return f'"{text}"'


# =========================================================================
# Pronoun Detection
# =========================================================================

#: Maps lowercase first-person pronouns to their grammatical case.
_PRONOUN_CASE_MAP: dict[str, str] = {
    "i": "subject",
    "me": "object",
    "my": "possessive_adj",
    "mine": "possessive_pro",
    "myself": "reflexive",
}

#: Regex pattern for first-person pronouns at word boundaries.
#: ``I`` is only matched when uppercase (standalone capital I).
#: Other pronouns are case-insensitive.
_PRONOUN_PATTERN = re.compile(
    r"\b(?:I|[Mm][Ee]|[Mm][Yy]|[Mm][Ii][Nn][Ee]|[Mm][Yy][Ss][Ee][Ll][Ff])\b"
)


# =========================================================================
# -ing Participle Detection
# =========================================================================

#: Verbs whose base form ends in -ing but are NOT participles.
#: These should be conjugated normally (bring → brings, sing → sings).
_ING_BASE_VERBS: frozenset[str] = frozenset({
    "bring",
    "cling",
    "fling",
    "king",
    "ping",
    "ring",
    "sing",
    "sling",
    "spring",
    "sting",
    "string",
    "swing",
    "thing",
    "wing",
    "wring",
    "zing",
})


def _should_conjugate(verb: str) -> bool:
    """Determine whether a verb should be conjugated.

    Participles (words ending in -ing that are NOT real base verbs
    like "bring" or "sing") pass through unconjugated.

    Args:
        verb: The base form of the verb.

    Returns:
        ``True`` if the verb should be conjugated, ``False`` if it
        should pass through as-is (e.g. participles like "diving").
    """
    lower = verb.lower()
    if lower.endswith("ing") and lower not in _ING_BASE_VERBS:
        return False
    return True


# =========================================================================
# Verb Marker Regex
# =========================================================================

#: Matches ``.word`` verb markers: a dot followed immediately by a letter,
#: then word characters.  Negative lookbehind prevents matching ``..word``
#: (ellipsis + word).
_VERB_MARKER_PATTERN = re.compile(r"(?<!\.)\.([a-zA-Z]\w*)")


# =========================================================================
# Tokenizer Internals
# =========================================================================


def _split_speech_segments(text: str) -> list[tuple[str, bool]]:
    """Split text into alternating non-speech / speech segments.

    Speech is delimited by double quotes (``"..."``).  Unmatched
    opening quotes treat the rest of the string as speech.

    Args:
        text: Raw input text.

    Returns:
        List of ``(segment_text, is_speech)`` tuples.
    """
    segments: list[tuple[str, bool]] = []
    pos = 0
    while pos < len(text):
        # Find next opening quote
        quote_start = text.find('"', pos)
        if quote_start == -1:
            # No more quotes — rest is non-speech
            remainder = text[pos:]
            if remainder:
                segments.append((remainder, False))
            break

        # Non-speech before the quote
        if quote_start > pos:
            segments.append((text[pos:quote_start], False))

        # Find closing quote
        quote_end = text.find('"', quote_start + 1)
        if quote_end == -1:
            # Unmatched quote — rest is speech
            speech_content = text[quote_start + 1:]
            segments.append((speech_content, True))
            break
        else:
            speech_content = text[quote_start + 1:quote_end]
            segments.append((speech_content, True))
            pos = quote_end + 1
    return segments


def _spans_overlap(
    start: int, end: int, existing: list[tuple[int, int]]
) -> bool:
    """Check whether a span overlaps any existing span.

    Args:
        start: Start index (inclusive).
        end: End index (exclusive).
        existing: List of ``(start, end)`` spans already claimed.

    Returns:
        ``True`` if any overlap is found.
    """
    for es, ee in existing:
        if start < ee and end > es:
            return True
    return False


def build_char_candidates(
    actor: "Character",
    room_occupants: list["Character"],
) -> list[tuple[str, "Character"]]:
    """Build sorted (name, character) pairs for character reference matching.

    For each room occupant (excluding the actor), collects possible
    name strings the actor might use to reference them, sorted by
    string length descending (longest match first).

    Args:
        actor: The character performing the emote.
        room_occupants: All characters in the room.

    Returns:
        List of ``(name_string, character)`` pairs, sorted longest
        first.
    """
    from world.grammar import DEFAULT_SDESC_KEYWORDS, get_article
    from world.identity import compose_sdesc, get_physical_descriptor
    from world.search import strip_leading_article

    candidates: list[tuple[str, "Character"]] = []

    for char in room_occupants:
        if char is actor:
            continue

        names: list[str] = []

        # 1. Display name as seen by actor (assigned name or sdesc with article)
        display_name = char.get_display_name(actor)
        if display_name:
            names.append(display_name)
            # 2. Article-stripped version
            stripped = strip_leading_article(display_name)
            if stripped != display_name:
                names.append(stripped)

        # 3. Raw sdesc (no article)
        sdesc = char.get_sdesc()
        if sdesc and sdesc != char.key:
            if sdesc not in names:
                names.append(sdesc)

        # 4. Descriptor + keyword only (no feature clause)
        height = getattr(char, "height", None)
        build = getattr(char, "build", None)
        if height and build:
            try:
                descriptor = get_physical_descriptor(height, build)
                keyword = getattr(char, "sdesc_keyword", None)
                if not keyword:
                    keyword = DEFAULT_SDESC_KEYWORDS.get(
                        getattr(char, "gender", "neutral"), "person"
                    )
                short_sdesc = compose_sdesc(descriptor, keyword)
                if short_sdesc not in names:
                    names.append(short_sdesc)
            except (KeyError, AttributeError):
                pass

        # 5. Keyword only
        keyword = getattr(char, "sdesc_keyword", None)
        if not keyword:
            keyword = DEFAULT_SDESC_KEYWORDS.get(
                getattr(char, "gender", "neutral"), "person"
            )
        if keyword and keyword not in names:
            names.append(keyword)

        # 6. Character .key — Builder+ only (check actor's permissions)
        # For the emote engine, we include .key if the actor has Builder+
        # permissions.  Normal players don't get .key access.
        if hasattr(actor, "locks"):
            try:
                if actor.locks.check_lockstring(
                    actor, "perm(Builder)"
                ):
                    if char.key not in names:
                        names.append(char.key)
            except Exception:
                pass

        for name in names:
            candidates.append((name, char))

    # Sort by length descending so longest match wins
    candidates.sort(key=lambda pair: len(pair[0]), reverse=True)
    return candidates


def _find_char_ref_spans(
    text: str,
    candidates: list[tuple[str, "Character"]],
    claimed_spans: list[tuple[int, int]],
) -> list[tuple[int, int, "Character", str]]:
    """Find character reference matches in text.

    Scans text for case-insensitive word-boundary matches against
    candidate names.  Skips spans already claimed by verb markers.

    Args:
        text: The non-speech text segment.
        candidates: Sorted ``(name, character)`` pairs from
            :func:`build_char_candidates`.
        claimed_spans: Spans already claimed (verb markers, etc.).

    Returns:
        List of ``(start, end, character, matched_text)`` tuples.
    """
    refs: list[tuple[int, int, "Character", str]] = []
    ref_spans: list[tuple[int, int]] = list(claimed_spans)

    for name, char in candidates:
        # Build word-boundary pattern for this name
        pattern = re.compile(
            r"\b" + re.escape(name) + r"\b", re.IGNORECASE
        )
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            if not _spans_overlap(start, end, ref_spans):
                refs.append((start, end, char, match.group()))
                ref_spans.append((start, end))

    return refs


def _find_pronoun_spans(
    text: str,
    claimed_spans: list[tuple[int, int]],
) -> list[tuple[int, int, str, str]]:
    """Find first-person pronoun matches in text.

    Args:
        text: The non-speech text segment.
        claimed_spans: Spans already claimed by verbs and char refs.

    Returns:
        List of ``(start, end, pronoun_lower, case)`` tuples.
    """
    pronouns: list[tuple[int, int, str, str]] = []

    for match in _PRONOUN_PATTERN.finditer(text):
        start, end = match.start(), match.end()
        if _spans_overlap(start, end, claimed_spans):
            continue
        word = match.group()
        lower = word.lower()
        # "I" must be uppercase to match as a pronoun
        if lower == "i" and word != "I":
            continue
        case = _PRONOUN_CASE_MAP.get(lower)
        if case:
            pronouns.append((start, end, lower, case))

    return pronouns


def _tokenize_non_speech(
    text: str,
    actor: "Character",
    candidates: list[tuple[str, "Character"]],
    is_first_segment: bool,
) -> list[TextToken | VerbToken | PronounToken | CharRefToken]:
    """Tokenize a non-speech segment.

    Args:
        text: The non-speech text to tokenize.
        actor: The character performing the emote.
        candidates: Character reference candidates from
            :func:`build_char_candidates`.
        is_first_segment: Whether this is the first non-speech
            segment in the emote (determines auto-verb for first word).

    Returns:
        List of tokens.
    """
    if not text:
        return []

    # Step 1: Find verb markers (.word patterns)
    claimed_spans: list[tuple[int, int]] = []
    verb_spans: list[tuple[int, int, str]] = []  # (start, end, base_form)

    for match in _VERB_MARKER_PATTERN.finditer(text):
        # The match includes the dot; the group(1) is the word after dot
        dot_start = match.start()
        word_end = match.end()
        base_form = match.group(1)
        verb_spans.append((dot_start, word_end, base_form))
        claimed_spans.append((dot_start, word_end))

    # Step 1b: Auto-verb for first word of the emote
    # Only if this is the first non-speech segment AND the text starts
    # with a word (not whitespace or punctuation)
    auto_verb_span: tuple[int, int, str] | None = None
    if is_first_segment:
        first_word_match = re.match(r"([a-zA-Z]\w*)", text)
        if first_word_match:
            word = first_word_match.group(1)
            start, end = first_word_match.start(), first_word_match.end()
            # Only auto-verb if it's not a first-person pronoun
            if word.lower() not in _PRONOUN_CASE_MAP:
                if not _spans_overlap(start, end, claimed_spans):
                    auto_verb_span = (start, end, word)
                    claimed_spans.append((start, end))

    # Step 2: Find character references
    char_ref_spans = _find_char_ref_spans(text, candidates, claimed_spans)
    for start, end, _char, _matched in char_ref_spans:
        claimed_spans.append((start, end))

    # Step 3: Find pronouns
    pronoun_spans = _find_pronoun_spans(text, claimed_spans)
    for start, end, _pron, _case in pronoun_spans:
        claimed_spans.append((start, end))

    # Step 4: Build sorted list of all identified spans
    all_spans: list[tuple[int, int, str, object]] = []

    # Auto-verb
    if auto_verb_span:
        s, e, word = auto_verb_span
        all_spans.append((s, e, "verb", word))

    # Explicit verb markers
    for s, e, base_form in verb_spans:
        all_spans.append((s, e, "verb", base_form))

    # Character references
    for s, e, char, matched in char_ref_spans:
        all_spans.append((s, e, "charref", (char, matched)))

    # Pronouns
    for s, e, pron, case in pronoun_spans:
        all_spans.append((s, e, "pronoun", (pron, case)))

    # Sort by position
    all_spans.sort(key=lambda span: span[0])

    # Step 5: Build token list, filling gaps with TextTokens
    tokens: list[TextToken | VerbToken | PronounToken | CharRefToken] = []
    pos = 0

    for span_start, span_end, span_type, data in all_spans:
        # Text before this span
        if span_start > pos:
            tokens.append(TextToken(text[pos:span_start]))

        if span_type == "verb":
            tokens.append(VerbToken(data))
        elif span_type == "charref":
            char, matched = data
            tokens.append(CharRefToken(char, matched))
        elif span_type == "pronoun":
            pron, case = data
            tokens.append(PronounToken(pron, case))

        pos = span_end

    # Trailing text
    if pos < len(text):
        tokens.append(TextToken(text[pos:]))

    return tokens


# =========================================================================
# Public Tokenizer
# =========================================================================


def tokenize_dot_pose(
    raw_input: str,
    actor: "Character",
    room_occupants: list["Character"] | None = None,
) -> list[TextToken | VerbToken | PronounToken | SpeechToken | CharRefToken]:
    """Tokenize a dot-pose input string.

    Splits input into speech and non-speech segments, then tokenizes
    each non-speech segment for verb markers, character references,
    and first-person pronouns.

    Args:
        raw_input: The text after the ``.`` command prefix.
        actor: The character performing the emote.
        room_occupants: Characters in the room.  If ``None``, no
            character reference matching is performed.

    Returns:
        Ordered list of tokens representing the parsed emote.
    """
    if not raw_input or not raw_input.strip():
        return []

    candidates = build_char_candidates(
        actor, room_occupants or []
    )

    segments = _split_speech_segments(raw_input)
    tokens: list[
        TextToken | VerbToken | PronounToken | SpeechToken | CharRefToken
    ] = []

    # Track whether we've seen the first non-speech segment
    seen_first_non_speech = False

    for segment_text, is_speech in segments:
        if is_speech:
            tokens.append(SpeechToken(segment_text, actor))
        else:
            is_first = not seen_first_non_speech
            segment_tokens = _tokenize_non_speech(
                segment_text, actor, candidates, is_first
            )
            tokens.extend(segment_tokens)
            # Only count as "seen first" if the segment produced
            # any non-whitespace content
            if segment_text.strip():
                seen_first_non_speech = True

    return tokens


# =========================================================================
# Per-Observer Renderer
# =========================================================================


def render_for_observer(
    tokens: list[
        TextToken | VerbToken | PronounToken | SpeechToken | CharRefToken
    ],
    actor: "Character",
    observer: "Character",
) -> str:
    """Render a token stream for a specific observer.

    Handles first-mention tracking, verb conjugation, pronoun
    transformation, and character reference resolution.

    Args:
        tokens: Parsed token list from :func:`tokenize_dot_pose`.
        actor: The character who performed the emote.
        observer: The character receiving the rendered message.

    Returns:
        Fully rendered emote string for this observer.
    """
    is_actor = observer is actor
    gender = GENDER_MAP.get(
        getattr(actor, "sex", "ambiguous") or "ambiguous", "neutral"
    )

    parts: list[str] = []
    actor_named = False
    # Track whether any non-whitespace content has been emitted before
    # the first actor mention.  Used to decide whether the first-mention
    # name should be capitalize_first'd (sentence-initial) or left
    # lowercase (mid-sentence, e.g. after a speech block).
    has_prior_content = False

    for token in tokens:
        if isinstance(token, TextToken):
            parts.append(token.text)
            if token.text.strip():
                has_prior_content = True

        elif isinstance(token, VerbToken):
            if not actor_named:
                # First verb — prepend actor name or "You"
                actor_named = True
                if is_actor:
                    # Actor self-view: "You lean" or "you lean" if
                    # speech came first
                    you = "You" if not has_prior_content else "you"
                    parts.append(f"{you} {token.base_form}")
                else:
                    # Observer: always capitalize_first on first mention
                    display_name = capitalize_first(
                        actor.get_display_name(observer)
                    )
                    if _should_conjugate(token.base_form):
                        conjugated = conjugate_third_person(token.base_form)
                        parts.append(f"{display_name} {conjugated}")
                    else:
                        parts.append(f"{display_name} {token.base_form}")
            else:
                # Subsequent verb — just conjugate (no name prepend)
                if is_actor:
                    parts.append(token.base_form)
                else:
                    if _should_conjugate(token.base_form):
                        parts.append(
                            conjugate_third_person(token.base_form)
                        )
                    else:
                        parts.append(token.base_form)
            has_prior_content = True

        elif isinstance(token, PronounToken):
            if token.case == "subject":
                # Subject pronoun "I"
                if not actor_named:
                    # First mention — use full name or "You"/"you"
                    actor_named = True
                    if is_actor:
                        you = "You" if not has_prior_content else "you"
                        parts.append(you)
                    else:
                        # Observer: always capitalize_first on first mention
                        display_name = capitalize_first(
                            actor.get_display_name(observer)
                        )
                        parts.append(display_name)
                else:
                    # Subsequent mention — use pronoun
                    if is_actor:
                        parts.append("you")
                    else:
                        pronoun = transform_pronoun(
                            "I", "third", gender
                        )
                        parts.append(pronoun)
            else:
                # Non-subject pronouns: always render as pronoun form
                if is_actor:
                    transformed = transform_pronoun(
                        token.original, "second"
                    )
                    parts.append(transformed)
                else:
                    transformed = transform_pronoun(
                        token.original, "third", gender
                    )
                    parts.append(transformed)
            has_prior_content = True

        elif isinstance(token, SpeechToken):
            parts.append(
                process_speech(
                    token.text, token.speaker, observer, token.language
                )
            )
            has_prior_content = True

        elif isinstance(token, CharRefToken):
            # Resolve character reference per-observer
            display_name = token.character.get_display_name(observer)
            parts.append(display_name)
            has_prior_content = True

    result = "".join(parts)

    # Post-processing: capitalize first alphabetic character
    result = capitalize_first(result)

    # Post-processing: auto-punctuation
    stripped = result.rstrip()
    if stripped and stripped[-1] not in ".!?\"')":
        result = stripped + "."

    return result


# =========================================================================
# Room Broadcast
# =========================================================================


def render_dot_pose(
    tokens: list[
        TextToken | VerbToken | PronounToken | SpeechToken | CharRefToken
    ],
    actor: "Character",
    location: object,
    exclude: list | None = None,
) -> None:
    """Render and broadcast a dot-pose emote to all room occupants.

    Each observer receives a unique rendering with identity-aware
    character names, verb conjugation, and pronoun transformation.

    Args:
        tokens: Parsed token list from :func:`tokenize_dot_pose`.
        actor: The character performing the emote.
        location: The room to broadcast in.
        exclude: Characters/objects to exclude from receiving the
            message.
    """
    exclude_set = set(exclude) if exclude else set()

    for observer in location.contents:
        if observer in exclude_set:
            continue
        if not hasattr(observer, "msg"):
            continue

        rendered = render_for_observer(tokens, actor, observer)
        observer.msg(text=rendered, type="pose", from_obj=actor)
