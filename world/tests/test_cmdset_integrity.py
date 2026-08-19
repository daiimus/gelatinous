"""Cmdset integrity — the merged set is the player-visible surface.

Evennia treats ANY key/alias overlap between two commands as the same
merge slot: the later addition silently replaces the earlier one,
key and aliases together. That's how the doors' `close` ate the entire
`advance` command for five weeks (#2044) while every unit test stayed
green — unit tests instantiate command classes directly and never
cross the merge. These tests assert the integration invariant.
"""

from collections import Counter

from django.test import TestCase


def _merged_character_commands():
    from commands.default_cmdsets import CharacterCmdSet
    cs = CharacterCmdSet()
    cs.at_cmdset_creation()
    return list(cs.commands)


class TestCmdsetIntegrity(TestCase):

    def test_no_name_clashes_in_character_cmdset(self):
        """No key or alias may be claimed by two commands — a clash means
        one of them silently ceases to exist for every player."""
        names = Counter()
        owners = {}
        for cmd in _merged_character_commands():
            for name in [cmd.key] + list(cmd.aliases or []):
                names[name] += 1
                owners.setdefault(name, []).append(cmd.key)
        clashes = {n: owners[n] for n, c in names.items() if c > 1}
        self.assertEqual(
            clashes, {},
            f"name(s) claimed by multiple commands — the later addition "
            f"has silently REPLACED the earlier one: {clashes}")

    def test_canon_commands_survive_the_merge(self):
        """The commands a player would miss immediately must exist in
        the merged set — presence in a sub-cmdset is not presence."""
        canon = {
            "attack", "advance", "charge", "retreat", "flee", "grapple",
            "aim", "buy", "steal", "pickpocket", "frisk", "eat", "drink",
            "open", "close", "look", "get", "drop", "wield",
        }
        merged = {cmd.key for cmd in _merged_character_commands()}
        missing = canon - merged
        self.assertEqual(
            missing, set(),
            f"canon commands absent from the MERGED character cmdset "
            f"(eaten by a clash or dropped registration): {missing}")
