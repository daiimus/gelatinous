# Web Character Creation Alignment Spec

> **Status:** ✅ **SHIPPED** — Phases 1–4 and the respawn interface; the Phase 5 skintone/longdesc form fields are 📋 UNBUILT (not decided). ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 13 claim(s) false, annotated inline**.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - The Phase 5 testing checklist is entirely unchecked, contradicting both this document's header and the code. The checklist is stale; the header is right.

## Overview

This document defines how the web-based character creation should align with the telnet-based character creation system in `commands/charcreate.py`.

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
- Option 1: Flash clone (copy all stats from previous character) — **since
  2026-09-25 (#3667) only when the dead body holds its own sleeve policy;**
  otherwise both doors show the refusal instead of the card.
  `create_flash_clone` asks the gate again when it builds the clone. It
  raises `PolicyRefused` if `flash_clone_refusal` objects, if the body still
  has its `death_progression` script (still on the table), or if another
  door has just taken the policy (`take_policy`). If the build then fails
  part-way, the new body is deleted and the policy is put back
  (`restore_policy`). After a good build an ordinary policy is spent and a
  standing one is re-issued in the new body's name (`renew_perpetual`).
  The web door (`handle_respawn_submission`) catches `PolicyRefused` and
  sends the player back to the sleeve choice with the refusal text.
- Option 2: Choose from 3 random templates (300-point GRIM distributions)
- Each template (`generate_random_template`) rolls its own name, sex,
  height, build and hair (about 15% come out bald); the player does not
  choose sex for a template. Taking a template spends the dead body's
  policy (`forfeit_policy`, #3667) on both doors.
- The web door (`CharacterCreateView.get`) offers respawn before it checks
  the sleeve limit, so respawn works at any number of active sleeves.

### Character Attributes Set

**From telnet character creation (`first_char_finalize`):**

```python
# Core identity
char.key = build_name_from_death_count(f"{first_name} {last_name}", 1)  # "First Last I"
char.sex = sex                           # "male", "female", or "ambiguous"
char.height = height                     # menu choices (world.identity)
char.build = build
char.hair_color = hair_color             # None when Bald
char.hair_style = hair_style             # None when Bald

# GRIM stats (AttributeProperty)
char.grit = grit                         # 1-150
char.resonance = resonance               # 1-150
char.intellect = intellect               # 1-150
char.motorics = motorics                 # 1-150

# Manifest designation (#3033)
ensure_manifest(char)

# Stack/clone tracking
char.unarchive_character()               # attribute + sleeve tag
char.db.stack_id = str(uuid.uuid4())     # Unique consciousness ID
char.db.decant_announce_pending = True   # decant scene on first puppet
char.db.original_creation = time.time()  # Unix timestamp
char.db.current_sleeve_birth = time.time() # Unix timestamp
char.death_count = 1                     # AttributeProperty default

# Out of the Limbo staging room before the puppet
char.move_to(get_spawn_location(), quiet=True)
```

**From flash clone (`create_flash_clone`):**

```python
# Inherited from old character
char.grit = old_character.grit
char.resonance = old_character.resonance
char.intellect = old_character.intellect
char.motorics = old_character.motorics
char.sex = old_character.sex
char.db.desc = old_character.db.desc
char.longdesc = old_character.longdesc   # Dictionary copy
char.db.skintone = old_character.db.skintone
char.death_count = old_character.death_count  # Already incremented at death
char.db.stack_id = old_character.db.stack_id  # Same consciousness
char.db.previous_clone_dbref = old_character.dbref

# New for this sleeve
char.key = build_name_from_death_count(old.key, death_count)  # Roman numeral
char.db.current_sleeve_birth = time.time()
char.db.archived = False

# Corrected 2026-09-11 — see `create_flash_clone` in commands/charcreate.py:
#   char.unarchive_character()   # not a db.archived assignment
#   char.db.skintone is copied only when the source HAS one,
#     and char.longdesc only when the source HAS longdescs —
#     the unconditional forms above would write None over state the new
#     body was just seeded with
# And the clone inherits far more than the block above lists:
#   char.db.species + a REBUILT MedicalState, when the old species differs
#     from the new body's — the body you get
#     back is the body you had; without it a bioroid came back human
#   char.sleeve_uid — same body, same physical identity
#   char.height / char.build / char.hair_color / char.hair_style /
#     char.sdesc_keyword (each only when the source has one)
#   the recognition imprint, via world.imprint (#2188)
#   the manifest designation, via ensure_manifest(char,
#     inherit_from=old_character) — a service record is not
#     reissued on resleeve (#3033)
#   char.db.stack_id gets a new uuid when the old body has none
#   char.db.decant_announce_pending
```

## Web Form Requirements

> **Status: Form COMPLETE.** Phases 1–4 were built incrementally and are now
> live. The shipped `CharacterForm` in `web/website/forms.py` includes the split
> name fields (`first_name`, `last_name`), `sex`, `height`, `build`, all four GRIM stats, and the
> full 300-point + name-uniqueness validation. The respawn interface
> (templates + flash clone) also **shipped and is deployed to production**
> — see `WEB_RESPAWN_CHARACTER_CREATION_SPEC.md`. The per-phase breakdown
> is retained below as the historical implementation plan.

### Phase 1: Minimal Form (COMPLETE)

**Extend Evennia's CharacterForm with:**
- `grit` (IntegerField, min=1, max=150, initial=75)

**Keep from Evennia default:**
- `db_key` (CharField) - Character name
- `desc` (CharField/TextField) - Description

**Validation:**
- No GRIM total validation yet (just testing single field)

### Phase 2: Basic GRIM Form (COMPLETE)

**Add all GRIM fields:**
- `grit` (IntegerField, min=1, max=150, initial=75)
- `resonance` (IntegerField, min=1, max=150, initial=75)
- `intellect` (IntegerField, min=1, max=150, initial=75)
- `motorics` (IntegerField, min=1, max=150, initial=75)

**Validation (in `clean()`):**
- Total must equal 300
- Each stat 1-150

### Phase 3: Name Structure (COMPLETE)

**Split name into fields:**
- `first_name` (CharField, max=30, required, pattern validation)
- `last_name` (CharField, max=30, required, pattern validation)

**Combine to create `db_key`:**
```python
charname = f"{first_name} {last_name}"
```

> **Correction 2026-09-11:** this recipe was the #2449 bug. The live view
> composes the key through the shared numeral helper in
> `CharacterCreateView.form_valid` (`web/website/views/characters.py`):
> `charname = build_name_from_death_count(f"{first_name} {last_name}", 1)`
> → `"First Last I"`, with the reasoning kept in the comment above it. This was the only creation site in the codebase that
> skipped the helper, so a web sleeve was keyed without an "I" and its
> first death renamed the clone straight to "First Last II".

**Validation:**
- 2-30 characters each, and **first and last together at most 30** — the shared `validate_name` caps the combined name; both doors now say so (#3436)
- Regex: `^[a-zA-Z][a-zA-Z\-']*[a-zA-Z]$`
- Check uniqueness of full name

### Phase 4: Sex/Gender (COMPLETE)

**Add field:**
- `sex` (ChoiceField: "male", "female", "ambiguous")

**Set on character:**
```python
character.sex = form.cleaned_data['sex']
```

### Phase 5: Advanced (Optional) — 📋 UNBUILT (not decided)

The web form has no `skintone` or `longdesc` field.

**Additional fields:**
- `skintone` (CharField/ChoiceField)
- `longdesc` (TextField/FormSet for detailed description)

## Implementation Strategy

### Current State
✅ Template overrides working (`character_form.html`, `_menu.html`)
✅ "Decant Sleeve" / "Manage Sleeves" terminology applied
✅ Full GRIM + name/sex form **implemented** in `web/website/forms.py`
   (class `CharacterForm`): `first_name`, `last_name`, `sex`, `height`, `build`, `desc`, and all
   four GRIM stats (`grit`, `resonance`, `intellect`, `motorics`)
✅ `clean()` enforces the 300-point GRIM budget and full-name uniqueness;
   `clean_first_name()`/`clean_last_name()` enforce the name regex
✅ Custom `CharacterCreateView` wired via `web/website/urls.py`
   (`characters/create/`)

### Completed Work

Phases 1–4 below are **done**. The live form already collects name, sex, and the
full GRIM distribution with server-side validation:

**Step 1: Single GRIM Field Test — DONE**
- `web/website/forms.py` created
- `CharacterForm` extends Evennia's `CharacterForm`
- `character.grit` set correctly from the form

**Step 2: Full GRIM Fields — DONE**
- `resonance`, `intellect`, `motorics` added
- `clean()` validates the 300-point total
- Live point calculator wired in the template's JavaScript

**Step 3: Name Structure — DONE**
- `first_name`, `last_name` fields added with regex + length validation
- Names combined into the character key; uniqueness checked in `clean()`

**Step 4: Sex Field — DONE**
- `sex` ChoiceField (male/female/ambiguous) added and applied to the character

### Remaining Work

**Step 5: Respawn Interface**
- `CharacterCreateView.get` asks `account.respawn_candidate()` (#2615);
  when it returns a dead sleeve, `show_respawn_interface` renders
  `website/character_respawn_create.html` with three
  `generate_random_template()` cards (kept in the Django session for the
  POST) and the flash-clone card, or the refusal in its place
- `CharacterCreateView.post` sends a submission carrying `sleeve_choice` to
  `handle_respawn_submission`, which calls `create_flash_clone` or
  `create_character_from_template`
- See `WEB_RESPAWN_CHARACTER_CREATION_SPEC.md`

## Form Example (as built)

The form below reflects the live `web/website/forms.py`. The `first_name`,
`last_name`, `sex`, `height` and `build` field definitions are omitted here for brevity (see the
source), but the `Meta.fields` tuple matches the real code exactly.

```python
# web/website/forms.py
from django import forms
from evennia.web.website.forms import CharacterForm as EvenniaCharacterForm

class CharacterForm(EvenniaCharacterForm):
    """Extended character form with GRIM stats, name structure, and sex."""

    # first_name / last_name (CharField, regex + length validated),
    # sex (ChoiceField) and height / build (ChoiceFields from
    # world.identity HEIGHTS / BUILDS, initial "average") are also
    # defined here — omitted for brevity.

    grit = forms.IntegerField(
        min_value=1, max_value=150, initial=75,
        label="Grit",
        help_text="Physical power and endurance (1-150)",
        widget=forms.NumberInput(attrs={'class': 'form-control grim-stat'})
    )
    
    resonance = forms.IntegerField(
        min_value=1, max_value=150, initial=75,
        label="Resonance",
        help_text="Psychic affinity and willpower (1-150)",
        widget=forms.NumberInput(attrs={'class': 'form-control grim-stat'})
    )
    
    intellect = forms.IntegerField(
        min_value=1, max_value=150, initial=75,
        label="Intellect",
        help_text="Logic, memory, and reasoning (1-150)",
        widget=forms.NumberInput(attrs={'class': 'form-control grim-stat'})
    )
    
    motorics = forms.IntegerField(
        min_value=1, max_value=150, initial=75,
        label="Motorics",
        help_text="Dexterity, reflexes, and coordination (1-150)",
        widget=forms.NumberInput(attrs={'class': 'form-control grim-stat'})
    )
    
    class Meta(EvenniaCharacterForm.Meta):
        # Extend parent's fields with our custom fields
        fields = ('first_name', 'last_name', 'sex', 'height', 'build', 'desc',
                  'grit', 'resonance', 'intellect', 'motorics')
    
    def clean(self):
        """Validate GRIM total equals 300 and the full name is unique."""
        cleaned_data = super().clean()
        
        grit = cleaned_data.get('grit', 0)
        resonance = cleaned_data.get('resonance', 0)
        intellect = cleaned_data.get('intellect', 0)
        motorics = cleaned_data.get('motorics', 0)
        
        total = grit + resonance + intellect + motorics
        
        if total != 300:
            raise forms.ValidationError(
                f"GRIM stats must total exactly 300 points. Current total: {total} points."
            )
        
        return cleaned_data
```

## View Example (as built)

> **Correction 2026-09-11 — this example is no longer "as built".** The
> real `form_valid` is `CharacterCreateView.form_valid` in
> `web/website/views/characters.py`. Differences
> that matter:
> - `charname = form.cleaned_data['db_key']` cannot work: `db_key` is not
>   among the live form's fields (`CharacterForm.Meta.fields` in
>   `web/website/forms.py`), and the
>   create template renders no such input, so the key is absent from
>   `cleaned_data` and the subscript raises `KeyError`. The view reads
>   `first_name` and `last_name` and composes the key via
>   `build_name_from_death_count(..., 1)`.
> - the character is created in Limbo (#2) as a staging area, with the
>   spawn room resolved separately (`settings.START_LOCATION`), stashed on
>   `db.prelogout_location` and `location` nulled so the sleeve is
>   invisible until first puppet.
> - besides the four GRIM stats it also sets `sex`,
>   `height`/`build` (#2449), `db.stack_id` /
>   `db.original_creation` / `db.current_sleeve_birth`,
>   `unarchive_character()`, `db.decant_announce_pending`
>   (so a first-time web player gets the decant scene rather than
>   the routine re-login line) and `ensure_manifest(character)`
>   (#3033).
> - a slot check runs first (`account.active_sleeves` vs
>   `settings.MAX_NR_CHARACTERS`), and Evennia colour codes are stripped
>   from errors before they reach a web page.
>
> Retained below as the shape of the override, which is still accurate.

```python
# web/website/views/characters.py
from django.contrib import messages
from django.http import HttpResponseRedirect
from evennia.web.website.views.characters import CharacterCreateView as EvenniaCharacterCreateView
from web.website import forms

class CharacterCreateView(EvenniaCharacterCreateView):
    """Extended character creation with GRIM stats."""
    
    form_class = forms.CharacterForm
    
    def form_valid(self, form):
        """Handle character creation with GRIM stats."""
        account = self.request.user
        
        # Extract form data
        charname = form.cleaned_data['db_key']
        description = form.cleaned_data.get('desc', '')
        
        # Create character (Evennia pattern)
        character, errors = self.typeclass.create(
            charname, account, description=description
        )
        
        if errors:
            [messages.error(self.request, x) for x in errors]
            return self.form_invalid(form)
        
        if character:
            # Set GRIM stats
            character.grit = form.cleaned_data['grit']
            character.resonance = form.cleaned_data['resonance']
            character.intellect = form.cleaned_data['intellect']
            character.motorics = form.cleaned_data['motorics']
            
            messages.success(
                self.request,
                f"Character '{character.name}' created with GRIM stats!"
            )
            return HttpResponseRedirect(self.success_url)
        else:
            messages.error(self.request, "Character creation failed.")
            return self.form_invalid(form)
```

## URL Override (excerpt)

The real `web/website/urls.py` also overrides, ahead of Evennia's routes,
the manage, delete (which archives), detail and update character pages,
the staff-only character and channel lists, and several site pages
(registration, logout, forum SSO, the atlas and others). Only the create
route is shown here.

```python
# web/website/urls.py
from django.urls import path
from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns
from web.website.views.characters import CharacterCreateView

urlpatterns = [
    path("characters/create/", CharacterCreateView.as_view(), name="character-create"),
]

urlpatterns = urlpatterns + evennia_website_urlpatterns
```

## Testing Checklist

### Phase 1 (Single Field) — COMPLETE
- [x] Form displays with grit field
- [x] Can enter value 1-150
- [x] Value is saved to `character.grit`
- [x] Can retrieve value with `character.grit`

### Phase 2 (Full GRIM) — COMPLETE
- [x] All four GRIM fields appear
- [x] JavaScript calculator shows total
- [x] Cannot submit if total ≠ 300
- [x] All four stats saved correctly
- [x] Can create multiple characters with different distributions

### Phase 3 (Name Structure) — COMPLETE
- [x] First/last name fields appear
- [x] Name validation works (regex, length)
- [x] Names combined into `character.key`
- [x] Uniqueness check works

### Phase 4 (Sex) — COMPLETE
- [x] Sex dropdown appears with 3 options
- [x] Selection saved to `character.sex`
- [x] Gender property returns correct value

### Phase 5 (Respawn)

> **2026-09-11:** still unchecked, and still stale — the respawn code is
> live on both doors (see the note at §"Remaining Work"). Left unchecked
> rather than ticked because no one has recorded playing these five
> through, and reading the code is not the same evidence as walking the
> flow in the live game; whoever does that should tick them then.

- [ ] Flash clone option appears for accounts with dead characters (insured deaths only since #3667)
- [ ] Templates display correctly
- [ ] Flash clone preserves all attributes
- [ ] Roman numeral increments correctly
- [ ] Death count carries forward

## Notes

- **Incremental approach:** Each phase builds on previous, with testing at each step
- **Code reuse:** Import functions from `commands/charcreate.py` where possible
- **Consistency:** Web and telnet should create identical character states
  - **2026-09-11 — one axis still diverges: HAIR.** The telnet door asks
    for hair colour and style (`first_char_hair_color`,
    `first_char_hair_style` in `commands/charcreate.py`) and stamps them
    (`first_char_finalize`); the respawn templates roll them
    (`generate_random_template`, applied in
    `create_character_from_template`); a flash clone inherits them
    (`create_flash_clone`). Since #2449 the web form asks height and
    build, so hair is the only identity axis it still leaves out. The web
    first-character form asks for neither hair field (`CharacterForm` in
    `web/website/forms.py`) and `CharacterCreateView.form_valid` sets
    neither, so both stay `None` — which `format_hair_feature` in
    `world/identity.py` reads as **bald**, so the sdesc has no
    distinguishing feature unless something is wielded or worn (hair is
    step 3 of the chain in `get_distinguishing_feature`,
    `typeclasses/characters.py`). Nothing sets either
    attribute on an existing player character afterwards — the only other
    writers in the repo are NPC generators and builder tools — so it is
    permanent. **Already named, never fixed:** issue #2449 listed
    `hair_color`/`hair_style` alongside `height`/`build` in its own trace
    ("get_distinguishing_feature has no hair to report") and closed with
    only height/build addressed, so this wants a reopen or a successor
    issue citing #2449 — not a first filing. Owner call first on whether
    the web door is deliberately a reduced chargen.
  - **2026-09-11 — `create_character_from_template` stamps no
    `db.stack_id`** (nor `db.original_creation` or
    `db.current_sleeve_birth`), unlike every other creation path
    (`first_char_finalize`, `create_flash_clone`,
    `CharacterCreateView.form_valid`). Both doors use it for a
    template respawn, so the gap is symmetric rather than a parity break.
    **Recorded, not re-opened:** #2449 investigated this exact gap and
    rejected it — `db.stack_id` has no gameplay reader (today: propagation
    inside `create_flash_clone`, the `ensure_manifest` docstring in
    `world/manifest.py`, and the one-off
    `scripts/builds/164_backfill_the_last_sleeves.py`),
    so no player can observe it. It stays written down here because
    manifest lineage is defined in terms of it and a future reader will
    otherwise rediscover the gap and re-file it. Birth date does have a
    fallback (`_sleeve_born` in `world/death_records.py`); stack_id has none.
- **Safety:** Always test on development before production deployment
