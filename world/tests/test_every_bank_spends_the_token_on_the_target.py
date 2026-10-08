"""Every weapon bank spends {hit_location} on the target, and only there
(#3710; the handgun-only pin of #3708 generalised).

The loader fills ``{hit_location}`` with the TARGET's rolled location in
every audience's line (COMBAT_MESSAGE_FORMAT_SPEC). So:

* an attacker line never says "your {hit_location}": that is the
  attacker's own part, and it reads "Your groin closes around the grip";
* a victim or observer line never says "{attacker_name}'s {hit_location}":
  the attacker's part again, spelled with the target's location;
* a token is never glued to letters ("{hit_location}s", "{hit_location}or"):
  the scar of an old regex that ate a body word inside a longer word
  (hands, armor, kneecap, jawline).
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
GLUED = re.compile(r"[A-Za-z]\{hit_location\}|\{hit_location\}[a-z]")


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
            for entry in entries or ():
                if isinstance(entry, dict):
                    yield bank, phase, entry


class TheTokenIsAlwaysTheTargets(TestCase):

    def test_there_are_banks_to_check(self):
        self.assertGreater(len(list(_banks())), 80)

    def test_no_attacker_line_spends_the_token_on_the_attacker(self):
        slips = [(b, p, e["attacker_msg"]) for b, p, e in _entries() if SELF.search(e.get("attacker_msg", ""))]
        self.assertEqual(slips, [], f"{len(slips)} attacker self lines: {slips[:5]}")

    def test_no_victim_or_observer_line_spends_the_token_on_the_attacker(self):
        slips = [(b, p, role, e[role]) for b, p, e in _entries() for role in ("victim_msg", "observer_msg")
                 if ATTACKERS_PART.search(e.get(role, ""))]
        self.assertEqual(slips, [], f"{len(slips)} attacker-part lines: {slips[:5]}")

    def test_no_token_is_glued_to_letters(self):
        slips = [(b, p, role, e[role]) for b, p, e in _entries() for role in ("attacker_msg", "victim_msg", "observer_msg")
                 if GLUED.search(e.get(role, ""))]
        self.assertEqual(slips, [], f"{len(slips)} glued tokens: {slips[:5]}")

    def test_a_token_in_an_attacker_line_is_echoed_to_the_victim(self):
        # The issue's own heuristic, kept as a census rather than a bar: a
        # legitimate target token whose victim sibling says the word plainly
        # is a victim-side gap, not this issue. Pinned at its count on
        # 2026-10-08 (10, down from 252) so the number can only fall.
        count = sum(1 for _, _, e in _entries()
                    if "{hit_location}" in e.get("attacker_msg", "") and "{hit_location}" not in e.get("victim_msg", ""))
        self.assertLessEqual(count, 10, count)
