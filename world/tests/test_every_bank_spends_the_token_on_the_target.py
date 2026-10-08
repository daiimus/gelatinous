"""Every weapon bank spends {hit_location} on the target, and only there
(#3710; the handgun-only pin of #3708 generalised).

The loader fills ``{hit_location}`` with the TARGET's rolled location in
every audience's line (COMBAT_MESSAGE_FORMAT_SPEC). So:

* an attacker line never says "your {hit_location}": that is the
  attacker's own part, and it reads "Your groin closes around the grip";
* a victim or observer line never says "{attacker_name}'s {hit_location}":
  the attacker's part again, spelled with the target's location;
* a token is never glued to letters or a hyphen ("{hit_location}s",
  "{hit_location}or", "{hit_location}-first"): the scar of the 2025-09-27
  conversion, which ate a body word inside a longer word (hands, armor,
  kneecap, jawline), and one authored style that reads wrong for most
  locations;
* a token never sits in an adverb seat ("they stagger {hit_location}"),
  where the conversion had eaten the adverb "back".

The conversion also tokenized the author's word in seats behind an article
that are not the target's struck part (the head of the axe, the side of
your blade, drop to one knee, a side swing); those were restored by
aligning each line with its pre-conversion ancestor and are not pinned
here, because no regex tells "the side of your head" from "the {hit_location}".
A token behind a possessive or article whose anatomy the sentence fixes by
other words ("catches them under the chin; their {hit_location} snaps back")
is a known limit of the conversion and out of this pin's reach.
"""
import glob
import importlib
import os
import re
from unittest import TestCase

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK_DIR = os.path.join(HERE, "combat", "messages")
SELF = re.compile(r"\b[Yy]our \{hit_location\}(?![A-Za-z])")
ATTACKERS_PART = re.compile(r"\{attacker_name\}['’]s \{hit_location\}")
GLUED = re.compile(r"[A-Za-z]\{hit_location\}|\{hit_location\}[a-z]|\{hit_location\}-[a-z]")
# The conversion also tokenized the adverb "back" ("they stagger back") and
# list items ("the hand, wrist, and forearm"); the ancestor words were
# restored (#3710). These seats can never be the target's struck part.
ADVERB_SEAT = re.compile(r"\b(stagger|staggers|staggering|stumble|stumbles|stumbling|drawn|snap|snaps|whip|whips|jerk|jerks|yank|yanks|roll|rolls|slam|slams|lurch|lurches|reel|reels|them|you|it|come|comes|coming|go|goes|get|gets|fall|falls|thrown|knocked|forced|driven|pushed|sent) \{hit_location\}(?=[ .,;!—-]|$)")
# The issue's own census heuristic: an attacker line carrying the token
# while its victim sibling carries none. What survives is not this issue
# (the attacker's token is the target's part; the victim line simply does
# not name a part); the survivors are named so a new one fails and a fix
# must strike its entry.
SURVIVORS = {
    "bowel_disruptor/hit/31",
    "bowel_disruptor/hit/38",
    "bowel_disruptor/miss/37",
    "robot_riot_gun/kill/8",
    "robot_riot_gun/miss/11",
    "scalpel/hit/2",
    "scalpel/kill/12",
    "spraycan/initiate/12",
}


def _banks():
    for path in sorted(glob.glob(os.path.join(BANK_DIR, "*.py"))):
        name = os.path.basename(path)[:-3]
        if name.startswith("_"):
            continue
        module = importlib.import_module(f"world.combat.messages.{name}")
        messages = getattr(module, "MESSAGES", None)
        if isinstance(messages, dict):
            yield name, messages


def _entries():
    for bank, messages in _banks():
        for phase, entries in messages.items():
            for index, entry in enumerate(entries or ()):
                if isinstance(entry, dict):
                    yield bank, phase, index, entry


class TheTokenIsAlwaysTheTargets(TestCase):

    def test_there_are_banks_to_check(self):
        self.assertGreater(len(list(_banks())), 80)

    def test_no_attacker_line_spends_the_token_on_the_attacker(self):
        slips = [(b, p, e["attacker_msg"]) for b, p, _, e in _entries() if SELF.search(e.get("attacker_msg", ""))]
        self.assertEqual(slips, [], f"{len(slips)} attacker self lines: {slips[:5]}")

    def test_no_victim_or_observer_line_spends_the_token_on_the_attacker(self):
        slips = [(b, p, role, e[role]) for b, p, _, e in _entries() for role in ("victim_msg", "observer_msg")
                 if ATTACKERS_PART.search(e.get(role, ""))]
        self.assertEqual(slips, [], f"{len(slips)} attacker-part lines: {slips[:5]}")

    def test_no_token_is_glued_to_letters(self):
        slips = [(b, p, role, e[role]) for b, p, _, e in _entries() for role in ("attacker_msg", "victim_msg", "observer_msg")
                 if GLUED.search(e.get(role, ""))]
        self.assertEqual(slips, [], f"{len(slips)} glued tokens: {slips[:5]}")

    def test_no_token_sits_in_an_adverb_seat(self):
        slips = [(b, p, role, e[role]) for b, p, _, e in _entries() for role in ("attacker_msg", "victim_msg", "observer_msg")
                 if ADVERB_SEAT.search(e.get(role, ""))]
        self.assertEqual(slips, [], f"{len(slips)} adverb seats: {slips[:5]}")

    def test_the_heuristic_survivors_are_exactly_the_named_ones(self):
        # Down from 252 on master; a new one fails here, a fix strikes its
        # entry from SURVIVORS.
        found = {f"{b}/{p}/{i}" for b, p, i, e in _entries()
                 if "{hit_location}" in e.get("attacker_msg", "") and "{hit_location}" not in e.get("victim_msg", "")}
        self.assertEqual(found, SURVIVORS, {"new": sorted(found - SURVIVORS), "fixed": sorted(SURVIVORS - found)})
