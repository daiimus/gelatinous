"""Crowd ambience does not act on the player's body (#2738).

The module's own Rule 2:

    ...no hand in YOUR pocket, no shove that moves YOU, no pinning YOUR
    arms. Those imply a physical action the player cannot answer. Plain
    sensory perception ("you hear a dog bark", "the cold air bites") is
    fine.

Second-person address is explicitly PERMITTED. Acting on the player's
body is not. Six lines did the second, all in `packed` tiers:

    nightclub  "the crowd surges as one on the drop and you go where it goes"
    constab.   "the crowd moves you; queueing is now a fiction"
    market     "the crush carries you -- walking is a negotiation..."
    market     "...whatever's in your pockets is everyone's business"
    market     "the jam ... decides where you go next"
    shop       "the crowd moves you whether you're in the queue or not"

They cluster in `packed` because that is where an author reaching for
"this crowd is overwhelming" naturally writes physical consequence --
and it is exactly where the rule matters most, since a player in a
packed crowd is the one most likely to want to push back. The line
asserts something happened that the game state does not reflect: they
were not moved, and nothing was taken.

THE GUARD IS A REVIEWED SET, NOT A VERB BLACKLIST, and #2738's own
method note is why. A first scan for forbidden verbs (`shoves you`,
`rifles your`) found ZERO -- the violations say "the crowd moves you"
and "the crush carries you". Pattern-matching the forbidden phrasing
missed the forbidden meaning entirely.

So this asserts that the set of second-person lines is exactly the set
somebody has READ. A new one fails here and has to be adjudicated
against Rule 2 by a person, which is the only thing that worked.
"""
import re

from evennia.utils.test_resources import EvenniaTest

from world.crowd.crowd_messages import CROWD_MESSAGES

SECOND_PERSON = re.compile(r"\byou\b|\byour\b|\byours\b|\byourself\b", re.I)

#: Every second-person crowd line, read against Rule 2 and kept. All six
#: are PERCEPTION -- hearing, vibration through the floor, smell -- which
#: is the rule's own permitted example.
REVIEWED = {
    "someone nearby counts under their breath in a language you don't know",
    "two voices murmur low in a doorway and cut off as you come near",
    "a single low conversation murmurs somewhere behind you and goes quiet",
    "you can't hear the person beside you without putting your mouth to "
    "their ear",
    "the bass comes up through the grating into the soles of your feet",
    "a wall of sweat-and-fog heat hits you at the edge of the floor",
}


class TestRuleTwo(EvenniaTest):

    def _second_person(self):
        found = set()
        for _profile, pool in CROWD_MESSAGES.items():
            if not isinstance(pool, dict):
                continue
            for _intensity, cats in pool.items():
                if not isinstance(cats, dict):
                    continue
                for _cat, lines in cats.items():
                    for line in lines or []:
                        if SECOND_PERSON.search(line):
                            found.add(line)
        return found

    def test_the_scan_reads_real_pools(self):
        """Control: an empty sweep would satisfy the assertion below
        while checking nothing."""
        total = sum(len(lines or [])
                    for pool in CROWD_MESSAGES.values()
                    if isinstance(pool, dict)
                    for cats in pool.values() if isinstance(cats, dict)
                    for lines in cats.values())
        self.assertGreater(total, 100)

    def test_the_pattern_catches_second_person(self):
        """Control: and that the matcher fires on a known-good line."""
        self.assertTrue(SECOND_PERSON.search(
            "the bass comes up through the grating into the soles of "
            "your feet"))

    def test_every_second_person_line_has_been_read(self):
        found = self._second_person()
        new = found - REVIEWED
        self.assertEqual(
            new, set(),
            "a new second-person crowd line — read it against Rule 2 "
            "(perception is fine; moving the player or reaching into "
            "their pockets is not), then add it to REVIEWED:\n  "
            + "\n  ".join(sorted(new)))

    def test_the_reviewed_set_is_not_stale(self):
        """A line removed from the catalogue should leave REVIEWED, or
        the list slowly stops describing anything."""
        gone = REVIEWED - self._second_person()
        self.assertEqual(gone, set(),
                         f"REVIEWED lists lines that no longer exist: {gone}")
