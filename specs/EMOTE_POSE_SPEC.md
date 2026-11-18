# Emote, Pose & Communication System Specification

## Overview

This spec covers the emote, pose and communication commands. Every one of them renders one string per observer, so each observer reads every character by the name that observer knows them by.

- **Dot-pose (`.`)** — LambdaMOO-style first-person natural emoting with automatic perspective transformation
- **Traditional emote (`emote`)** — third-person emoting with identity-aware character references
- **Say (`say`)** — speech with per-observer speaker attribution
- **Directed speech (`to`)** — `say` aimed at one target; everyone present hears it, and a radio you hold or wear is transmitted through
- **Whisper (`whisper`)** — directed speech with per-observer attribution for speaker and target
- **Think (`think`)** — private interiority as the MUSH thoughtbubble `Name thinks . o O ( … )`, perceived only by the actor and (v1) Builder+; the interiority channel LLM NPCs use instead of leaking thought into their visible emote
- **Template socials** — `nod`, `shrug`, `laugh`, `sigh`, `smile`, `wave`, `bow`, `frown`
- **Grammar engine (`world/grammar.py`)** — shared verb conjugation, pronoun transformation and article handling

This system is the **communication counterpart** to the Identity & Recognition System (`IDENTITY_RECOGNITION_SPEC.md`). The identity spec defines *how characters are perceived*; this spec defines *how that perception is expressed in communication*. The grammar engine is specified in `GRAMMAR_ENGINE_SPEC.md`; this spec uses it.

### Relationship to Existing Systems

- **Replaces** `NATURAL_POSING_AND_PRONOUN_FIXES_SPEC.md` (deleted). Its `$pron()`/`$conj()` approach is incompatible with per-observer identity rendering.
- **Depends on** the identity system: sdesc, the `get_display_name` override, recognition memory.
- **Provides** the grammar engine that the identity spec's article handling, possessive forms and subject-verb agreement use.

### Design Principles

1. **First-person natural writing** — Players write as their characters think: "I lean back." The system handles perspective transformation for all observers.
2. **Per-observer truth** — Every observer may know every character by a different name. Communication renders uniquely per observer.
3. **Speech as structured data** — Quoted speech is tokenized separately from action text, so a language system can process speech independently.
4. **Grammar engine as shared infrastructure** — Verb conjugation, article handling and pronoun transformation live in a standalone module usable by any system.
5. **Explicit over implicit** — Verb markers (`.verb`) are explicit player annotations. The system does not attempt NLP-based verb detection.
6. **Graceful degradation** — Commands work without the identity system's name resolution, falling back to `.key` for character names.

### Why Not Evennia's `$pron()`/`$conj()`

Evennia's FuncParser (`$pron()`, `$conj()`, `$You()`) sends one template string to `msg_contents()` with `from_obj=actor` and resolves it for two audiences: the actor (`from_obj`) sees "You" and base-form verbs; everyone else sees `actor.key` and conjugated verbs. That is a **binary model**. The identity system needs **N-way resolution**: each observer may know the actor by a different name. FuncParser takes the actor's name from `.key`, bypassing `get_display_name(observer)`, and has no hook for per-observer name resolution. The codebase does not use `$pron()`, `$conj()` or `$You()`, so adopting FuncParser would mean retrofitting every `msg_contents()` call — the same scope as a custom pipeline, with the binary limit. The game therefore uses its own pipeline that produces **one string per observer**, with full control over name resolution, pronoun transformation and verb conjugation.

---

## Commands

All the commands below are open to everyone (`cmd:all()`), help category Social. The template socials are built in `world/emote_templates.py`; the rest are in `commands/CmdCommunication.py`.

### Dot-Pose (`.`)

`CmdDotPose`, key `.`. First-person natural emoting with automatic perspective transformation.

**Syntax:**

```
.<verb> <text> [.verb] [text] ["speech"] [I .verb] [text]
```

**Examples:**

| Input | Actor Sees | Observer Who Knows Actor (male) | Observer Who Doesn't Know Actor |
|---|---|---|---|
| `.lean back.` | You lean back. | Jorge leans back. | A lanky man leans back. |
| `.scratch at the stubble on my jaw, "What day is it?" I .ask.` | You scratch at the stubble on your jaw, "What day is it?" you ask. | Jorge scratches at the stubble on his jaw, "What day is it?" he asks. | A lanky man scratches at the stubble on his jaw, "What day is it?" he asks. |
| `"Get down!" I .shout, .diving behind cover.` | "Get down!" you shout, diving behind cover. | "Get down!" Jorge shouts, diving behind cover. | "Get down!" A lanky man shouts, diving behind cover. |
| `.nod at Jorge` | You nod at Jorge. | Jorge nods at Maria. | A lanky man nods at a compact woman. |
| `"Hey," I .say, .waving my hand. "Over here!"` | "Hey," you say, waving your hand. "Over here!" | "Hey," Jorge says, waving his hand. "Over here!" | "Hey," A lanky man says, waving his hand. "Over here!" |
| `.fold my arms and .lean against the wall.` | You fold your arms and lean against the wall. | Jorge folds his arms and leans against the wall. | A lanky man folds his arms and leans against the wall. |

An observer's first mention of the actor is always capitalized, so after speech an sdesc reads "A lanky man" (see §Capitalization and Punctuation). `.` with no text shows the usage help.

The first-person syntax, the token model and the rendering rules are below (§First-Person Pose Syntax, §Per-Observer Rendering).

### Traditional Emote (`emote`)

`CmdEmote`, key `emote`, aliases `:` and `pose`. The player writes in third person; the system prepends the actor's per-observer display name.

**Syntax:**

```
emote <third-person action text>
```

**Examples:**

| Input | Actor Sees | Observer Who Knows Actor | Observer Who Doesn't |
|---|---|---|---|
| `emote leans back against the wall.` | Jorge leans back against the wall. | Jorge leans back against the wall. | A lanky man leans back against the wall. |
| `emote nods at Jorge.` | Jorge nods at Maria. | Jorge nods at Maria. | A lanky man nods at a compact woman. |

**Self-view:** the actor sees their own `.key` (real name), NOT "You". The player wrote in third person — "You leans" would be broken grammar, and deconjugating verbs is fragile and error-prone. See Appendix C.

**No verb or pronoun transformation** is performed for `emote`; the player is responsible for their own grammar. Processing is limited to (`render_emote_for_observer`, `world/emote.py`):

- resolving character references per observer (second person for the observer themselves), the same bare-name matching as dot-pose;
- dropping an article or a stray `you` typed right before a reference, since the resolved name carries its own;
- turning `you's` into `your`;
- showing quoted words as `"..."` to observers who cannot hear. Character references inside quotes are not resolved.

No period is added, and the dot-pose capitalization rules do not apply (see §Capitalization and Punctuation).

### Say (`say`)

`CmdSay`, key `say`, alias `"`.

**Syntax:**

```
say <message>
"<message>
```

**Example:**

| Input | Actor Sees | Observer Who Knows Speaker | Observer Who Doesn't |
|---|---|---|---|
| `say Hello there.` | You say, "Hello there." | Jorge says, "Hello there." | A lanky man says, "Hello there." |

**Rules** (`CmdSay.func`; `world/speech.py`):

- `CmdSay.func` sends the actor their own line, then calls `broadcast_speech(caller, speech, location)`, the room loop `say` and `to` share. `whisper` shares only the line renderer, `render_speech_line` (#656).
- Speech content passes through unchanged — no pronoun or verb transformation. The only transformation is per-observer speaker attribution.
- **Attribution is not `get_display_name`.** `render_speech_line` uses `resolve_speaker_attribution(speaker, observer)` (`world/voice.py`): sight and the voice channel decide *who*, so a speaker hidden from the observer is attributed by VOICE, and a remembered voice can name someone the observer cannot see (CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §4.5).
- **Hearing gates the content.** A deaf-but-watching observer reads "X says something you can't make out." (`render_speech_line`). An observer who is both deaf and blind gets nothing (`broadcast_speech`).
- **Voice flavour may be appended** for observers who can see the speaker (`visible_voice_flavor`, `render_speech_line`). A garbled voice always renders; otherwise it is a low-frequency sprinkle rolled once per utterance, so every observer reads it consistently.
- `say` breaks stealth: `break_stealth(caller)` in `CmdSay.func`, placed *after* the argument and location guards, so a refused command does not blow your cover for an action that never happened (#2530).

### Directed Speech (`to`)

`CmdTo`. `say` aimed at one target. Everyone present still hears it.

**Syntax:**

```
to <target> <message>
```

**Examples** (actor speaks to a character they know as "Jorge"):

| Audience | Sees |
|---|---|
| Actor | You say to Jorge, "Meet me later." |
| Target | A lanky man says to you, "Meet me later." |
| Room observer who knows neither | A lanky man says to a compact woman, "Meet me later." |

**Rules** (`CmdTo.func`, `commands/CmdCommunication.py`):

- The target is the longest run of leading words that names exactly one thing, so a multi-word sdesc is not split into the message. At least one word is always left for the message.
- Attribution, hearing and voice flavour work exactly as for `say` (`world/speech.py` `broadcast_speech` with `target=`). The target's speech payload is marked `addressed`.
- You can address anyone or anything in the room, and anything you hold or wear, but not something carried in a pocket (`addressable`). The refusal reads `<target> is stowed away — you'd have to hold it or wear it to speak to it.`
- Aimed at a radio, `to` transmits through it, spoken openly (`world.radio.transmit`), instead of speaking to the room. You must be holding or wearing the radio, or be seated at the console (`world.radio.can_transmit_through`). A channelled action refuses a radio target first.
- `to` breaks stealth. As built, the call comes after the usage, search, reach and channelling checks but before the radio hold-or-seat check, so that one refusal still costs cover.

### Whisper (`whisper`)

`CmdWhisper`, key `whisper`. Directed speech with per-observer attribution for both speaker and target.

**Syntax:**

```
whisper "<message>" to <person>
whisper <person> = <message>
```

The first form is the syntax `CmdWhisper`'s help gives. `CmdWhisper.parse` matches the quoted-to form first and falls back to `=`; the usage error in `CmdWhisper.func` advertises only the quoted-to form. Owner ruling of 2026-07-03, recorded in `specs/proposals/STEALTH_AND_DETECTION_SPEC.md` §6.4 (the whisper carve-out): quoted-to is the syntax, and `whisper <person> = <message>` is a legacy alias that stays accepted — not a deprecation.

**Examples** (actor whispers to a character they know as "Jorge"):

| Audience | Sees |
|---|---|
| Actor | You whisper to Jorge, "Meet me later." |
| Target | A compact woman whispers to you, "Meet me later." |
| Room observer who knows both | Jorge whispers something to Maria. |
| Room observer who knows neither | A lanky man whispers something to a compact woman. |

**Three-audience rendering:**

| Audience | Template | Character References |
|---|---|---|
| Actor (speaker) | `You whisper to {target}, "{message}"` | Target = `get_display_name(actor)` |
| Target | `{actor} whispers to you, "{message}"` | Actor named by `resolve_speaker_attribution(actor, target)`: by sight, or by a known voice when the whisperer is hidden. Hearing gates the words: a deaf target reads `{actor} whispers something to you, but you can't make it out.` |
| Room observers | `{actor} whispers something to {target}.` | Both = `get_display_name(observer)` |

**Visibility rule:** room observers see that a whisper occurred and between whom, but NOT the speech content. Only the speaker and target receive the content. A whisper is a visual event to bystanders: only those who can see, and from whom neither the whisperer nor the target is hidden, get the `whispers something to` line; nobody else gets anything. Whispering does not break stealth. If the whisperer is hidden from the target, the target's awareness of the whisperer rises to SUSPICIOUS: they know something is there, not who.

**Target resolution** follows the identity spec's targeting priority:

1. Assigned names from the actor's recognition memory
2. Sdescs of visible room occupants
3. Character `.key` values — staff only. `Character.search` always runs identity matching first; for staff (`world.search.may_use_real_names`) its fallback also keeps matches by `.key`. For everyone else the fallback drops any character `world.search.is_identity_match` does not allow, which is only an assigned name or an sdesc, so an ordinary player cannot whisper to a character by real key. A hidden target is not in the search pool and reads as a plain miss.
4. Ordinals for ambiguous matches

If no target is found, the actor receives an error message. If multiple targets match without an ordinal, the actor is prompted to clarify.

### Think (`think`)

`CmdThink`, key `think`. Private roleplay — a character's interiority, rendered as the MUSH thoughtbubble. The thinker's name resolves per-observer like an emote; the content is shown only to perceivers.

**Examples** (actor thinks "these are my innermost thoughts."):

| Audience | Sees |
|---|---|
| Actor | You think . o O ( these are my innermost thoughts. ) |
| Builder+ in room (knows actor as "Bob") | Bob thinks . o O ( these are my innermost thoughts. ) |
| Builder+ in room (doesn't know actor) | A lanky man thinks . o O ( these are my innermost thoughts. ) |
| Everyone else | (nothing) |

**Perceiver rule (v1):** only the actor and **Builder+** in the room perceive a thought — staff watching a scene see what characters (and LLM NPCs) are thinking. `render_think` gates on a single perceiver test. Staff here means an observer that passes `check_permstring("Builder")` (`render_think`), not the shared staff test `world.search.may_use_real_names`. This is the channel an LLM NPC uses for interiority instead of leaking private thought into its visible `emote`. Thinking does not break stealth.

### Pre-Built Emote Templates (template socials)

`nod`, `shrug`, `laugh`, `sigh`, `smile`, `wave`, `bow` and `frown` (`SOCIAL_COMMANDS`, `world/emote_templates.py`). Each has a solo form and, except `sigh`, a targeted form. Observers read the templates below, with `{actor}` and `{target}` resolved via `get_display_name(observer)`:

| Social | Solo | Targeted |
|---|---|---|
| nod | `{actor} nods.` | `{actor} nods at {target}.` |
| shrug | `{actor} shrugs.` | `{actor} shrugs at {target}.` |
| laugh | `{actor} laughs.` | `{actor} laughs at {target}.` |
| sigh | `{actor} sighs.` | (none) |
| smile | `{actor} smiles.` | `{actor} smiles at {target}.` |
| wave | `{actor} waves.` | `{actor} waves at {target}.` |
| bow | `{actor} bows.` | `{actor} bows respectfully to {target}.` |
| frown | `{actor} frowns.` | `{actor} frowns at {target}.` |

```
nod             → "Jorge nods."          / "A lanky man nods."
nod jorge       → "Jorge nods at Maria." / "A lanky man nods at a compact woman."
shrug           → "Jorge shrugs."
```

- The actor sees `You nod.` or `You nod at <target as the actor knows them>.` (`bow`: `You bow respectfully to …`).
- `sigh` has no targeted form: `sigh <anything>` replies `Usage: sigh`.
- The rest of the line is searched for as the target (`caller.search`).
- A social breaks stealth once it is sure to happen; a usage refusal or a failed search does not.
- The person a targeted social names is marked `addressed`, so an NPC can answer it.

---

## First-Person Pose Syntax

### Command Structure

The `.` command accepts two starting patterns:

- **Verb-first:** `.lean back` — the first word after `.` is the first verb
- **Speech-first:** `"Get down!" I .shout` — starts with quoted speech; the actor reference comes from a later `I` pronoun

### Verb Markers

The `.` prefix marks a word as a verb requiring conjugation:

- **First verb:** the first word after the `.` command trigger (no additional `.` prefix needed on it), unless that word is a first-person pronoun (I, me, my, mine, myself) or the pose starts with speech or another non-letter; then only `.`-marked words are verbs.
- **Subsequent verbs:** marked with a `.` prefix anywhere in the text: `I .murmur`, `.diving behind cover`.

**Disambiguation rule:** `.` followed by a letter (`[a-zA-Z]`) is a verb marker. `.` followed by whitespace, punctuation, end-of-string, or a digit is literal punctuation. A dot right after another dot (`...word`) is never a verb marker.

```
.lean back.                    → "lean" = verb, final "." = punctuation
.lean back, "Hello." I .say.   → "lean" = verb, "." inside quotes = speech,
                                  ".say" = verb, final "." = punctuation
.lean back...                  → "lean" = verb, "..." = punctuation
```

**Only mark words that need conjugation.** Participles like `taking` and `diving` don't change form between first and third person — they don't need markers. The system trusts the player's explicit markers: a marked non-verb (e.g., `.the`) is conjugated anyway ("thes") — that's the player's error, and help text should be clear that only verbs should be marked. Exception: a marked word ending in -ing is treated as a participle and left as typed (`.diving` → "diving"), except the -ing base verbs bring, cling, fling, king, ping, ring, sing, sling, spring, sting, string, swing, thing, wing, wring and zing (`world/emote.py` `_should_conjugate`).

### Pronoun Detection

First-person pronouns outside quoted speech are detected and transformed:

| Pronoun | Case | Actor View | Observer (male) | Observer (female) | Observer (neutral) |
|---|---|---|---|---|---|
| I | subject | you | he | she | they |
| me | object | you | him | her | them |
| my | possessive adj. | your | his | her | their |
| mine | possessive pro. | yours | his | hers | theirs |
| myself | reflexive | yourself | himself | herself | themselves |

**Detection rules:**

- Case-insensitive matching: `I`, `My`, `my` all match
- Only matched **outside** quoted speech blocks
- **Word-boundary matching**: `"mine"` inside `"undermine"` does NOT match
- `I` is only matched as a standalone capital letter at a word boundary

### Speech Blocks

Text enclosed in double quotes (`"..."`) is a speech block:

- **Never scanned** for pronouns, verb markers, or character references.
- **Preserved verbatim** for the speaker and for every observer who can **hear** the speaker. `process_speech` (`world/emote.py`) redacts the quoted words to `"..."` for any observer other than the speaker who fails `can_hear` (CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §4, #589). The speaker always hears their own words.
- **Tokenized as distinct speech tokens** with speaker metadata (see §Speech Token System).

Unmatched quotes (an opening `"` with no closing `"`) treat the rest of the input as speech. Nested quotes are not supported — the parser matches the first `"` to the next `"`.

### Character References

Other characters mentioned in the emote are resolved by **bare name matching** (`build_char_candidates`):

1. Get all visible characters in the room (excluding the actor).
2. For each character, collect names the actor might use:
   - The display name the actor already holds for them (assigned name, or sdesc with article), and the same without its article
   - Each single word of a name the actor holds for them, except function words and generic person-words (the, that, man, guy…)
   - The raw sdesc
   - Height/build descriptor + keyword, the keyword alone, and the descriptor alone (which matches only when typed with a capital letter), all built from the character's apparent look (`world.identity.apparent_axes`)
   - The character's `.key`, for staff only (`world.search.may_use_real_names`)
3. Sort candidates by string length, descending (longest match first).
4. Scan the emote text (excluding quoted speech) for case-insensitive, whole-word matches.
5. Replace matches with character-reference tokens.

This follows the identity spec's targeting priority: assigned names, then sdescs, then real keys (staff only), then ordinals.

**Only scanned outside quoted speech.** If your character says someone's name in dialogue, that's speech content, not a game-object reference.

**Ambiguity:** if several characters match the same string, an ordinal picks one: `2nd tall man` resolves to the second character in the room that matches `tall man`. Only numeric ordinals work (`1st`, `2nd`, `3rd`…), not words like `second`. This is the emote's own pre-pass (`world/emote.py` `_find_ordinal_char_ref_spans`), not the search ordinal system. With no ordinal, the first match is taken (consistent with Evennia's default search behavior).

**No match:** a name that matches no room occupant is plain text, not an error. This handles references to absent characters, objects, or abstract concepts naturally.

**Self-reference:** the actor typing their own name is not a character reference. `build_char_candidates` skips the actor, and `CmdEmote` and `CmdDotPose` leave the caller out of the room list, so the typed name stays plain text and every observer reads it exactly as typed. In a dot-pose, `I`, `me` and `my` are the way to refer to yourself.

The resolved game object is stored in the reference token. At render time each observer sees that character via `get_display_name(observer)`, which may be completely different from what the actor typed.

---

## Token Model

The parser (`world/emote.py`) turns the input into a stream of typed tokens; each type renders differently per observer.

| Token | Holds |
|---|---|
| `TextToken` | literal text, passed through unchanged |
| `VerbToken` | a marked verb's base form ("lean", "ask") |
| `PronounToken` | the typed first-person pronoun and its case: subject, object, possessive_adj, possessive_pro, reflexive |
| `SpeechToken` | the quoted content without quotes, the speaker (usually the actor), and a language (`None` = common/default) |
| `CharRefToken` | the resolved character and the text the actor typed ("Jorge", "the tall man") |

### Parsing Order

1. Extract speech blocks into speech tokens.
2. Identify verb markers (the first word, and `.`-marked words; a final `.` at end-of-string is punctuation).
3. Identify pronouns outside speech.
4. Identify character references outside speech.
5. Everything else is text.

For `.scratch at the stubble on my jaw, "What day is it?" I .ask.` this gives: verb `scratch`, text ` at the stubble on `, pronoun `my`, text ` jaw, `, speech `What day is it?`, text, pronoun `I`, text, verb `ask`, text `.`.

In a speech-first pose (`"Get down!" I .shout, .diving behind cover.`), the first actor reference comes from the `I` pronoun, not from an implicit verb subject; the first-mention rule applies, so that first `I` resolves to the full display name. Multiple speech blocks (`"Hey," I .say, .waving my hand. "Over here!"`) are each tokenized independently, and the speech hook processes each separately.

---

## Grammar Engine

Verb conjugation, article handling (including pluralia tantum), pronoun transformation, possessive forms, capitalization and default sdesc keywords are specified in [`GRAMMAR_ENGINE_SPEC.md`](GRAMMAR_ENGINE_SPEC.md). The pronoun tables are repeated in Appendix B for reference from the rendering pipeline. The grammar engine uses `inflect` for phoneme-aware article selection (a/an).

---

## Per-Observer Rendering

### Broadcast

`render_dot_pose(token_stream, actor, location, exclude=None)` (`world/emote.py`) renders the pose once for each perceiver in the room and sends it.

- **Who receives it:** `perceivers(location, exclude_set)` (`world/perception.py`), a character duck-type filter (#2788, #3420, #3530). Most objects standing in live rooms are not characters. A `hasattr(observer, "msg")` check excludes nothing — every typeclassed Evennia object has `.msg` — so do not use one as the filter.
- **The msg is typed and attributed:** `observer.msg(text=rendered, type="pose", from_obj=actor, **payload)`.
- **A structured speech payload rides along.** `_extract_speech` pulls any embedded quote and the ids of referenced characters; `world/speech.py` `speech_payload` attaches `speech` (hearing-gated) and `addressed`, so an NPC can tell "posed AT me" from "posed in the room". A wordless pose still carries `addressed` via `payload.setdefault`; `render_emote` carries the same fallback (#2462).

`render_for_observer` renders one observer's string.

### Actor Self-View

When `observer == actor`:

| Token Type | Rendering |
|---|---|
| TextToken | Unchanged |
| VerbToken | Second-person form via `conjugate_second_person`: the base form, with a typed -s form normalised (`.leans` → "lean", `.is` → "are"). -ing participles, modals and irregular past forms pass through unchanged. |
| PronounToken | Second-person form: I→you, my→your, me→you, mine→yours, myself→yourself |
| SpeechToken | `process_speech(text, speaker, observer)` |
| CharRefToken | `_resolve_charref` — `"you"`/`"your"` if the ref is the actor (self-ref), else `get_display_name(actor)` |

The actor's own reference (implicit from the first verb, or explicit `I`) renders as **"You"** (capitalized if sentence-initial, lowercase otherwise).

### Observer View

When `observer != actor`:

| Token Type | Rendering |
|---|---|
| TextToken | Unchanged |
| VerbToken | `conjugate_third_person(base_form)`: lean→leans, ask→asks |
| PronounToken | Third-person, gender-matched: I→he/she/they, my→his/her/their |
| SpeechToken | `process_speech(text, speaker, observer)` |
| CharRefToken | `_resolve_charref` — `"you"`/`"your"` if the ref IS the observer, else `get_display_name(observer)` |

The actor's name renders as `get_display_name(observer)` — "Jorge", "a lanky man", etc.

### First-Mention vs. Subsequent-Mention

The actor may be referenced several times in one pose. The renderer tracks whether the actor has been named.

**First reference** to the actor (implicit from the first verb, or the first `I` pronoun):

- Actor self-view: "You", or "you" when speech or other text comes before it
- Observer: full display name via `get_display_name(observer)`, always capitalized — "Jorge" or "A lanky man"

**Subsequent references** to the actor (`I` pronoun tokens after the first reference):

- Actor self-view: "you" (lowercase)
- Observer: gender-matched subject pronoun — "he", "she", "they"

**Possessive, objective and reflexive pronouns** (`my`, `me`, `mine`, `myself`) are **always** rendered as pronouns regardless of position:

- Actor: "your", "you", "yours", "yourself"
- Observer: "his"/"her"/"their", "him"/"her"/"them", etc.

**Character references** (other characters in the pose) render as full display names via `get_display_name(observer)` — with **one carve-out: a reference to the observer themselves renders second-person** (`you`, or `your` for the possessive). So a pose that targets you reads "watches **you**", never your own name; everyone else still resolves to the name that observer knows them by. No pronoun substitution for any other (non-actor, non-observer) character. Dot-pose and traditional emote share this rule — both resolve references through `_resolve_charref(character, observer)`. Because the resolved name carries its own article, an article (or a stray `you`) typed right before a reference is dropped: `.watch the lanky man` renders "…watches a lanky man" or "…watches Jorge", never "the a lanky man". A possessive reference to the observer, `the lanky man's`, renders `your`.

### Rendering Trace

Input: `.lean back and .sigh. "What a day," I .mutter.`

- **Observer who knows the actor as "Jorge" (male):** the first verb names the actor ("Jorge leans"), `sigh` → "sighs", the speech passes through, the second `I` is a subsequent reference → "he", `mutter` → "mutters".
  Final: `Jorge leans back and sighs. "What a day," he mutters.`
- **Actor:** the first verb gives "You lean", verbs stay in base form, the second `I` → "you".
  Final: `You lean back and sigh. "What a day," you mutter.`

### Capitalization and Punctuation

These rules apply to dot-pose only (`render_for_observer`). `render_emote_for_observer` applies neither, so `emote leans back` broadcasts "Jorge leans back" with no period.

**Capitalization:**

1. The first letter of the rendered string is capitalized:
   - Named actors: "Jorge leans back." — already capitalized
   - Sdescs: "a lanky man leans back." → "A lanky man leans back." — article capitalized
   - Self-view: "You lean back." — already capitalized
   - Speech-first: `"Get down!" Jorge shouts.` — the opening quote is the first character; the letter inside is already capitalized
2. An observer's first mention of the actor is always capitalized, so an sdesc after speech reads `"Get down!" A lanky man shouts.`
3. The letter after any *bare* `.`, `!` or `?` followed by whitespace is capitalized, so a multi-beat pose reads "…sets a glass down. He lets his eyes linger." Punctuation that *closes a quote* is excluded, so `"Get down!" you shout` stays lowercase.

**Auto-punctuation:** the check examines the last non-whitespace character. If it is not `.`, `!`, `?`, `"`, `'` or `)`, a period is appended. This prevents double punctuation while ensuring clean sentence endings.

### Performance

Per-observer rendering produces N strings for N observers. For a room with 20 observers and a pose referencing 2 characters: 20 token stream traversals, 20 × 2 = 40 `get_display_name` lookups (dict lookups in recognition memory), 20 string concatenations. This is microsecond-scale work per pose, the same profile as `msg_room_identity` in the identity spec.

---

## Identity System Integration

### Self-Perception Resolution

`get_display_name(self)` returns the character's `.key` (their own real name), NOT "You". This keeps third-person sentences correct everywhere: "You is standing here" or "You leans back against the wall" would occur anywhere `get_display_name(self)` is used in a third-person template.

Self-perception "You" is applied by the rendering layer, not by `get_display_name`:

| Context | Self-Perception Mechanism |
|---|---|
| Dot-pose (`.`) | The pipeline checks `observer == actor` and uses "You" + second-person verb forms |
| Traditional emote | Uses `get_display_name(self)` → `.key`. No "You" (the player wrote third person) |
| `say` / `whisper` | Fixed "You say" / "You whisper" line for the actor |
| Room descriptions | `_process_description_variables()` handles self-view for `look` |
| System messages | Explicit `if observer == actor` check in message templates |

See Appendix C for the rationale. The identity spec's §Self-Perception records this decision.

### Disguise Interaction

If the actor is disguised (via `appear`), their display name changes per observer as expected; for names, the pipeline calls `get_display_name(observer)` and the identity system handles the rest. Two other parts follow the disguise themselves:

- Pronouns come from the actor's apparent gender (`world.identity.get_apparent_gender`, which a disguise keyword decides), not from `sex`.
- Character-reference handles are built from the referenced person's apparent look (`world.identity.apparent_axes`), so their hidden real look cannot be used to pose at them.

If a *referenced* character is disguised, observers who see through the disguise see the real identity while others see the disguised sdesc.

---

## Speech Token System

Speech tokens carry who is speaking and in what language, so speech can be processed per observer without changing the emote parser.

The renderer calls the speech hook `process_speech(text, speaker, observer, language=None)` (`world/emote.py`) for each speech token. It returns the text in quotes, or `"..."` for an observer other than the speaker who cannot hear (see §Speech Blocks). A language system is meant to plug in here and nowhere else: implementing languages requires **zero changes to the emote parser**, only to `process_speech`.

---

## Death Filter

The death filter (`Character.msg` in `typeclasses/characters.py`) passes a dead character only the death curtain, messages from the death-progression script, and messages from staff that are not social. A message is social (`_is_social_message`) when its `type` is say, pose, emote, tell, whisper or ooc, or its text matches a speech pattern. Every other message, with or without a sender, is dropped. The communication commands send with `from_obj` and a `type` (`say` for say and to, `whisper` for whisper, `pose` for dot-pose, emote and the socials), so a dead character receives none of them, from staff included:

```python
observer.msg(text=rendered_message, type="say")
```

---

## Edge Cases

### Empty Input

`.` with no text after it: display the usage help message.

### Malformed Verb Markers

`.` followed by nothing at the end of the text is a literal period (`.` + end-of-string = punctuation). A `.` marker on a non-verb is conjugated anyway; a marked -ing word is the exception (see §Verb Markers).

### Missing Targets and Ambiguous References

See §Character References: no match is plain text; several matches take an ordinal, or the first match without one.

### Combat Context and Stealth

All communication commands work during combat; the combat handler does not block them. They are not free of effects: `say`, `to`, `emote`/`:`/`pose`, `.` and the template socials break stealth, so a hidden speaker emerges. The call comes once the command has passed its own checks, so a refused command does not cost cover (one exception is noted under §Directed Speech). `whisper` and `think` do not break stealth. `to` aimed at a radio transmits over it.

### Very Long Emotes

No explicit length limit is imposed by the emote system. Server-side limits (Evennia's input length cap) apply.

---

## Unbuilt

- 📋 UNBUILT (no issue) — **Language system.** The speaker's `say` or dot-pose sets the `language` field on speech tokens from the character's active language; `process_speech` checks the observer's comprehension: full comprehension gives the verbatim text, partial comprehension garbled/fragmented text, no comprehension a generic description (e.g., `"[speaks in an unfamiliar language]"`). Out of scope for this spec; the data model is ready.
- 📋 UNBUILT (no issue) — **Telepathy/psychic sense for `think`.** A future telepathy/psychic sense drops into `render_think`'s single perceiver test (slotting into `world/perception.py`'s capacity/sense framework) without changing callers.
- 📋 UNBUILT (no issue) — **Pronoun-aware placements.** `@look_place` / `@temp_place` integration with pronoun-aware descriptions.

---

## Not decided

- Should traditional `emote` get the dot-pose capitalization and auto-punctuation rules (§Capitalization and Punctuation)? Today it gets neither.
- Who counts as staff for seeing a `think` (§Think): should the display gates keep reading the permission on the character, or should every staff gate read the account's permission and honour `quell`, as the real-name doors do (#3818)?

---

## Where it lives

| File | Holds |
|---|---|
| `commands/CmdCommunication.py` | `CmdSay`, `CmdTo`, `CmdWhisper`, `CmdEmote`, `CmdDotPose`, `CmdThink` |
| `world/emote.py` | Tokenizer and per-observer renderer for dot-pose, emote and think; `process_speech` |
| `world/speech.py` | Shared speech line for say, to and whisper, the room loop for say and to, and the speech payload |
| `world/emote_templates.py` | The eight template socials (`SOCIAL_COMMANDS`) |
| `world/grammar.py` | Grammar engine: conjugation, articles, pronouns |
| `commands/default_cmdsets.py` | Adds `CmdSay`, `CmdTo`, `CmdWhisper`, `CmdEmote`, `CmdDotPose`, `CmdThink` and `SOCIAL_COMMANDS` to `CharacterCmdSet` |

Related documents: `IDENTITY_RECOGNITION_SPEC.md`, `GRAMMAR_ENGINE_SPEC.md`, `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md`, `specs/proposals/STEALTH_AND_DETECTION_SPEC.md`.

---

## Appendix A: Verb Conjugation

Conjugation is specified in `GRAMMAR_ENGINE_SPEC.md` §Verb Conjugation: the irregular table keyed by any recognised form (is/are/be, was/were, has/have, does/do), modals returned unchanged, irregular past forms (`IRREGULAR_PAST`) returned unchanged, and the regular rules (-s/-sh/-ch/-x/-z and -o → "es"; consonant + y → "ies" (vowels: a, e, i, o, u; all other letters are consonants); else "s"), reached after an already-conjugated form is normalised and the irregular table re-consulted. When a verb conjugates wrongly, extend the tables in `world/grammar.py` and record it in `GRAMMAR_ENGINE_SPEC.md`, not here.

---

## Appendix B: Pronoun Transformation Tables

### Table B.1 — First-Person to Second-Person (Actor Self-View)

| First Person | Second Person |
|---|---|
| I | you |
| me | you |
| my | your |
| mine | yours |
| myself | yourself |

### Table B.2 — First-Person to Third-Person (Observer View)

| First Person | Male | Female | Neutral |
|---|---|---|---|
| I | he | she | they |
| me | him | her | them |
| my | his | her | their |
| mine | his | hers | theirs |
| myself | himself | herself | themselves |

### Table B.3 — Gender Mapping

This map applies when no disguise keyword is active. Under a disguise, pronouns come from `world.identity.get_apparent_gender`; see IDENTITY_RECOGNITION_SPEC §Pronouns Under Disguise.

| Character `sex` Attribute | Gender Category |
|---|---|
| `"male"` | male |
| `"female"` | female |
| `"ambiguous"` | neutral |
| `"neutral"` | neutral |
| `"nonbinary"` | neutral |
| `"other"` | neutral |

---

## Appendix C: Architectural Decision — Self-Perception in `get_display_name`

The identity spec originally specified that `get_display_name(self)` returns `"You"`. That causes grammatical errors in any third-person context:

- Room description: "You is standing here." (should be "Jorge is standing here.")
- Traditional emote: "You leans back." (should be "Jorge leans back.")
- Combat message: "You attacks the bandit." (should be "Jorge attacks the bandit.")

Instead, `get_display_name(self)` returns `self.key`, the character's own real name, which is always safe in a third-person sentence, and self-perception "You" is handled by the communication/rendering layer (table in §Self-Perception Resolution). The `_process_description_variables()` system for `look` descriptions already handled self-perception separately from `get_display_name`, which was precedent for this separation. This keeps `get_display_name` safe in any grammatical context without special-casing.
