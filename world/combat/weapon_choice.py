"""One door for "what does this body fight with" (MULTI_WEAPON_COMBAT_SPEC
§4-§5, #3695 slice 1).

Every reader of the wielded weapon comes through here: the swing, the
reach gates, the initiate prose, the aim verbs, the sever verb, the
flee-safety check. They used to disagree (one picked the first held
item, one the highest damage, one asked only whether the first weapon was
ranged), so claws out meant claws swung where they could not reach while
a loaded pistol sat in the other hand.

Rule order, a pure peek (nothing here changes state):

1. Candidates in slot order: deployed natural weapons (each hand's own
   claws), then held items, one option per distinct object (a two-slot
   grip is one option with two slots).
2. Real weapons: if any held item carries the ``("weapon", "type")`` tag,
   untagged held items are dropped (the #516 rule); with nothing tagged,
   only the single highest-damage improvised item stays, so nothing
   rotates a cigarette. Naturals are always real.
3. Range: with a target out of melee reach, ranged options only; with
   none, everything stays so the caller's reach line fires.
4. Natural precedence (owner ruling 2026-10-03, §14 ruling 2): among the
   options that can reach, deployed naturals win outright. At range a
   held pistol fires while the claws stay out; in melee the claws swing
   and the knife waits.
5. Akimbo grouping (§5): options sharing an ``akimbo_family`` become ONE
   option on the lead item's attributes overlaid with the profile for the
   largest count the group covers. One attack, never one per limb.
6. Rotation is slice 2. In slice 1 held weapons keep range-then-max and
   naturals take the first option.
"""
from dataclasses import dataclass, replace

from world.combat.constants import (
    AKIMBO_PROFILE_FIELDS, WEAPON_ATTR_AKIMBO_FAMILY,
    WEAPON_ATTR_AKIMBO_PROFILES, WEAPON_ATTR_HIT_BONUS, WEAPON_TYPE_UNARMED,
)
from world.combat.utils import _in_melee_range, get_weapon_damage


@dataclass(frozen=True)
class WeaponChoice:
    """One attack's worth of weapon. ``items`` in slot order, the lead
    first; ``slots`` the grasping slots it occupies (empty for a natural
    weapon on a non-grasping host, which keeps body-wide manipulation)."""
    items: tuple
    slots: tuple
    damage: int
    hit_bonus: int
    damage_type: object
    weapon_type: str
    is_ranged: bool
    natural: bool

    @property
    def item(self):
        return self.items[0]

    @property
    def akimbo(self) -> bool:
        return len(self.items) > 1


def _db(item, name, default=None):
    value = getattr(getattr(item, "db", None), name, None)
    return default if value is None else value


def _is_ranged(item) -> bool:
    return bool(_db(item, "is_ranged", False))


def _is_real_weapon(item) -> bool:
    tags = getattr(item, "tags", None)
    try:
        return bool(tags is not None and tags.has("weapon", category="type"))
    except Exception:  # noqa: BLE001 — a stub without a tag handler is not a weapon
        return False


def _single(item, slots, natural) -> WeaponChoice:
    return WeaponChoice(
        items=(item,), slots=tuple(slots),
        damage=get_weapon_damage(item, 0),
        hit_bonus=int(_db(item, WEAPON_ATTR_HIT_BONUS, 0) or 0),
        damage_type=_db(item, "damage_type"),
        weapon_type=str(_db(item, "weapon_type") or WEAPON_TYPE_UNARMED),
        is_ranged=_is_ranged(item),
        natural=natural,
    )


def _profiles(item) -> dict:
    """``akimbo_profiles`` with integer counts; a stored key may come back
    as a string."""
    raw = _db(item, WEAPON_ATTR_AKIMBO_PROFILES) or {}
    out = {}
    for key, overrides in dict(raw).items():
        try:
            out[int(key)] = dict(overrides or {})
        except (TypeError, ValueError):
            continue
    return out


def _grouped(members) -> WeaponChoice:
    """``members`` (two or more singles of one family, in slot order)
    become one option: the lead's attributes under the profile for the
    largest count the group covers. Only the profile fields may change;
    anything else a profile says is dropped here."""
    lead = members[0]
    overrides = {k: v for k, v in _profiles(lead.item).get(len(members), {}).items()
                 if k in AKIMBO_PROFILE_FIELDS}
    if "damage" in overrides:
        overrides["damage"] = int(overrides["damage"])
    if "hit_bonus" in overrides:
        overrides["hit_bonus"] = int(overrides["hit_bonus"])
    if "weapon_type" in overrides:
        overrides["weapon_type"] = str(overrides["weapon_type"])
    return replace(lead, items=tuple(m.item for m in members),
                   slots=tuple(s for m in members for s in m.slots), **overrides)


def _group_akimbo(options):
    """Step 5. Members of one family, distinct objects, in slot order; the
    profile for the largest count k with k <= n takes k members as one
    option, leftovers regroup by the same rule or stay single. Options
    without a family pass through in place."""
    out, pending = [], {}
    order = []
    for option in options:
        family = _db(option.item, WEAPON_ATTR_AKIMBO_FAMILY)
        if not family:
            out.append(option)
            continue
        if family not in pending:
            pending[family] = []
            order.append(family)
        pending[family].append(option)
    for family in order:
        members = pending[family]
        while members:
            keys = [k for k in _profiles(members[0].item) if 1 < k <= len(members)]
            if not keys:
                out.append(members.pop(0))
                continue
            k = max(keys)
            out.append(_grouped(members[:k]))
            members = members[k:]
    return out


def _candidates(char):
    """Step 1: deployed naturals (each hand's own object), then held items,
    one option per distinct object."""
    seen, options = set(), []
    hands = getattr(char, "hands", None) or {}
    try:
        from world.medical.augments import get_active_natural_weapons
        naturals = get_active_natural_weapons(char)
    except Exception:  # noqa: BLE001 — a stub without a medical model fights with its hands
        naturals = []
    for container, item in naturals:
        if id(item) in seen:
            continue
        seen.add(id(item))
        slots = (container,) if container in hands else ()
        options.append(_single(item, slots, natural=True))
    held = {}
    for slot, item in hands.items():
        if item is None or id(item) in seen:
            if item is not None and id(item) in held:
                held[id(item)][1].append(slot)      # a two-slot grip
            continue
        seen.add(id(item))
        held[id(item)] = (item, [slot])
    for item, slots in held.values():
        options.append(_single(item, slots, natural=False))
    return options


def _real_weapons(options):
    """Step 2 (#516): tagged weapons shoulder untagged items aside; with
    nothing tagged, one improvised item, the hardest-hitting."""
    naturals = [o for o in options if o.natural]
    held = [o for o in options if not o.natural]
    if not held:
        return naturals
    tagged = [o for o in held if _is_real_weapon(o.item)]
    if tagged:
        return naturals + tagged
    return naturals + [max(held, key=lambda o: o.damage)]


def _in_reach(options, char, target, at_range):
    """Step 3. ``at_range`` asks the question without a target: what would
    fire at range (the aiming peek)."""
    if not at_range and (target is None or _in_melee_range(char, target)):
        return options
    ranged = [o for o in options if o.is_ranged]
    return ranged or options


def weapon_options(char, target=None, *, at_range=False, precedence=True):
    """The ordered wheel of options after every step (§11): what a future
    "k attacks per round" ruling would take the next k of. ``precedence=False``
    leaves step 4 out: every real option that can reach, naturals and held
    alike, for a reader that wants a particular kind of item rather than
    the attack's pick (the sever verb's blade)."""
    options = _in_reach(_real_weapons(_candidates(char)), char, target, at_range)
    if precedence:
        naturals = [o for o in options if o.natural]
        if naturals:
            options = naturals                  # step 4, natural precedence
    return _group_akimbo(options)


def choose_weapon(char, target=None, *, at_range=False):
    """The weapon THIS attack uses, or None when unarmed. Slice 1: a
    natural option takes the first place in the wheel; held weapons keep
    range-then-max. ``at_range=True`` is the aiming peek: the option that
    would fire at range, so the aim, aim-stop and move-while-aiming lines
    name the gun the ranged gate approved, not the claws or the heavier
    blade that would swing in melee."""
    options = weapon_options(char, target, at_range=at_range)
    if not options:
        return None
    if options[0].natural:
        return options[0]
    return max(options, key=lambda o: o.damage)


def has_ranged_option(char) -> bool:
    """Any real option is ranged: the gates that used to ask "is the
    wielded weapon ranged" ask this, so a knife sorting first no longer
    blocks a pistol. The range step cannot change the answer (it keeps
    every option or exactly the ranged ones), so no target is taken."""
    return any(o.is_ranged for o in _real_weapons(_candidates(char)))
