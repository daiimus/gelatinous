# Web-Based Respawn Character Creation Specification

## Overview

The website's "Decant Sleeve" page gives a player the same respawn choice the telnet decant menu gives: three rolled templates and, when the dead body is insured, a flash clone. With no sleeve to respawn from, the same page is the first-character form with manual GRIM allocation. The page is `CharacterCreateView` in `web/website/views/characters.py`; it reuses the telnet code in `commands/charcreate.py` (`generate_random_template`, `create_character_from_template`, `create_flash_clone`). Sleeve policies and the flash-clone gate are specified in `specs/SLEEVE_INSURANCE_SPEC.md`.

## The two doors

**Telnet** (`commands/charcreate.py`):
- **First character**: custom stat allocation, 300 points across GRIM.
- **Respawn**: an EvMenu with 3 random templates and the flash clone option (or its refusal, #3667).
- **Confirm**: the confirm node (`respawn_confirm_template`) shows the template's rolled sex and offers only decant / back (#3358, owner ruling A).

**Web** (`web/website/views/characters.py`):
- **Respawn**: when `account.respawn_candidate()` returns an archived sleeve, the page shows three rolled templates and the flash clone card (or its refusal, #3667).
- **First character**: otherwise `CharacterCreateView.get` checks the active-sleeve limit, then shows the manual GRIM form.

## The Decant Sleeve page (GET)

`CharacterCreateView.get` chooses the flow by asking `account.respawn_candidate() is not None`.

- `Account.respawn_candidate` (typeclasses/accounts.py) returns `last_character` only when that sleeve is ARCHIVED. When the attribute points at a living or a deleted sleeve it clears the attribute and returns None (#2615). Both doors use it, so they agree about what is respawnable.
- **Respawn branch** (`show_respawn_interface`):
  - rolls 3 templates with `generate_random_template()` and stores them in the Django session for the POST;
  - passes the templates, the old character, `flash_clone_name` and `flash_clone_refusal` to `web/templates/website/character_respawn_create.html`;
  - heads the page "Your previous sleeve has been archived. Select a new sleeve to decant into.";
  - shows one card per template: name, its rolled sex, and numeric GRIM;
  - shows the flash clone card: the name the clone wakes as (with its generation numeral), the old body's sex and GRIM. When the clone is refused, the refusal text replaces the card (see Flash clone);
  - has no sex selection (#3358, ruling A). The only controls are the `sleeve_choice` radios and the Decant Sleeve button.
- **First-character branch**: after the max-character check, the view falls through to the standard form (`super().get(...)`): manual stat allocation, unchanged.

The respawn page is styled to the game's dark dissolution/body-horror aesthetic and works at phone width.

## Templates (`generate_random_template`)

A template is a dict:

```python
{
    'first_name': str,
    'last_name': str,
    'name': str,            # "First Last", for display
    'sex': 'male' | 'female' | 'ambiguous',
    'grit': int,
    'resonance': int,
    'intellect': int,
    'motorics': int,
    'height': str,
    'build': str,
    'hair_color': str | None,
    'hair_style': str | None
}
```

- The sex is rolled first; the first name is drawn from the name bank keyed to that roll.
- GRIM: three stats get 25-100 points each, the fourth gets the rest of 300 (max 150); then the four are shuffled.
- Both hair keys are None about 15% of the time (bald).

## Flash clone

### When it is offered (#3667, sleeve insurance Slice C)

Both doors offer the flash clone only when `world.insurance.flash_clone_refusal(old_body)` is None: the body was archived with reason `death` and holds its own sleeve policy (bought alive at the Thawn-Harrison lobby terminal). Otherwise the card gives way to the refusal text. A POST that reaches `create_flash_clone` anyway gets `PolicyRefused`, which the view shows as a message. A shelved body (web archive, reason `manual`) is never cloned back. See `specs/SLEEVE_INSURANCE_SPEC.md`.

### What a clone inherits

> **Owner ruling 2026-09-14:** a flash clone inherits GRIM, appearance, sex and imprint -- **not augments**. Chrome stays on the corpse; the clone's medical state is rebuilt from the species table (`create_flash_clone`). You come back a flesh bag.

`create_flash_clone(account, old_character)`:
- Inherits: GRIM stats, appearance (desc, longdesc), sex, skintone, species (the medical state is rebuilt when it differs from the new body's), `sleeve_uid`, height, build, hair colour and style, sdesc keyword, the imprint (who they knew at the last backup, `world.imprint.restore`), `death_count`, `stack_id` and the manifest designation (`ensure_manifest(..., inherit_from=old_character)`).
- Records the old body in `previous_clone_dbref`.
- Does not inherit augments (ruling above).
- Names the clone with `build_name_from_death_count()` (generation numerals, below). `death_count` is not incremented here; archival already did it.
- Leaves the archived body in `account.characters` (see the comment in `create_flash_clone`); the archived tag keeps it out of the active count.

## Submitting (POST)

The POST carries one field:

```python
{'sleeve_choice': 'template_0' | 'template_1' | 'template_2' | 'flash_clone'}
```

No sex is posted. `CharacterCreateView.post` sends any POST carrying `sleeve_choice` to `handle_respawn_submission`:

- **Template** (`template_0` to `template_2`): the three templates `show_respawn_interface` stored in the session at GET are read back. If they are gone, the player is told the session expired and sent back to the create page. Otherwise `create_character_from_template` makes the sleeve with the sex the template was rolled with (`template.get('sex', 'ambiguous')`; the default only covers a template dict missing the key). Then `world.insurance.forfeit_policy` deletes the dead body's own sleeve policy, a perpetual one included (#3667).
- **Flash clone**: `account.respawn_candidate()` is asked again and `create_flash_clone` is called. It spends an ordinary policy and re-issues a perpetual one in the new body's name (`renew_perpetual`). A `PolicyRefused` shows its text and sends the player back to the choice. The view never sets the clone's sex; `create_flash_clone` inherits it.
- **Both**: the new sleeve is taken off the grid (see "Web-created sleeves stay off the grid"), `last_character` is cleared, the stored templates are dropped from the session, and the player is redirected to Character Management with a success message.

## How a sleeve becomes respawnable

`archive_character()` sets `account.db.last_character = character` and increments `character.death_count`. It finds the owner through `world.ownership.owning_account`, so this holds with no live puppet. A sleeve can be archived by death or from the web; only a death can be flash-cloned (#3667).

## Sex: no selection on either door

Neither door offers a sex choice (#3358, owner ruling A, 2026-09-13). A template sleeve is decanted with the sex `generate_random_template` rolled; a flash clone takes the dead body's sex.

*Overturned intention:* this spec first planned a Male / Female / Ambiguous selector on the respawn page, for templates and flash clones. It was removed from the web page on purpose, because a template rolls its sex first and draws a gendered first name from it, so a selector let the two contradict each other. Ruling A (#3358, 2026-09-13) then removed it from telnet too: no sex selection on either door.

## Generation numerals

- Every sleeve carries a Roman numeral suffix built from `death_count`: the first sleeve renders as `Jorge Jackson I`, the first clone as `Jorge Jackson II`, and so on (issue #50).
- A trailing word is stripped as a generation numeral only when it follows a space, is uppercase, and is exactly the form `int_to_roman` would write (`split_roman_suffix`, `roman_value`, #3359). A name that merely ends in numeral letters is left whole.
- The web Manage Sleeves sort uses the same parser.

## Character limit and superusers

- `at_character_limit` (typeclasses/accounts.py) counts `active_sleeves` (tag-indexed) against `MAX_NR_CHARACTERS`. It drives the "Decant Sleeve" menu item: the item is hidden when the account is at the limit.
- Neither `at_character_limit` nor the web create view's own limit check has a superuser bypass. `Account.check_available_slots` still lets superusers and Developers past the slot limit.
- Reason: superusers are meant for administrative access, not regular play, so a superuser backup account is subject to the same rules as regular players.

## Manage Sleeves

- `CharacterManageView` lists every sleeve on the account, archived ones included, sorted by name and then by generation numeral.
- Each row (`character_manage_list.html`) shows the designation (with numeral), decanted date, retired date (deaths only), status (Archived or Active), and an Archive link on active sleeves.
- No image, no GRIM, no death count (the numeral carries it) and no sex field.

## Stat display

- GRIM is a 1-150 scale on a 300-point budget (`GRIM_MIN = 1` / `GRIM_MAX = 150` in web/website/forms.py, applied to all four stat fields).
- The respawn cards (character_respawn_create.html) and the post-creation success message (`handle_respawn_submission`, `form_valid`) show numeric GRIM.
- Tier words come from `STAT_DESCRIPTORS` (world/combat/constants.py): `@stats` / `score` (commands/CmdCharacter.py) and the web character detail page (`get_stat_descriptor`, called from `OwnerOnlyCharacterDetailView`) show them. See specs/proposals/DESCRIPTIVE_STAT_SYSTEM_SPEC.md.

## Web-created sleeves stay off the grid until first puppet

A character made on the web (first-time or respawn) must not stand in the world as an unpuppeted body, looking like an NPC, before the player first connects. Both web paths (`handle_respawn_submission` and `form_valid` in web/website/views/characters.py) do what Evennia's own unpuppet does.

### Creation
1. The view creates the character in Limbo (#2), the staging room (`form_valid`; `get_start_location` on the respawn paths).
2. It sets `db.prelogout_location` to the START_LOCATION room (Limbo if that lookup fails), then sets `location = None`.
3. The character exists in the database but not in the game world.
4. A `WEB_CHAR_CREATE` line goes to splattercast naming the character, the path (first-time or respawn), and the room it will be restored to on login.

### First login
1. The player connects.
2. The game's own `Account.at_post_login` (typeclasses/accounts.py) puppets the account's single active sleeve; `AUTO_PUPPET_ON_LOGIN` is False. With no active sleeve it starts the telnet decant menu instead, and with several it shows a picker.
3. Evennia's built-in `at_pre_puppet` (`DefaultCharacter`, evennia/objects/objects.py) sees `location is None` and restores the character to `db.prelogout_location` (or home).
4. The character appears in the game world. On this first puppet `Character.at_post_puppet` sees `decant_announce_pending`, plays the decant scene to the room and shows the player the sleeve-policy card; later logins show "{actor} stirs as consciousness returns."

### Later sessions
- **Quit**: `Character.at_post_unpuppet` posts an in-fiction exit line to the room, stands the body up, stores `prelogout_location` and sets location to None.
- **Login**: the character is restored from the None location by `at_pre_puppet`, as above.

### NPCs and player characters
- NPCs (made with `@spawnnpc`) are never puppeted, have no session and no account, and always stand in a room. This mechanism does not touch them.
- Web-created player characters have no session until login, sit at `location = None` until then, and are restored to a room on first puppet: the same mechanics as quit/disconnect.

### Why `location = None`
- It is Evennia's standard way to keep an unpuppeted player character out of the world, so restoration needs no custom hook: Evennia's own `at_pre_puppet` does it (the game's `at_post_puppet` / `at_post_unpuppet` overrides change only the room lines and posture).
- It needs no special case for NPCs.
- Rejected: leaving the character at START_LOCATION behind a visibility check (needs a custom `access()` override and a way to tell NPCs from player characters); parking it in Limbo (needs special handling on login and extra location management).

## Edge cases

1. **Template generation fails**: see Unbuilt.
2. **No `last_character` but all characters archived**: see Not decided.
3. **`last_character` deleted from the database**: `respawn_candidate()` clears the pointer and the page shows the manual form.
4. **Concurrent creation attempts**: Flash clone: two doors racing for one policy get one body and one refusal (the atomic `take_policy` in `create_flash_clone`). Template: only dropping the stored templates from the session after success stops a second submission.
5. **Invalid sex**: nothing to validate; no sex is submitted on the web respawn path. The `.get('sex', 'ambiguous')` default in `handle_respawn_submission` is the fallback for a template dict missing the key.

## Unbuilt

- **Template generation fails → show an error and fall back to the manual form.** 📋 UNBUILT (no issue; not decided): `show_respawn_interface` does not catch a failure in `generate_random_template`, so the page errors.
- Loading states on form submission. 📋 UNBUILT (no issue)
- Helpful tooltips/descriptions on the respawn page. 📋 UNBUILT (no issue)
- Regenerate templates without a page refresh (AJAX). 📋 UNBUILT (no issue)
- Preview character appearance before decanting. 📋 UNBUILT (no issue)
- A "Randomize All" button for template generation. 📋 UNBUILT (no issue)
- Edit template stats before decanting (within the 300-point limit). 📋 UNBUILT (no issue)
- A character comparison view (side-by-side stats). 📋 UNBUILT (no issue)
- Descriptive stat adjectives (e.g., "Mighty" instead of "5") on the respawn cards and in the decant success message; the web character detail page (`get_stat_descriptor`) and `@stats` already show tier words. 📋 UNBUILT (no issue)

## Not decided

- **No `last_character`, but every character on the account is archived.** The web view treats this as a first character. Telnet login instead points `last_character` at the most recently archived sleeve and offers the respawn menu (`Account.at_post_login`). The two doors differ here; which is wanted is not decided.

## Related documents

- `specs/SLEEVE_INSURANCE_SPEC.md`: sleeve policies, the flash-clone gate, `forfeit_policy`, `renew_perpetual`.
- `specs/proposals/DESCRIPTIVE_STAT_SYSTEM_SPEC.md`: GRIM tier words.
- Evennia `DefaultCharacter` (`evennia/objects/objects.py`): `at_pre_puppet`, `at_post_unpuppet`.
