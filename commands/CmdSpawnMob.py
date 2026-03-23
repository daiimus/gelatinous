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


def roll_stat():
    return randint(1, 3)


class CmdSpawnMob(Command):
    """
    Spawns an unpossessed Character with randomized name, stats, and sex.

    Usage:
        @spawnmob [optional name]

    If no name is given, one is generated based on randomized sex.
    The mob receives randomized identity attributes (height, build,
    hair) so it participates in the identity/recognition system.
    """

    key = "@spawnmob"
    locks = "cmd:perm(Builders) or perm(Developers)"

    def func(self):
        caller = self.caller

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
        mob_name = self.args.strip() or f"{first} {last}"

        # Create the character
        mob = create_object(
            typeclass="typeclasses.characters.Character",
            key=mob_name,
            location=caller.location,
            home=caller.location
        )

        mob.db.desc = (
            "A breathing body without an identity."
            " Its eyes flicker, but it does not move."
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

        caller.msg(f"You manifest {mob_name} into the world.")
        caller.location.msg_contents(
            f"{mob_name} flickers into existence, vacant and twitching.",
            exclude=caller,
        )
