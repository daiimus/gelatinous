"""@spawnmob -- manifest a person, or a body, where you stand.

A human or synthetic spawn is a whole PERSON built the way the colony
builds everyone else: the civilian factory's random archetype for that
species (persona, voice, wardrobe, stock), the shuttle arrival's rolled
personhood (style, traits, designation, skills), ensouled with no home
and no post, and PINNED -- frozen in time until a GM puppets it or a
developer tests against it (owner ruling 2026-09-14). A rat or a bare
robot chassis is a body: species surfaces and the flavor pass, no soul.
``/secbot`` is the production security factory's front door.

There is no hollow-body switch any more. ``/blank`` produced a
Character that behaved like nothing in the live game; every test that
passed on one proved nothing about the game.
"""
from random import choice, randint

from evennia import Command, create_object

from world.identity import RAT_COATS, RAT_SIZES, ROBOT_CHASSIS, ROBOT_FINISHES
from world.identity_utils import msg_room_identity
from world.mob_flavor import apply_random_flavor

#: switch -> species. ``secbot`` is a role, not a species (it is the only
#: switch that changes typeclass), and is handled on its own.
SPECIES_SWITCHES = {
    "human": "human",
    "synth": "synthetic_humanoid",
    "rat": "rat",
    "robot": "robot",
}
VALID_SWITCHES = tuple(SPECIES_SWITCHES) + ("secbot",)
#: species that spawn as a PERSON (soul, persona, wardrobe); the rest are bodies
PERSON_SPECIES = ("human", "synthetic_humanoid")


def roll_stat():
    return randint(1, 3)


def archetypes_for(species):
    """The civilian archetypes a *species* may be spawned as."""
    from world.director.civilians import CIVILIAN_ROLES
    return sorted(role for role, spec in CIVILIAN_ROLES.items()
                  if (spec.get("species") or "human") == species)


def spawn_person(species, location, name=None, role=None):
    """A full person of *species*, pinned where they stand: a random
    civilian archetype for the species (persona, voice, wardrobe,
    stock), rolled personhood, a soul with no home and no post, frozen
    in time. Returns the person, or ``None`` if the species has no
    archetype."""
    from world.director.civilians import spawn_civilian
    from world.souls import ensoul, pin
    from world.souls.population import roll_person
    choices = archetypes_for(species)
    if not choices:
        return None
    role = role if role in choices else choice(choices)
    # Dress in the wings, not on stage: the factory wears its wardrobe
    # through the real `wear` command, which the room would watch ("puts
    # on a…" four times from a stranger nobody has been introduced to).
    # Build in Limbo, then step into the room in one quiet move.
    from django.conf import settings
    from evennia.utils.search import search_object
    wings = search_object(settings.DEFAULT_HOME)
    wings = wings[0] if wings else location
    npc = spawn_civilian(role, wings, drift=False)
    if npc is None:
        return None
    if name:
        npc.key = name
    roll_person(npc)
    ensoul(npc, role=role, home=None, post=None, schedule="day")
    pin(npc)
    npc.home = location
    npc.db.post = location
    if npc.location != location:
        npc.move_to(location, quiet=True, move_hooks=False)
    return npc


def spawn_body(species, location, name=None):
    """A body with no soul -- a rat, or a bare robot chassis. Species
    surfaces through the one helper, then the flavor pass."""
    from world.anatomy import apply_species
    if species == "rat":
        key = name or f"a {choice(RAT_SIZES)} {choice(RAT_COATS)} rat"
    elif species == "robot":
        key = name or f"a {choice(ROBOT_FINISHES)} {choice(ROBOT_CHASSIS)} robot"
    else:
        key = name or f"a {species}"
    mob = create_object(
        typeclass="typeclasses.characters.Character",
        key=key, location=location, home=location,
    )
    mob.db.is_npc = True   # the canonical NPC marker (absence = PC)
    apply_species(mob, species)
    mob.sex = "ambiguous" if species == "robot" else choice(["male", "female"])
    for stat in ("grit", "resonance", "intellect", "motorics"):
        setattr(mob, stat, roll_stat())
    apply_random_flavor(mob)
    return mob


class CmdSpawnMob(Command):
    """
    Manifest a person, or a body, where you stand.

    Usage:
        @spawnmob [<name>]          - a human person (same as /human)
        @spawnmob/human [<name>]
        @spawnmob/synth [<name>]
        @spawnmob/rat [<name>]
        @spawnmob/robot [<name>]
        @spawnmob/secbot [<name>]

    A human or synthetic spawn is a whole person: a random archetype
    for that species (persona, voice, clothes, pockets), rolled
    style, traits and designation, a soul with no home and no job,
    and PINNED -- frozen in time. It talks like anyone but does not
    eat, plan or walk until you ``@unpin`` it. Use it for testing, or
    for a GM to puppet later. Delete it when you are done.

    A rat or a robot is a body: species anatomy and flavor, no soul.
    ``/secbot`` builds a complete security unit through the same
    factory the director's respawn uses.

    The name you give becomes the object's key; people see and target
    the short description the game composes, which is echoed back to
    you on spawn.
    """
    key = "@spawnmob"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Admin"
    #: Declared on the class as well (the #2569 invariants read them
    #: here): an unknown switch is REFUSED, and every species switch is
    #: in the valid set. ``secbot`` selects the robot body via its own
    #: factory.
    VALID_SWITCHES = VALID_SWITCHES
    _SPECIES = {**SPECIES_SWITCHES, "secbot": "robot"}

    def func(self):
        caller = self.caller
        raw_args = (self.args or "").strip()
        species = "human"
        secbot = False
        if raw_args.startswith("/"):
            parts = raw_args[1:].split(None, 1)
            switches = ([s.lower() for s in parts[0].split("/") if s]
                        if parts else [])
            if not switches:
                caller.msg("Usage: @spawnmob[/switch] [<name>]. A bare "
                           "'/' is not a switch.")
                return
            if "blank" in switches:
                caller.msg(
                    "|r/blank is gone.|n Every spawn is a full person now -- "
                    "use /human (or /synth, /rat, /robot, /secbot). "
                    "Nothing was spawned."
                )
                return
            unknown = [sw for sw in switches if sw not in VALID_SWITCHES]
            if unknown:
                caller.msg(
                    f"|rUnrecognised switch(es):|n /{', /'.join(unknown)}. "
                    f"Nothing was spawned. Valid: "
                    f"/{', /'.join(VALID_SWITCHES)}."
                )
                return
            secbot = "secbot" in switches
            for switch in switches:
                if switch in SPECIES_SWITCHES:
                    species = SPECIES_SWITCHES[switch]
            raw_args = parts[1] if len(parts) > 1 else ""
        name = raw_args or None

        if secbot:
            # The SAME factory the director's respawn loop uses, so a
            # hand-spawned unit and an alcove replacement are identical.
            from world.director.population import spawn_secbot
            mob = spawn_secbot(caller.location, name=name)
            caller.msg(f"You manifest {mob.key} into the world.")
            msg_room_identity(
                location=caller.location,
                template="{mob} powers up, status lights climbing to green.",
                char_refs={"mob": mob},
                exclude=[caller],
            )
            return

        if species in PERSON_SPECIES:
            mob = spawn_person(species, caller.location, name=name)
            if mob is None:
                caller.msg(f"|rNo archetype is authored for {species}; nothing was spawned.|n")
                return
            sdesc = mob.get_sdesc() if hasattr(mob, "get_sdesc") else mob.key
            role = (mob.db.soul_role or "").replace("_", " ")
            from world.grammar import get_article
            caller.msg(
                f"You manifest |w{mob.key}|n -- {sdesc}, {get_article(role)} {role} -- "
                f"|ypinned in place|n. @unpin to let them live; delete them when done."
            )
            msg_room_identity(
                location=caller.location,
                template="{mob} flickers into existence, then holds perfectly still.",
                char_refs={"mob": mob},
                exclude=[caller],
            )
            return

        mob = spawn_body(species, caller.location, name=name)
        caller.msg(f"You manifest {mob.key} into the world.")
        msg_room_identity(
            location=caller.location,
            template="{mob} flickers into existence, vacant and twitching.",
            char_refs={"mob": mob},
            exclude=[caller],
        )
