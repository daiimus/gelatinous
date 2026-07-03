from evennia import Command
from evennia import create_object
from random import choice, randint
from world.namebank import (
    FIRST_NAMES_MALE,
    FIRST_NAMES_FEMALE,
    FIRST_NAMES_AMBIGUOUS,
    LAST_NAMES
)
from world.identity import (
    HEIGHTS, BUILDS, HAIR_COLORS, HAIR_STYLES,
    RAT_SIZES, RAT_COATS,
    ROBOT_FINISHES, ROBOT_CHASSIS,
)
from world.identity_utils import msg_room_identity
from world.mob_flavor import apply_random_flavor


def roll_stat():
    return randint(1, 3)


class CmdSpawnMob(Command):
    """
    Spawns an unpossessed Character with randomized identity, stats, and
    flavor (short description, longdescs, look_place).

    Usage:
        @spawnmob [optional name]
        @spawnmob/blank [optional name]
        @spawnmob/rat [optional name]

    If no name is given, one is generated based on randomized sex (for
    humans) or defaulted to a species-flavored key (for non-humans).
    Humanoid mobs receive randomized identity attributes (height, build,
    hair) plus a randomly selected short description, longdescs, and a
    look_place — drawn from ``world/mob_flavor/``.

    Switches:
        /blank   - skip the flavor pass; produces the legacy minimal mob
                   (stock filler description, no longdescs, no look_place)
                   for clean diagnostic spawns.
        /rat     - spawn an anatomically distinct rat instead of a
                   humanoid. Medical state initializes with rat organs;
                   flavor (short desc / longdesc / look_place) dispatches
                   to the rat tables.  See ``SPECIES_AUTHORING.md``.
        /robot   - spawn a humanoid robot. Mechanical chassis (amber
                   hydraulic fluid, non-rotting frame, infection-immune,
                   tougher components); key composes to "a {finish}
                   {chassis} robot"; renders neutral (they/their); flavor
                   dispatches to the robot tables.
        /synth   - spawn a synthetic humanoid (replicant). Passes as
                   human in appearance and flavor, but its medical state
                   uses the synthetic anatomy (cobalt fluid, non-rotting,
                   infection-immune).
        /secbot  - spawn a complete security unit: a robot wired for
                   duty — ``role=security`` (answers dispatch, scans
                   BOLOs, syncs intel) on the LLMNpc typeclass with the
                   stock security persona seeded and ``llm_driven`` on,
                   so it also *talks* like a municipal machine.
    """

    key = "@spawnmob"
    locks = "cmd:perm(Builders) or perm(Developers)"

    def func(self):
        caller = self.caller

        # Parse switches
        raw_args = self.args.strip()
        blank = False
        secbot = False
        species = "human"
        if raw_args.startswith('/'):
            parts = raw_args[1:].split(None, 1)
            if parts:
                switches = [s.lower() for s in parts[0].split('/') if s]
                if "blank" in switches:
                    blank = True
                if "rat" in switches:
                    species = "rat"
                if "robot" in switches:
                    species = "robot"
                if "synth" in switches:
                    species = "synthetic_humanoid"
                if "secbot" in switches:
                    secbot = True
                    species = "robot"
                raw_args = parts[1] if len(parts) > 1 else ""

        # Assign sex with chance of ambiguity
        sex = choice(["male", "female"])
        if randint(1, 10) <= 2:  # 20% chance to use ambiguous
            sex = "ambiguous"
        if species == "robot":
            sex = "ambiguous"  # machines render neutral (they/their)

        # Name: humans pull from the name banks; non-humans compose
        # a rich species-flavored sdesc key (a rat gets a size + coat
        # pair like "a wiry brown rat" rather than the bare "a rat").
        # See world.identity.RAT_SIZES / RAT_COATS.
        if species in ("human", "synthetic_humanoid"):
            # A synthetic passes as human — same name banks and identity.
            if sex == "male":
                first = choice(FIRST_NAMES_MALE)
            elif sex == "female":
                first = choice(FIRST_NAMES_FEMALE)
            else:
                first = choice(FIRST_NAMES_AMBIGUOUS)
            last = choice(LAST_NAMES)
            mob_name = raw_args or f"{first} {last}"
        elif species == "rat":
            mob_name = raw_args or (
                f"a {choice(RAT_SIZES)} {choice(RAT_COATS)} rat"
            )
        elif species == "robot":
            mob_name = raw_args or (
                f"a {choice(ROBOT_FINISHES)} {choice(ROBOT_CHASSIS)} robot"
            )
        else:
            mob_name = raw_args or f"a {species}"

        # /secbot delegates wholesale to the population factory — the SAME
        # code the director's respawn loop uses, so a hand-spawned unit and
        # an alcove replacement are identical (posted to the base, armed,
        # voiced). See world/director/population.py.
        if secbot:
            from world.director.population import spawn_secbot
            mob = spawn_secbot(caller.location, name=(raw_args or None))
            caller.msg(f"You manifest {mob.key} into the world.")
            msg_room_identity(
                location=caller.location,
                template="{mob} powers up, status lights climbing to green.",
                char_refs={"mob": mob},
                exclude=[caller],
            )
            return

        # Create the character
        mob = create_object(
            typeclass="typeclasses.characters.Character",
            key=mob_name,
            location=caller.location,
            home=caller.location
        )
        mob.db.is_npc = True   # the canonical NPC marker (absence = PC)

        # Set species before re-initializing the species-dependent
        # surfaces (longdesc default set, medical state).
        # ``at_object_creation`` already ran with the default species
        # (None → human), so for non-human spawns we must overwrite
        # those surfaces with species-aware values.
        if species != "human":
            mob.db.species = species
            # Re-seed longdesc with the species default surface set.
            from world.anatomy import get_species_default_longdesc_locations
            mob.longdesc = get_species_default_longdesc_locations(species)
            # Re-initialize medical state so organs come from the
            # species table (humans got the human organ set during
            # at_object_creation; rats need rat organs).
            from world.medical.core import MedicalState
            mob._medical_state = MedicalState(mob)
            mob.db.medical_state = mob._medical_state.to_dict()

        mob.sex = sex

        mob.grit = roll_stat()
        mob.resonance = roll_stat()
        mob.intellect = roll_stat()
        mob.motorics = roll_stat()

        # Humanoid-identity attributes (height / build / hair) — humans
        # and synthetics (replicants pass as human).  Rats and robots
        # skip these; their sdesc renders from the composed ``.key``
        # ("a wiry brown rat", "a battered security robot") naturally.
        if species in ("human", "synthetic_humanoid"):
            # Randomize so the mob gets a proper sdesc (e.g. "a gaunt
            # man with blonde braids") instead of falling back to
            # ``.key``.
            mob.height = choice(HEIGHTS)
            mob.build = choice(BUILDS)
            # sdesc_keyword defaults via get_sdesc() based on gender
            # (man / woman / person), so we leave it unset.
            # 20% chance of bald (None), otherwise random hair
            if randint(1, 5) == 1:
                mob.hair_color = None
                mob.hair_style = None
            else:
                mob.hair_color = choice(HAIR_COLORS)
                mob.hair_style = choice(HAIR_STYLES)

        # Flavor pass — random short desc, longdescs, and look_place.
        # /blank preserves the legacy minimal-flavor behavior.
        # ``apply_random_flavor`` is now species-aware (it dispatches
        # to ``mob.db.species``'s flavor tables), so non-humans get
        # rat-shaped / etc. prose automatically.
        if blank:
            mob.db.desc = (
                "A breathing body without an identity."
                " Its eyes flicker, but it does not move."
            )
        else:
            apply_random_flavor(mob)

        caller.msg(f"You manifest {mob_name} into the world.")
        msg_room_identity(
            location=caller.location,
            template="{mob} flickers into existence, vacant and twitching.",
            char_refs={"mob": mob},
            exclude=[caller],
        )
