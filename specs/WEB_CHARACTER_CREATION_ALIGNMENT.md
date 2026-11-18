# Web Character Creation Alignment Spec

## Overview

This document defines how the web-based character creation should align with
the telnet-based character creation system in `commands/charcreate.py`. The
web door is `CharacterCreateView` in `web/website/views/characters.py`, with
the form `CharacterForm` in `web/website/forms.py`. Respawn on the web door is
described in full in
[`WEB_RESPAWN_CHARACTER_CREATION_SPEC.md`](WEB_RESPAWN_CHARACTER_CREATION_SPEC.md).

## Data Collection Requirements

### Telnet Character Creation Flow

**First Character:**
1. First name (validated, 2-30 chars, letters/hyphens/apostrophes)
2. Last name (validated, same rules; first and last together at most 30)
3. Sex (menu: Male / Female / Androgynous; stored as male/female/ambiguous)
4. Height (`HEIGHTS` in `world/identity.py`)
5. Build (`BUILDS`)
6. Hair colour (`HAIR_COLORS`, or Bald, which skips step 7)
7. Hair style (`HAIR_STYLES`)
8. GRIM distribution (300 points total)
   - Grit (1-150)
   - Resonance (1-150)
   - Intellect (1-150)
   - Motorics (1-150)
9. Confirm

**Respawn (after death):**
- Option 1: Flash clone (copy all stats from previous character), offered only
  when the dead body holds its own sleeve policy (#3667); otherwise both doors
  show the refusal instead of the card.
  - `create_flash_clone` asks the gate again when it builds the clone. It
    raises `PolicyRefused` if `flash_clone_refusal` objects, if the body still
    has its `death_progression` script (still on the table), or if another
    door has just taken the policy (`take_policy`).
  - If the build then fails part-way, the new body is deleted and the policy
    is put back (`restore_policy`).
  - After a good build an ordinary policy is spent and a standing one is
    re-issued in the new body's name (`renew_perpetual`).
  - The web door (`handle_respawn_submission`) catches `PolicyRefused` and
    sends the player back to the sleeve choice with the refusal text.
- Option 2: Choose from 3 random templates (300-point GRIM distributions).
  - Each template (`generate_random_template`) rolls its own name, sex,
    height, build and hair (about 15% come out bald); the player does not
    choose sex for a template.
  - Taking a template spends the dead body's policy (`forfeit_policy`, #3667)
    on both doors.
- The web door (`CharacterCreateView.get`) offers respawn before it checks
  the sleeve limit, so respawn works at any number of active sleeves.

### Character Attributes Set

**From telnet character creation (`first_char_finalize`):**

- `key` — `build_name_from_death_count(f"{first_name} {last_name}", 1)`,
  giving `"First Last I"`.
- `sex` — `"male"`, `"female"` or `"ambiguous"`.
- `height`, `build` — the menu choices (`world.identity`).
- `hair_color`, `hair_style` — `None` when Bald.
- `grit`, `resonance`, `intellect`, `motorics` (AttributeProperty) — each
  1-150.
- Manifest designation via `ensure_manifest(char)` (#3033).
- `unarchive_character()` — the archive attribute and the sleeve tag.
- `db.stack_id` — a new `uuid4` string, the unique consciousness ID.
- `db.decant_announce_pending = True` — the decant scene plays on first
  puppet.
- `db.original_creation` and `db.current_sleeve_birth` — Unix timestamps of
  creation.
- `death_count = 1` (the AttributeProperty default).
- The character is moved out of the Limbo staging room to
  `get_spawn_location()` (quietly) before the puppet.

**From flash clone (`create_flash_clone`):**

Inherited from the old character:
- `grit`, `resonance`, `intellect`, `motorics`.
- `sex`.
- `db.desc`.
- `longdesc` (a dictionary copy), only when the source has longdescs.
- `db.skintone`, only when the source has one. These two are conditional
  because an unconditional copy would write `None` over state the new body
  was just seeded with.
- `death_count` (already incremented at death).
- `db.stack_id` — the same consciousness; a new uuid when the old body has
  none.
- `db.previous_clone_dbref` — the old character's dbref.
- `db.species`, with a rebuilt `MedicalState`, when the old species differs
  from the new body's: the body you get back is the body you had; without it
  a bioroid would come back human.
- `sleeve_uid` — same body, same physical identity.
- `height`, `build`, `hair_color`, `hair_style`, `sdesc_keyword` — each only
  when the source has one.
- The recognition imprint, via `world.imprint` (#2188).
- The manifest designation, via
  `ensure_manifest(char, inherit_from=old_character)`; a service record is
  not reissued on resleeve (#3033).
- `db.decant_announce_pending`.

New for this sleeve:
- `key` — `build_name_from_death_count(old.key, death_count)`, a Roman
  numeral.
- `db.current_sleeve_birth` — now.
- `unarchive_character()`.

## Web Form Requirements

The web first-character form is `CharacterForm` in `web/website/forms.py`, an
extension of Evennia's `CharacterForm`. Its fields (`Meta.fields`) are
`first_name`, `last_name`, `sex`, `height`, `build`, `desc`, `grit`,
`resonance`, `intellect`, `motorics`. There is no `db_key` field: the key is
composed from the two name fields.

### GRIM

- `grit`, `resonance`, `intellect`, `motorics` — IntegerField, min 1, max
  150, initial 75 each. Labels and help text:
  - Grit: "Physical power and endurance (1-150)"
  - Resonance: "Psychic affinity and willpower (1-150)"
  - Intellect: "Logic, memory, and reasoning (1-150)"
  - Motorics: "Dexterity, reflexes, and coordination (1-150)"
- Validation (in `clean()`): each stat 1-150, and the total must equal 300.
  Otherwise the form reads: "GRIM stats must total exactly 300 points.
  Current total: {total} points."
- The template's JavaScript shows a live point total as the player types.

### Name Structure

- `first_name`, `last_name` — CharField, max 30, required, pattern
  validation (`clean_first_name()` / `clean_last_name()`).
- Validation:
  - 2-30 characters each, and **first and last together at most 30** — the
    shared `validate_name` caps the combined name; both doors say so (#3436).
  - Regex: `^[a-zA-Z][a-zA-Z\-']*[a-zA-Z]$`
  - `clean()` checks uniqueness of the full name.
- The key is composed in `CharacterCreateView.form_valid` through the shared
  numeral helper: `build_name_from_death_count(f"{first_name} {last_name}", 1)`
  gives `"First Last I"`, as on every other creation path. A key composed
  without the helper has no "I", and its first death would rename the clone
  straight to "First Last II" (#2449).

### Sex/Gender

- `sex` — ChoiceField: "male", "female", "ambiguous", set on the character
  as `character.sex`.

### Height and Build

- `height` and `build` — ChoiceFields from `HEIGHTS` / `BUILDS` in
  `world.identity`, initial "average" (#2449).

### Phase 5: Advanced (Optional) — 📋 UNBUILT (not decided)

The web form has no `skintone` or `longdesc` field.

**Additional fields:**
- `skintone` (CharField/ChoiceField)
- `longdesc` (TextField/FormSet for detailed description)

## Web Character Creation (`CharacterCreateView.form_valid`)

`CharacterCreateView` (`web/website/views/characters.py`) uses
`CharacterForm`. When a valid first-character form is submitted,
`form_valid`:

1. Runs a slot check first: `account.active_sleeves` against
   `settings.MAX_NR_CHARACTERS`.
2. Reads `first_name` and `last_name` and composes the key with
   `build_name_from_death_count(..., 1)`.
3. Creates the character in Limbo (#2) as a staging area. The spawn room is
   resolved separately (`settings.START_LOCATION`), stashed on
   `db.prelogout_location`, and `location` is nulled so the sleeve is
   invisible until first puppet.
4. Sets the four GRIM stats, `sex`, `height`/`build` (#2449),
   `db.stack_id` / `db.original_creation` / `db.current_sleeve_birth`,
   `unarchive_character()`, `db.decant_announce_pending` (so a first-time web
   player gets the decant scene rather than the routine re-login line) and
   `ensure_manifest(character)` (#3033).

If `self.typeclass.create` returns errors, each goes to `messages.error`
(Evennia colour codes stripped first) and the form is shown again
(`form_invalid`). If no character comes back, the page reads "Character
creation failed."

## Web Respawn

- `CharacterCreateView.get` asks `account.respawn_candidate()` (#2615). When
  it returns a dead sleeve, `show_respawn_interface` renders
  `website/character_respawn_create.html` with three
  `generate_random_template()` cards (kept in the Django session for the
  POST) and the flash-clone card, or the refusal in its place.
- `CharacterCreateView.post` sends a submission carrying `sleeve_choice` to
  `handle_respawn_submission`, which calls `create_flash_clone` or
  `create_character_from_template`.
- See `WEB_RESPAWN_CHARACTER_CREATION_SPEC.md`.

## Templates and URLs

- Template overrides: `character_form.html`, `_menu.html`. The pages use the
  "Decant Sleeve" / "Manage Sleeves" terminology.
- `web/website/urls.py` routes `characters/create/` (name
  `character-create`) to the custom `CharacterCreateView`, ahead of Evennia's
  routes. The same file also overrides, ahead of Evennia's routes, the
  manage, delete (which archives), detail and update character pages, the
  staff-only character and channel lists, and several site pages
  (registration, logout, forum SSO, the atlas and others).

## Notes

- **Code reuse:** Import functions from `commands/charcreate.py` where
  possible.
- **Consistency:** Web and telnet should create identical character states.
  - **One axis diverges: HAIR (2026-09-11, #2449).** The telnet door asks for
    hair colour and style (`first_char_hair_color`, `first_char_hair_style`
    in `commands/charcreate.py`) and stamps them (`first_char_finalize`); the
    respawn templates roll them (`generate_random_template`, applied in
    `create_character_from_template`); a flash clone inherits them
    (`create_flash_clone`). The web form asks height and build (#2449), so
    hair is the only identity axis it leaves out. The web first-character
    form asks for neither hair field (`CharacterForm` in
    `web/website/forms.py`) and `CharacterCreateView.form_valid` sets
    neither, so both stay `None` — which `format_hair_feature` in
    `world/identity.py` reads as **bald**, so the sdesc has no distinguishing
    feature unless something is wielded or worn (hair is step 3 of the chain
    in `get_distinguishing_feature`, `typeclasses/characters.py`). Nothing
    sets either attribute on an existing player character afterwards — the
    only other writers in the repo are NPC generators and builder tools — so
    it is permanent. **Already named, never fixed:** issue #2449 listed
    `hair_color`/`hair_style` alongside `height`/`build` in its own trace
    ("get_distinguishing_feature has no hair to report") and closed with only
    height/build addressed, so this wants a reopen or a successor issue
    citing #2449 — not a first filing. Owner call first on whether the web
    door is deliberately a reduced chargen (see Not decided).
  - **`create_character_from_template` stamps no `db.stack_id`** (nor
    `db.original_creation` or `db.current_sleeve_birth`), unlike every other
    creation path (`first_char_finalize`, `create_flash_clone`,
    `CharacterCreateView.form_valid`). Both doors use it for a template
    respawn, so the gap is symmetric rather than a parity break. **Recorded,
    not re-opened:** #2449 investigated this exact gap and rejected it —
    `db.stack_id` has no gameplay reader (its readers are propagation inside
    `create_flash_clone`, the `ensure_manifest` docstring in
    `world/manifest.py`, and the one-off
    `scripts/builds/164_backfill_the_last_sleeves.py`), so no player can
    observe it. It stays written down here because manifest lineage is
    defined in terms of it and a future reader will otherwise rediscover the
    gap and re-file it. Birth date does have a fallback (`_sleeve_born` in
    `world/death_records.py`); stack_id has none.
- **Safety:** Always test on development before production deployment.

## Unbuilt

- 📋 UNBUILT (not decided) — `skintone` and `longdesc` fields on the web form
  (see Phase 5 above).

## Not decided

- Is the web door deliberately a reduced chargen? Owner call first, before
  #2449 is reopened or a successor issue citing it is filed (see Notes,
  HAIR).

## Related

- [`WEB_RESPAWN_CHARACTER_CREATION_SPEC.md`](WEB_RESPAWN_CHARACTER_CREATION_SPEC.md)
  — the respawn interface on the web door.
- `commands/charcreate.py` — the telnet door, `create_flash_clone`,
  `create_character_from_template`, `generate_random_template`,
  `validate_name`.
- `web/website/forms.py` (`CharacterForm`), `web/website/views/characters.py`
  (`CharacterCreateView`), `web/website/urls.py`.
