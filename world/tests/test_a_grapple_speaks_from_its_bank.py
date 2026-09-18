"""A grapple speaks from its authored bank (#3427).

`world/combat/messages/grapple.py` holds thirty "hit" variants, three
"miss" and two "release". The three resolvers a player actually reaches
printed one hardcoded sentence each -- *"You successfully grapple X!"*,
*"You fail to grapple X."*, *"You release your grapple on X."* -- and
never asked the bank anything, so seventy-two of seventy-six authored
lines were unreachable. The bank itself was fine: #2823 pins that every
bank exports the name the loader reads, and this one does. Nothing
called the loader for a grapple.

`speak_grapple_beat(actor, target, phase)` is the door now: one
`get_combat_message("grapple", phase, ...)` per beat, the actor's line
to the actor, the victim's to the victim, and the room's per-observer
template through `msg_room_identity`.

These tests drive `resolve_grapple_initiate` and
`resolve_release_grapple` -- what the command layer calls -- rather than
`speak_grapple_beat`. A helper-level test passes just as happily against a
resolver that never calls the helper.

## Four corrections to the plan these tests were written from

* **`randint` cannot be patched on `world.combat.grappling`.** Every
  resolver does `from random import randint` INSIDE the function body,
  so the module carries no such attribute and `mock.patch` would raise
  `AttributeError` rather than pin anything. The roll is pinned on
  `random.randint` itself -- `lambda lo, hi: hi` -- with motorics
  deciding the winner. That is also safer than a `side_effect` list of
  rolls: `select_hit_location` now takes a `random.randint` of its own
  on this path, and a list would have been eaten out of order by it.
* **The accessor colours what it returns**, by phase: "hit" comes back
  `|g...|n` (a hold is not a wound), "miss" `|y...|n`, and "release" `|g...|n` -- which is in neither
  list -- comes back bare. An expected line is therefore not simply the
  bank string, and a test that compared against the raw bank entry would
  fail on a correct implementation.
* **`get_combat_message` has to be patched on `world.combat.messages`**,
  the package the helper imports it from at call time; patching a name
  on `grappling` would miss.
* **The consensual hold is a real control, not a mocked one.** It is
  reached with `grant_trust(victim, grappler, "grab")` -- the door
  players use (#3363) -- so the test proves the trust path still bypasses
  the bank rather than proving a patched `check_consent` returns what it
  was told to.

The three `grapple_damage_*` phases are deliberately unpinned here:
#3285 is an open owner question about whether damage-in-a-grapple speaks
at all, and pinning a phase nobody has ruled on would make that ruling
harder to carry out.
"""

import contextlib
import random
import re
from unittest import TestCase, mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.combat.grappling as grappling
import world.combat.messages as messages_pkg
from world.combat.constants import (DB_CHAR, DB_GRAPPLED_BY_DBREF,
                                    DB_GRAPPLING_DBREF)
from world.combat.handler import get_or_create_combat
from world.combat.messages.grapple import MESSAGES
from world.combat.utils import (add_combatant, get_character_dbref,
                                get_display_name_safe)
from world.consent import grant_trust
from world.grammar import capitalize_first

#: What `speak_grapple_beat` is made to hand the accessor while a rendered
#: line is being compared, so the comparison has one known answer. The
#: accessor spaces the underscore out; the bank sees "left arm".
PINNED_LOCATION = "left_arm"
PINNED_LOCATION_SPACED = "left arm"

#: `get_combat_message._apply_color`, phase by phase.
# A hold is not a wound: the grapple bank keeps the colours its hardcoded
# lines wore -- green for a hold taken or released, yellow for a miss.
_COLOR = {"hit": "|g", "miss": "|y", "release": "|g"}

#: The lines the resolvers used to print instead of asking the bank.
OLD_LINES = ("You successfully grapple", "You fail to grapple",
             "You release your grapple on")


def _coloured(phase, text):
    prefix = _COLOR.get(phase)
    return f"{prefix}{text}|n" if prefix else text


def _render(template, attacker_name, target_name,
            hit_location=PINNED_LOCATION_SPACED):
    """One bank string rendered with the accessor's own kwargs."""
    return template.format(
        attacker_name=attacker_name, target_name=target_name,
        attacker=attacker_name, target=target_name,
        hit_location=hit_location,
        item_name="fists", item="fists",
        blood="crimson", Blood="Crimson", phase="?",
    )


class _GrappleBeat(EvenniaTest):
    """Two people in a real fight, with every line they are told kept."""

    def setUp(self):
        super().setUp()
        self.A = create_object("typeclasses.characters.Character",
                               key="Alpha", location=self.room1)
        self.B = create_object("typeclasses.characters.Character",
                               key="Bravo", location=self.room1)
        self.handler = get_or_create_combat(self.room1)
        add_combatant(self.handler, self.A, target=self.B)
        add_combatant(self.handler, self.B, target=self.A)
        self.said = {}
        for ch in (self.A, self.B):
            self.said[ch] = []
            ch.msg = (lambda who: (lambda text=None, **kw:
                                   self.said[who].append(str(text))))(ch)

    # ── fixture plumbing ────────────────────────────────────────────

    def entries(self):
        lst = self.handler.db.combatants
        return (lst,
                next(e for e in lst if e.get(DB_CHAR) == self.A),
                next(e for e in lst if e.get(DB_CHAR) == self.B))

    @contextlib.contextmanager
    def _staged(self, bank=None, pin_location=True):
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(random, "randint", lambda lo, hi: hi))
            if pin_location:
                stack.enter_context(
                    mock.patch("world.medical.utils.select_hit_location",
                               return_value=PINNED_LOCATION))
            if bank is not None:
                stack.enter_context(
                    mock.patch.object(messages_pkg, "get_combat_message", bank))
            yield stack.enter_context(
                mock.patch.object(grappling, "msg_room_identity"))

    def initiate(self, win, bank=None, pin_location=True):
        """Drive the real resolver; the roll is decided by motorics, not
        by luck -- `randint` returns its own upper bound."""
        self.A.motorics, self.B.motorics = (100, 1) if win else (1, 100)
        lst, actor, _ = self.entries()
        with self._staged(bank=bank, pin_location=pin_location) as room:
            grappling.resolve_grapple_initiate(actor, lst, self.handler)
        self.handler.db.combatants = lst
        return room

    def hold(self):
        """Put the pair in the state a won grapple leaves behind."""
        lst, actor, victim = self.entries()
        actor[DB_GRAPPLING_DBREF] = get_character_dbref(self.B)
        victim[DB_GRAPPLED_BY_DBREF] = get_character_dbref(self.A)
        self.handler.db.combatants = lst
        self.assertIs(self.handler.get_grappling_obj(self.entries()[1]), self.B,
                      "fixture: Alpha is not holding Bravo")

    def release(self, bank=None, pin_location=True):
        lst, actor, _ = self.entries()
        with self._staged(bank=bank, pin_location=pin_location) as room:
            grappling.resolve_release_grapple(actor, lst, self.handler)
        self.handler.db.combatants = lst
        return room

    # ── what the bank should have said ──────────────────────────────

    def expected_lines(self, phase, key):
        """Every variant of `phase` rendered for one audience, exactly as
        the accessor renders it -- the set the delivered line must be in."""
        if key == "attacker_msg":
            names = dict(attacker_name="You",
                         target_name=get_display_name_safe(self.B, self.A))
        else:
            names = dict(
                attacker_name=capitalize_first(
                    get_display_name_safe(self.A, self.B)),
                target_name="you")
        return [_coloured(phase, _render(v[key], **names))
                for v in MESSAGES[phase]]

    def expected_templates(self, phase):
        """The observer line with its two character placeholders swapped
        for `msg_room_identity` tokens, which is what the accessor hands
        back as `observer_template`."""
        out = []
        for variant in MESSAGES[phase]:
            template = (variant["observer_msg"]
                        .replace("{attacker_name}", "{actor}")
                        .replace("{target_name}", "{target_char}")
                        .replace("{attacker}", "{actor}")
                        .replace("{target}", "{target_char}"))
            out.append(_coloured(
                phase, template.replace("{hit_location}",
                                        PINNED_LOCATION_SPACED)))
        return out

    def matching(self, said, expected, what):
        """Which bank variants the delivered lines match. A set, because
        the point is which BEAT was told, not which sentence."""
        found = {i for i, line in enumerate(expected) if line in said}
        self.assertTrue(
            found,
            f"{what}: nothing said matched a bank variant.\n"
            f"  said: {said}\n  first expected: {expected[0]}")
        return found

    def told(self, who):
        return self.said[who]

    def assert_no_old_line(self):
        for who in (self.A, self.B):
            for line in self.said[who]:
                for old in OLD_LINES:
                    self.assertNotIn(
                        old, line,
                        f"{who.key} was told the hardcoded line: {line}")

    def assert_broadcast(self, room, phase):
        """The room heard the bank's observer template, per observer, with
        the two people who got their own line left out."""
        self.assertTrue(room.called, "the room was told nothing")
        kwargs = room.call_args.kwargs
        self.assertEqual(kwargs["location"], self.room1)
        self.assertEqual(kwargs["char_refs"],
                         {"actor": self.A, "target_char": self.B})
        self.assertEqual(set(kwargs["exclude"]), {self.A, self.B})
        templates = self.expected_templates(phase)
        self.assertIn(kwargs["template"], templates,
                      f"the room got a template outside the bank: "
                      f"{kwargs['template']}")
        return {i for i, t in enumerate(templates) if t == kwargs["template"]}


def _sentinel_bank(record):
    """A stand-in accessor that records the ask and answers in strings no
    bank contains, so the delivery can be pinned without the bank."""
    def bank(weapon_type, phase, attacker=None, target=None, **kwargs):
        record.append((weapon_type, phase, attacker, target, kwargs))
        return {
            "attacker_msg": "SENTINEL-ACTOR",
            "victim_msg": "SENTINEL-VICTIM",
            "observer_msg": "SENTINEL-OBSERVER",
            "observer_template": "SENTINEL {actor} {target_char}",
            "observer_char_refs": {"actor": attacker, "target_char": target},
        }
    return bank


class TestAWonGrappleSpeaksFromTheBank(_GrappleBeat):

    def test_the_actor_reads_one_of_the_thirty_hit_variants(self):
        self.initiate(win=True)
        self.matching(self.told(self.A), self.expected_lines("hit", "attacker_msg"),
                      "the grappler")
        self.assert_no_old_line()

    def test_the_victim_reads_the_same_beat_from_their_side(self):
        self.initiate(win=True)
        self.matching(self.told(self.B), self.expected_lines("hit", "victim_msg"),
                      "the victim")

    def test_the_room_hears_it_through_the_identity_layer(self):
        room = self.initiate(win=True)
        self.assert_broadcast(room, "hit")

    def test_all_three_audiences_are_told_the_same_variant(self):
        """One beat, three views. Rendering each audience from a
        separately drawn variant would read as three different events in
        the same room."""
        room = self.initiate(win=True)
        actor = self.matching(self.told(self.A),
                              self.expected_lines("hit", "attacker_msg"), "actor")
        victim = self.matching(self.told(self.B),
                               self.expected_lines("hit", "victim_msg"), "victim")
        observer = self.assert_broadcast(room, "hit")
        self.assertTrue(actor & victim & observer,
                        f"three different beats: {sorted(actor)} / "
                        f"{sorted(victim)} / {sorted(observer)}")

    def test_the_bank_is_asked_for_grapple_hit(self):
        """The same claim from the other end: whatever the bank returns
        is what the three parties are handed."""
        record = []
        room = self.initiate(win=True, bank=_sentinel_bank(record))
        self.assertEqual([(w, p) for w, p, _, _, _ in record], [("grapple", "hit")])
        _, _, attacker, target, _ = record[0]
        self.assertIs(attacker, self.A)
        self.assertIs(target, self.B)
        self.assertIn("SENTINEL-ACTOR", self.told(self.A))
        self.assertIn("SENTINEL-VICTIM", self.told(self.B))
        self.assertEqual(room.call_args.kwargs["template"],
                         "SENTINEL {actor} {target_char}")
        self.assertEqual(room.call_args.kwargs["char_refs"],
                         {"actor": self.A, "target_char": self.B})

    def test_the_hold_is_still_taken(self):
        """Control: the prose change did not move the state change."""
        self.initiate(win=True)
        _, actor, victim = self.entries()
        self.assertEqual(actor.get(DB_GRAPPLING_DBREF),
                         get_character_dbref(self.B))
        self.assertEqual(victim.get(DB_GRAPPLED_BY_DBREF),
                         get_character_dbref(self.A))


class TestALostGrappleSpeaksFromTheBank(_GrappleBeat):

    def test_the_actor_reads_one_of_the_three_miss_variants(self):
        self.initiate(win=False)
        self.matching(self.told(self.A), self.expected_lines("miss", "attacker_msg"),
                      "the grappler")
        self.assert_no_old_line()

    def test_the_victim_reads_the_miss_from_their_side(self):
        self.initiate(win=False)
        self.matching(self.told(self.B), self.expected_lines("miss", "victim_msg"),
                      "the victim")

    def test_the_room_hears_the_miss(self):
        room = self.initiate(win=False)
        self.assert_broadcast(room, "miss")

    def test_the_bank_is_asked_for_grapple_miss(self):
        record = []
        self.initiate(win=False, bank=_sentinel_bank(record))
        self.assertEqual([(w, p) for w, p, _, _, _ in record], [("grapple", "miss")])

    def test_no_hold_is_taken(self):
        """Control: a lost roll still holds nobody."""
        self.initiate(win=False)
        _, actor, victim = self.entries()
        self.assertIsNone(actor.get(DB_GRAPPLING_DBREF))
        self.assertIsNone(victim.get(DB_GRAPPLED_BY_DBREF))


class TestALetGoSpeaksFromTheBank(_GrappleBeat):

    def test_the_actor_reads_one_of_the_two_release_variants(self):
        self.hold()
        self.release()
        self.matching(self.told(self.A),
                      self.expected_lines("release", "attacker_msg"),
                      "the grappler")
        self.assert_no_old_line()

    def test_the_victim_is_told_they_are_free(self):
        self.hold()
        self.release()
        self.matching(self.told(self.B),
                      self.expected_lines("release", "victim_msg"),
                      "the released person")

    def test_the_room_hears_the_release(self):
        self.hold()
        room = self.release()
        self.assert_broadcast(room, "release")

    def test_the_bank_is_asked_for_grapple_release(self):
        record = []
        self.hold()
        self.release(bank=_sentinel_bank(record))
        self.assertEqual([(w, p) for w, p, _, _, _ in record],
                         [("grapple", "release")])

    def test_both_sides_of_the_grapple_are_cleared_as_before(self):
        self.hold()
        self.release()
        _, actor, victim = self.entries()
        self.assertIsNone(actor.get(DB_GRAPPLING_DBREF))
        self.assertIsNone(victim.get(DB_GRAPPLED_BY_DBREF))

    def test_releasing_nobody_says_nothing_from_the_bank(self):
        """Control: the guard above the prose still refuses first."""
        record = []
        self.release(bank=_sentinel_bank(record))
        self.assertEqual(record, [])
        self.assertIn("You are not grappling anyone.", self.told(self.A))


class TestAConsentedHoldIsNotAGrappleBeat(_GrappleBeat):
    """CONTROL (#3363). A hold someone allowed is not the fight the bank
    is written for: no roll happened, so there is no "hit" to narrate.
    Its own three lines stay, and the bank is not asked."""

    def setUp(self):
        super().setUp()
        grant_trust(self.B, self.A, "grab")

    def test_the_held_person_is_told_they_let_it_happen(self):
        self.initiate(win=False)     # a LOSING roll must not matter
        self.assertTrue(
            any("takes hold of you; you let them" in line
                for line in self.told(self.B)),
            f"the consensual line is gone: {self.told(self.B)}")

    def test_the_grappler_is_told_the_same(self):
        self.initiate(win=False)
        self.assertTrue(any("who lets you" in line for line in self.told(self.A)),
                        f"the consensual line is gone: {self.told(self.A)}")

    def test_the_bank_is_never_asked(self):
        record = []
        self.initiate(win=False, bank=_sentinel_bank(record))
        self.assertEqual(record, [],
                         "a consented hold was narrated as a combat grapple")

    def test_the_room_hears_the_consensual_broadcast(self):
        room = self.initiate(win=False)
        self.assertIn("does not resist", room.call_args.kwargs["template"])

    def test_the_hold_is_taken_without_a_contest(self):
        """Guards the guard: if trust stopped reaching this branch the
        three tests above would be checking the contested path and would
        fail for the wrong reason, so pin the state that only this branch
        produces -- a hold taken off a losing roll."""
        self.initiate(win=False)
        _, actor, _ = self.entries()
        self.assertEqual(actor.get(DB_GRAPPLING_DBREF),
                         get_character_dbref(self.B))


class TestTheHoldLandsSomewhereReal(_GrappleBeat):
    """`{hit_location}` is in the bank ("locking your arms around their
    chest"), so the accessor has to be told a body part. Nothing else in
    the grapple path had ever chosen one."""

    def _kwargs_of_a_real_grapple(self):
        record = []
        self.initiate(win=True, bank=_sentinel_bank(record), pin_location=False)
        self.assertEqual(len(record), 1)
        return record[0][4]

    def test_the_accessor_is_told_a_body_location(self):
        location = self._kwargs_of_a_real_grapple().get("hit_location")
        self.assertTrue(location, "no hit_location reached the bank")
        self.assertIsInstance(location, str)
        self.assertNotIn("{", location)
        self.assertNotIn("}", location)
        self.assertNotEqual(location.lower(), "none")

    def test_it_is_one_of_the_victims_own_body_locations(self):
        """Not a constant, and not the attacker's: the hold lands on the
        person being held, chosen the way an attack chooses."""
        location = self._kwargs_of_a_real_grapple().get("hit_location")
        allowed = set(self.B.longdesc or {}) | {"chest", "arm"}
        self.assertIn(location, allowed,
                      f"{location} is not a location {self.B.key} has")


class TestEveryGrappleVariantRenders(TestCase):
    """Every authored variant, through the real accessor, one at a time.

    The accessor swallows a bad placeholder into the string
    `"(Error: Missing placeholder ...)"` and delivers THAT to the player,
    so a broken variant is invisible until someone reads it in play. Now
    that all seventy-six are reachable, each one is rendered here.
    """

    PHASES = ("hit", "miss", "release")

    def _render_variant(self, phase, index):
        from world.combat.messages import get_combat_message
        with mock.patch.object(random, "choice", lambda seq, _i=index: seq[_i]):
            return get_combat_message("grapple", phase, attacker=None,
                                      target=None,
                                      hit_location=PINNED_LOCATION)

    def test_every_variant_formats_with_no_residual_braces(self):
        bad = []
        for phase in self.PHASES:
            for index in range(len(MESSAGES[phase])):
                msgs = self._render_variant(phase, index)
                for key in ("attacker_msg", "victim_msg", "observer_msg"):
                    text = msgs[key]
                    if "{" in text or "}" in text or "Error:" in text:
                        bad.append(f"{phase}[{index}].{key}: {text}")
                leftover = set(re.findall(r"\{(\w+)\}", msgs["observer_template"]))
                stray = leftover - {"actor", "target_char"}
                if stray:
                    bad.append(f"{phase}[{index}].observer_template leaves "
                               f"{sorted(stray)}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_the_hit_location_actually_reaches_the_prose(self):
        """The variants that name a body part must show the one they were
        given, spaced out of its underscore."""
        used = [i for i, v in enumerate(MESSAGES["hit"])
                if "{hit_location}" in v["attacker_msg"]]
        self.assertTrue(used, "no hit variant uses {hit_location} any more")
        for index in used:
            rendered = self._render_variant("hit", index)["attacker_msg"]
            self.assertIn(PINNED_LOCATION_SPACED, rendered)
            self.assertNotIn(PINNED_LOCATION, rendered)

    def test_the_pin_really_walks_the_bank(self):
        """Guards the guard: if the `random.choice` pin stopped selecting,
        the sweep above would render one variant thirty times and prove
        nothing."""
        for phase in self.PHASES:
            rendered = {self._render_variant(phase, i)["attacker_msg"]
                        for i in range(len(MESSAGES[phase]))}
            self.assertEqual(len(rendered), len(MESSAGES[phase]),
                             f"the {phase} sweep did not visit every variant")


class TestAFaceIsAFaceNotALimb(TestCase):
    """Two "hit" variants read `{hit_location}` for the place an
    expression sits, and `hit_location` is where the hold landed --
    "a look of grim determination on your left leg"."""

    def test_the_grim_determination_variant_says_face(self):
        variants = [v for v in MESSAGES["hit"]
                    if "grim determination" in v["attacker_msg"]]
        self.assertEqual(len(variants), 1,
                         "the variant this pin is about has moved")
        for key in ("attacker_msg", "victim_msg", "observer_msg"):
            text = variants[0][key]
            self.assertIn("determination on", text)
            self.assertIn("face", text)
            self.assertNotIn("{hit_location}", text)

    def test_no_hit_variant_wears_its_expression_on_a_limb(self):
        pattern = re.compile(r"determination on \w+ \{hit_location\}")
        bad = [f"hit[{i}].{key}: {v[key]}"
               for i, v in enumerate(MESSAGES["hit"])
               for key in ("attacker_msg", "victim_msg", "observer_msg")
               if pattern.search(v[key])]
        self.assertEqual(bad, [], "\n".join(bad))
