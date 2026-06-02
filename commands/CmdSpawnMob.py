from evennia import Command
from evennia import create_object
from random import choice, randint
from world.namebank import (
    FIRST_NAMES_MALE,
    FIRST_NAMES_FEMALE,
    FIRST_NAMES_AMBIGUOUS,
    LAST_NAMES
)
from world.identity import HEIGHTS, BUILDS, HAIR_COLORS, HAIR_STYLES
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

    If no name is given, one is generated based on randomized sex.
    The mob receives randomized identity attributes (height, build, hair)
    plus a randomly selected short description, longdescs across every
    body location with seed data, and a look_place — drawn from
    ``world/mob_flavor/``.

    Switches:
        /blank   - skip the flavor pass; produces the legacy minimal mob
                   (stock filler description, no longdescs, no look_place)
                   for clean diagnostic spawns.
    """

    key = "@spawnmob"
    locks = "cmd:perm(Builders) or perm(Developers)"

    def func(self):
        caller = self.caller

        # Parse /blank switch
        raw_args = self.args.strip()
        blank = False
        if raw_args.startswith('/'):
            parts = raw_args[1:].split(None, 1)
            if parts:
                switches = [s.lower() for s in parts[0].split('/') if s]
                if "blank" in switches:
                    blank = True
                raw_args = parts[1] if len(parts) > 1 else ""

        # Assign sex with chance of ambiguity
        sex = choice(["male", "female"])
        if randint(1, 10) <= 2:  # 20% chance to use ambiguous
            sex = "ambiguous"

        # Select appropriate name bank
        if sex == "male":
            first = choice(FIRST_NAMES_MALE)
        elif sex == "female":
            first = choice(FIRST_NAMES_FEMALE)
        else:
            first = choice(FIRST_NAMES_AMBIGUOUS)

        last = choice(LAST_NAMES)

        # Use user-specified name if given, otherwise generate
        mob_name = raw_args or f"{first} {last}"

        # Create the character
        mob = create_object(
            typeclass="typeclasses.characters.Character",
            key=mob_name,
            location=caller.location,
            home=caller.location
        )

        mob.sex = sex

        mob.grit = roll_stat()
        mob.resonance = roll_stat()
        mob.intellect = roll_stat()
        mob.motorics = roll_stat()

        # Identity attributes — randomize so the mob gets a proper
        # sdesc (e.g. "a gaunt man with blonde braids") instead of
        # falling back to its .key.
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
