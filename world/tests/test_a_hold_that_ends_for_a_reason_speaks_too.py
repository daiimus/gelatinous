"""A hold that ends for a reason other than letting go speaks too (#3615).

#3427 put the three grapple resolvers onto the authored bank. It left
four other doors where a hold ends -- and every one of them printed its
own fixed sentence, told nobody but the two people involved, and could
not be expanded or cut the way the rest of the combat prose can:

* `world/combat/movement_resolution.py::_release_grapple_for_charge`,
  both halves of it (the charger stays in the room, or charges out of
  it);
* `commands/combat/jump.py`, the gap jump -- *"You release your grip on
  X to focus on the gap jump!"*;
* the same file's blast sacrifice -- *"The explosion breaks your
  hold!"*;
* `commands/combat/movement.py`, the queue-time line the charger reads
  the moment they aim a charge at somebody else while holding a victim.

Five phases were authored for them (eleven variants), the helper was
made public as `speak_grapple_beat(actor, target, phase, *, audiences,
**extra_chars)`, and the four doors now speak through it. Two things
were new in the accessor to make that possible, and both are pinned
here rather than assumed:

* **a third party the line names.** `release_charge` says who is being
  charged, which is neither the actor nor the victim. It travels as
  `extra_chars={"charge_target": obj}` and is rendered PER AUDIENCE --
  the charger reads their own name for them, the victim reads theirs,
  and the room's template keeps a literal `{charge_target}` for
  `msg_room_identity` to resolve per observer, exactly as the two
  principals already were. Two people who know the same third party by
  different names is the whole point, so the fixture arranges precisely
  that and the tests fail if either audience reads the other's name.
* **`audiences`.** `release_intent` is a preview printed while the
  charge is still queued: the actor sets themselves to let go, and the
  hold has NOT ended yet. The victim must not be told they were
  released and the room must hear nothing at all.

## What is driven and what is pinned

Three of the four doors are driven through the code a player reaches:
`resolve_charge` for both charge halves, `CmdJump.handle_gap_jump` for
the gap, and `CmdCharge.func` for the preview. The blast door lives
inside `handle_explosive_sacrifice`'s delayed `reveal_outcome` closure,
so it is reached the way production reaches it -- `delay` is captured
and the callback fired -- rather than by calling the helper and hoping.
A source pin backs all four up: the retired sentences must not be
anywhere in the three command/resolver files, because a helper-level
test passes just as happily against a door that never calls the helper.

## Four things learned writing this

* **`randint` is bound at module scope in `world/combat/dice.py`** and
  in `movement_resolution`, unlike the grapple resolvers (which import
  it inside the function body, so the sibling module pins
  `random.randint`). Patching `random.randint` here would leave both
  rolls genuinely random. The pin is on `dice.randint` and
  `movement_resolution.randint`, with motorics deciding the winner.
* **`extra_chars` never reaches `shared_kwargs`**, which is what leaves
  `{charge_target}` literal in `observer_template` -- the `_PassThrough`
  map only passes through keys it was not given. So the expected room
  template is the bank's observer line with the two character
  placeholders swapped for identity tokens and the third one left
  alone.
* **The accessor capitalises the whole formatted line**, then colours
  it. Expected lines are built the same way round, or every victim line
  whose sentence opens on a name mismatches.
* **No variant COUNT is pinned.** The owner's ask was a bank that can
  be "expanded/subtracted like all our combat messages"; a test that
  fails when a line is added would be a test against the point of the
  change. Every variant is swept, none is counted.
"""

from __future__ import annotations

import contextlib
import inspect
import re
from unittest import TestCase, mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.combat.dice as dice
import world.combat.grappling as grappling
import world.combat.movement_resolution as movement_resolution
from world.combat.constants import (COMBAT_ACTION_CHARGE, DB_CHAR,
                                    DB_COMBAT_ACTION, DB_COMBAT_ACTION_TARGET,
                                    DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF,
                                    NDB_COUNTDOWN_REMAINING,
                                    NDB_GRENADE_TIMER)
from world.combat.handler import get_or_create_combat
from world.combat.messages import get_combat_message
from world.combat.messages.grapple import MESSAGES
from world.combat.utils import (add_combatant, get_character_dbref,
                                get_display_name_safe)
from world.grammar import capitalize_first
from world.identity import get_apparent_uid

CHARACTER = "typeclasses.characters.Character"

#: The five phases the four doors speak through.
NEW_PHASES = ("release_charge", "release_charge_away", "release_jump",
              "release_blast", "release_intent")

#: A hold lost, or about to be: the accessor's grapple override paints
#: all five yellow, the colour a failed grapple already wore.
LOST_GRIP = "|y"

#: Nothing in the five new phases may name anything but the two people
#: in the hold and the third party the charger goes for.
ALLOWED_PLACEHOLDERS = {"attacker_name", "target_name", "charge_target"}

#: The sentences the four doors printed instead of asking the bank. None
#: of them may survive anywhere in the three files.
OLD_LINES = (
    "You release your grapple on",           # both charge halves
    "releases their grapple on you",
    "You release your grip on",              # gap jump
    "releases their grip on you",
    "to focus on the gap jump",
    "The blast throws you clear",            # blast sacrifice
    "The explosion breaks your hold",
    "You prepare to release your grapple on",   # queue-time preview
)

#: How the two principals know the third party. Deliberately different,
#: and neither a substring of the other or of anybody's key.
ACTOR_SEES = "Vex"
VICTIM_SEES = "Quill"
THIRD_PARTY_KEY = "Cassidy"


# ── the accessor's own rendering, mirrored ──────────────────────────

def _fmt(template, **names):
    """One bank string through the accessor's format kwargs."""
    return template.format(
        item_name="fists", item="fists",
        blood="crimson", Blood="Crimson", phase="?", **names)


def _actor_line(variant, *, target_name, charge_target):
    return LOST_GRIP + capitalize_first(_fmt(
        variant["attacker_msg"],
        attacker_name="You", attacker="You",
        target_name=target_name, target=target_name,
        charge_target=charge_target)) + "|n"


def _victim_line(variant, *, attacker_name, charge_target):
    return LOST_GRIP + capitalize_first(_fmt(
        variant["victim_msg"],
        attacker_name=attacker_name, attacker=attacker_name,
        target_name="you", target="you",
        charge_target=charge_target)) + "|n"


def _room_template(variant):
    """The observer line as `msg_room_identity` receives it: the two
    principals swapped for identity tokens, `{charge_target}` left
    literal for the same layer to resolve per observer."""
    template = (variant["observer_msg"]
                .replace("{attacker_name}", "{actor}")
                .replace("{target_name}", "{target_char}")
                .replace("{attacker}", "{actor}")
                .replace("{target}", "{target_char}"))
    return LOST_GRIP + template + "|n"


class _Stranger:
    """A third party for the bankside sweeps: `get_display_name_safe`
    falls back to `.key` when there is no observer, which is all the
    rendering tests need and keeps them off the database."""

    key = THIRD_PARTY_KEY


# ── fixture ─────────────────────────────────────────────────────────

class _AHoldInARoom(EvenniaTest):
    """Alpha holds Bravo. Cassidy stands there to be charged -- known to
    Alpha as Vex and to Bravo as Quill, so a line rendered for the wrong
    audience is visible in the text itself."""

    def setUp(self):
        super().setUp()
        self.A = create_object(CHARACTER, key="Alpha", location=self.room1)
        self.B = create_object(CHARACTER, key="Bravo", location=self.room1)
        self.C = create_object(CHARACTER, key=THIRD_PARTY_KEY,
                               location=self.room1)
        self.A.motorics, self.B.motorics, self.C.motorics = 100, 1, 1

        uid = get_apparent_uid(self.C)
        self.assertIsNotNone(uid, "fixture: the third party has no identity")
        self.A.recognition_memory = {uid: {"assigned_name": ACTOR_SEES}}
        self.B.recognition_memory = {uid: {"assigned_name": VICTIM_SEES}}
        self.assertEqual(get_display_name_safe(self.C, self.A), ACTOR_SEES,
                         "fixture: the charger does not know the target")
        self.assertEqual(get_display_name_safe(self.C, self.B), VICTIM_SEES,
                         "fixture: the victim does not know the target")

        self.handler = get_or_create_combat(self.room1)
        add_combatant(self.handler, self.A, target=self.C)
        add_combatant(self.handler, self.B, target=self.A)
        add_combatant(self.handler, self.C, target=self.A)
        self.take_hold()
        self.capture()

    # ── plumbing ────────────────────────────────────────────────────

    def capture(self):
        self.said = {}
        for ch in (self.A, self.B, self.C):
            self.said[ch] = []
            ch.msg = (lambda who: (lambda text=None, **kw:
                                   self.said[who].append(str(text))))(ch)

    def take_hold(self):
        lst = self.handler.db.combatants
        actor = next(e for e in lst if e.get(DB_CHAR) == self.A)
        victim = next(e for e in lst if e.get(DB_CHAR) == self.B)
        actor[DB_GRAPPLING_DBREF] = get_character_dbref(self.B)
        victim[DB_GRAPPLED_BY_DBREF] = get_character_dbref(self.A)
        self.handler.db.combatants = lst
        self.assertIs(self.handler.get_grappling_obj(self.entry(self.A)),
                      self.B, "fixture: Alpha is not holding Bravo")

    def entry(self, who):
        return next(e for e in self.handler.db.combatants
                    if e.get(DB_CHAR) == who)

    def maybe_entry(self, who):
        return next((e for e in self.handler.db.combatants
                     if e.get(DB_CHAR) == who), None)

    def told(self, who):
        return self.said[who]

    def text(self, who):
        return "\n".join(self.said[who])

    def assert_beat(self, who, expected, what):
        """Which authored variants the delivered lines match -- a set,
        because the claim is which BEAT was told, not which sentence."""
        said = self.told(who)
        found = {i for i, line in enumerate(expected) if line in said}
        self.assertTrue(
            found,
            f"{what}: nothing said matched a bank variant.\n"
            f"  said: {said}\n  first expected: {expected[0]}")
        return found

    def assert_no_old_line(self):
        for who in (self.A, self.B, self.C):
            for line in self.said[who]:
                for old in OLD_LINES:
                    self.assertNotIn(
                        old, line,
                        f"{who.key} was told a retired line: {line}")

    def assert_hold_released(self):
        """Neither side still believes in the hold.

        Read defensively on the actor's side: a made gap jump takes the
        jumper out of the handler entirely (`remove_combatant`), so an
        entry that is gone is an entry that holds nobody. The VICTIM's
        entry always survives, and half a grapple -- a victim still
        flagged as held by somebody who has left -- is the state this
        control exists to catch.
        """
        victim = self.maybe_entry(self.B)
        self.assertIsNotNone(victim, "fixture: the victim left the fight")
        self.assertIsNone(victim.get(DB_GRAPPLED_BY_DBREF))
        actor = self.maybe_entry(self.A)
        if actor is not None:
            self.assertIsNone(actor.get(DB_GRAPPLING_DBREF))

    # ── the charge door ─────────────────────────────────────────────

    def charge(self, *, cross_room=False):
        """Drive `resolve_charge` -- what the handler calls when the
        queued charge comes round. The rolls are decided by motorics:
        `randint` returns its own upper bound, so Alpha's 100 beats
        Cassidy's 1."""
        if cross_room:
            self.C.location = self.room2
            managed = list(self.handler.db.managed_rooms or [])
            if self.room2 not in managed:
                managed.append(self.room2)
            self.handler.db.managed_rooms = managed
        lst = self.handler.db.combatants
        entry = next(e for e in lst if e.get(DB_CHAR) == self.A)
        entry[DB_COMBAT_ACTION] = COMBAT_ACTION_CHARGE
        entry[DB_COMBAT_ACTION_TARGET] = self.C
        with contextlib.ExitStack() as stack:
            for module in (dice, movement_resolution):
                stack.enter_context(
                    mock.patch.object(module, "randint", lambda lo, hi: hi))
            stack.enter_context(
                mock.patch.object(movement_resolution, "msg_room_identity"))
            for door in ("commands.explosion_utils.check_rigged_grenade",
                         "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(door))
            room = stack.enter_context(
                mock.patch.object(grappling, "msg_room_identity"))
            movement_resolution.resolve_charge(
                self.handler, self.A, entry, lst)
        return room


# ── (a) the charge doors ────────────────────────────────────────────

class TestChargingSomeoneElseNamesThemPerAudience(_AHoldInARoom):
    """Same room: the charger lets go of the victim and goes for a third
    party, and all three audiences are told WHO."""

    def expected_actor(self):
        return [_actor_line(v,
                            target_name=get_display_name_safe(self.B, self.A),
                            charge_target=ACTOR_SEES)
                for v in MESSAGES["release_charge"]]

    def expected_victim(self):
        return [_victim_line(v,
                             attacker_name=get_display_name_safe(self.A, self.B),
                             charge_target=VICTIM_SEES)
                for v in MESSAGES["release_charge"]]

    def test_the_charger_reads_a_release_charge_line(self):
        self.charge()
        self.assert_beat(self.A, self.expected_actor(), "the charger")
        self.assert_no_old_line()

    def test_the_charger_reads_their_own_name_for_the_person_charged(self):
        self.charge()
        self.assertIn(ACTOR_SEES, self.text(self.A))
        self.assertNotIn(VICTIM_SEES, self.text(self.A),
                         "the charger was handed the victim's view of the "
                         "person they are charging")

    def test_the_victim_reads_the_same_beat_with_their_own_name_for_them(self):
        self.charge()
        self.assert_beat(self.B, self.expected_victim(), "the released victim")
        self.assertIn(VICTIM_SEES, self.text(self.B))
        self.assertNotIn(ACTOR_SEES, self.text(self.B),
                         "the victim was handed the charger's view of the "
                         "person being charged")

    def test_both_sides_were_told_the_same_variant(self):
        self.charge()
        self.assertTrue(
            self.assert_beat(self.A, self.expected_actor(), "actor")
            & self.assert_beat(self.B, self.expected_victim(), "victim"),
            "the two halves of one beat came from different variants")

    def test_the_room_keeps_the_third_party_for_its_own_resolution(self):
        room = self.charge()
        self.assertTrue(room.called, "the room was told nothing")
        kwargs = room.call_args.kwargs
        self.assertIn("{charge_target}", kwargs["template"],
                      "the room template resolved the third party at send "
                      "time instead of leaving it per observer")
        self.assertIn(kwargs["template"],
                      [_room_template(v) for v in MESSAGES["release_charge"]],
                      f"the room got a template outside the bank: "
                      f"{kwargs['template']}")

    def test_the_room_is_handed_the_third_party_object(self):
        room = self.charge()
        refs = room.call_args.kwargs["char_refs"]
        self.assertIs(refs["charge_target"], self.C)
        self.assertIs(refs["actor"], self.A)
        self.assertIs(refs["target_char"], self.B)
        self.assertEqual(set(room.call_args.kwargs["exclude"]),
                         {self.A, self.B})
        self.assertIs(room.call_args.kwargs["location"], self.room1)

    def test_the_hold_really_ended(self):
        """Control: without it every assertion above could be passing on
        a door that was never reached."""
        self.charge()
        self.assert_hold_released()


class TestChargingOutOfTheRoomNamesNobodyElse(_AHoldInARoom):
    """Cross-room: the charger is gone before the victim could see who
    they went for, so the bank's away-variants name nobody."""

    def expected_actor(self):
        return [_actor_line(v,
                            target_name=get_display_name_safe(self.B, self.A),
                            charge_target=ACTOR_SEES)
                for v in MESSAGES["release_charge_away"]]

    def expected_victim(self):
        return [_victim_line(v,
                             attacker_name=get_display_name_safe(self.A, self.B),
                             charge_target=VICTIM_SEES)
                for v in MESSAGES["release_charge_away"]]

    def test_the_charger_reads_a_release_charge_away_line(self):
        self.charge(cross_room=True)
        self.assert_beat(self.A, self.expected_actor(), "the charger")
        self.assert_no_old_line()

    def test_the_victim_reads_it_from_their_side(self):
        self.charge(cross_room=True)
        self.assert_beat(self.B, self.expected_victim(), "the released victim")

    def test_the_victim_is_told_nothing_about_a_third_party(self):
        """The person dropped is the one who cannot see where their
        captor went. Bound on the victim, whose only line in this beat
        IS the release -- the charger's own text goes on to name the
        person they crashed into, which is the charge speaking, not the
        hold ending."""
        self.charge(cross_room=True)
        self.assertNotIn(ACTOR_SEES, self.text(self.B))
        self.assertNotIn(VICTIM_SEES, self.text(self.B))

    def test_the_away_variants_name_nobody_to_name(self):
        """The same claim at the bank: there is no `{charge_target}` in
        any away variant to render for any audience."""
        bad = [f"release_charge_away[{i}].{key}"
               for i, variant in enumerate(MESSAGES["release_charge_away"])
               for key in ("attacker_msg", "victim_msg", "observer_msg")
               if "{charge_target}" in variant[key]]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_the_room_template_carries_no_third_party(self):
        room = self.charge(cross_room=True)
        self.assertTrue(room.called, "the room was told nothing")
        kwargs = room.call_args.kwargs
        self.assertNotIn("{charge_target}", kwargs["template"])
        self.assertNotIn("charge_target", kwargs["char_refs"])
        self.assertIn(kwargs["template"],
                      [_room_template(v)
                       for v in MESSAGES["release_charge_away"]])

    def test_the_hold_really_ended(self):
        self.charge(cross_room=True)
        self.assert_hold_released()

    def test_the_room_that_watched_the_hold_hears_it_end(self):
        """The charger leaves the room in the same resolution. The beat
        must land where the hold was, not where the charger arrives:
        the release fires BEFORE the move (review of #3615), so the
        broadcast's location is the origin room, and afterwards the
        charger stands in the other one."""
        room = self.charge(cross_room=True)
        self.assertTrue(room.called, "the room was told nothing")
        self.assertIs(room.call_args.kwargs["location"], self.room1)
        self.assertIs(self.A.location, self.room2)


# ── (b) the two jump doors ──────────────────────────────────────────

class _AHoldAtTheEdge(_AHoldInARoom):
    """The same hold, on a roof with a gap to leap and a grenade to land
    on. `roll_to_disengage` is pinned won: the price of leaving a fight
    at the edge is another module's subject (#3583), and a jumper caught
    on the way out never reaches either door."""

    def setUp(self):
        super().setUp()
        self.gap = self.exit
        self.gap.key = "east"
        self.gap.db.is_gap = True
        self.far = create_object("typeclasses.rooms.Room", key="Far Roof")
        self.gap.db.gap_destination = self.far

    @contextlib.contextmanager
    def _quiet_jump(self):
        import world.gravity as gravity
        with contextlib.ExitStack() as stack:
            for target in ("commands.combat.jump.msg_room_identity",
                           "commands.combat.jump.clear_aim_state",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch.object(gravity, "msg_room_identity"))
            stack.enter_context(mock.patch.object(gravity, "delay"))
            stack.enter_context(mock.patch(
                "commands.combat.movement.roll_to_disengage",
                return_value=(True, None, [])))
            yield stack.enter_context(
                mock.patch.object(grappling, "msg_room_identity"))

    def leap(self):
        from commands.combat.jump import CmdJump

        cmd = CmdJump()
        cmd.caller = self.A
        cmd.direction = "east"
        with self._quiet_jump() as room:
            with mock.patch("commands.combat.jump.standard_roll",
                            return_value=(999, 999, 999)):
                cmd.handle_gap_jump()
        return room

    def grenade(self):
        obj = create_object("typeclasses.items.Item", key="grenade",
                            location=self.room1)
        obj.db.is_explosive = True
        obj.db.pin_pulled = True
        obj.db.blast_damage = 1
        obj.db.damage_type = "blast"
        setattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 3)
        # The arming path always leaves this key behind; the sacrifice
        # path deletes it unconditionally.
        setattr(obj.ndb, NDB_GRENADE_TIMER, None)
        return obj

    def land_on_the_grenade(self):
        """Production reaches the blast door through a delayed
        revelation, so the test does too: `delay` is captured and its
        callback fired."""
        from commands.combat.jump import CmdJump

        self.grenade()
        cmd = CmdJump()
        cmd.caller = self.A
        cmd.explosive_name = "grenade"
        with self._quiet_jump() as room:
            with mock.patch("commands.combat.jump.delay") as scheduled:
                cmd.handle_explosive_sacrifice()
            self.assertTrue(scheduled.called,
                            "no revelation was ever scheduled")
            reveal = scheduled.call_args.args[1]
            reveal()
        return room


class TestLeapingAGapSpeaksFromTheBank(_AHoldAtTheEdge):

    def expected_actor(self):
        return [_actor_line(v,
                            target_name=get_display_name_safe(self.B, self.A),
                            charge_target=ACTOR_SEES)
                for v in MESSAGES["release_jump"]]

    def expected_victim(self):
        return [_victim_line(v,
                             attacker_name=get_display_name_safe(self.A, self.B),
                             charge_target=VICTIM_SEES)
                for v in MESSAGES["release_jump"]]

    def test_the_jumper_reads_a_release_jump_line(self):
        self.leap()
        self.assert_beat(self.A, self.expected_actor(), "the jumper")
        self.assert_no_old_line()

    def test_the_dropped_victim_reads_it_from_their_side(self):
        self.leap()
        self.assert_beat(self.B, self.expected_victim(), "the dropped victim")

    def test_the_room_hears_it_per_observer(self):
        room = self.leap()
        self.assertTrue(room.called,
                        "the room still learns nothing when a hold is "
                        "dropped for a jump")
        template = room.call_args.kwargs["template"]
        self.assertIn(template, [_room_template(v)
                                 for v in MESSAGES["release_jump"]])
        self.assertEqual(room.call_args.kwargs["char_refs"],
                         {"actor": self.A, "target_char": self.B})

    def test_the_grip_really_opened(self):
        """Control: the real `break_grapple` ran, so the prose above was
        narrating an event rather than replacing one."""
        self.leap()
        self.assert_hold_released()


class TestABlastTearingThePairApartSpeaksFromTheBank(_AHoldAtTheEdge):

    def expected_actor(self):
        return [_actor_line(v,
                            target_name=get_display_name_safe(self.B, self.A),
                            charge_target=ACTOR_SEES)
                for v in MESSAGES["release_blast"]]

    def expected_victim(self):
        return [_victim_line(v,
                             attacker_name=get_display_name_safe(self.A, self.B),
                             charge_target=VICTIM_SEES)
                for v in MESSAGES["release_blast"]]

    def test_the_grappler_reads_a_release_blast_line(self):
        self.land_on_the_grenade()
        self.assert_beat(self.A, self.expected_actor(), "the hero")
        self.assert_no_old_line()

    def test_the_shielded_victim_reads_it_from_their_side(self):
        self.land_on_the_grenade()
        self.assert_beat(self.B, self.expected_victim(), "the human shield")

    def test_the_room_hears_it_per_observer(self):
        room = self.land_on_the_grenade()
        self.assertTrue(room.called,
                        "the room still learns nothing when a blast breaks "
                        "a hold")
        self.assertIn(room.call_args.kwargs["template"],
                      [_room_template(v) for v in MESSAGES["release_blast"]])


class TestTheRetiredSentencesAreGoneFromTheDoors(TestCase):
    """The helper is only the door if the doors call it. Bound off the
    source of the three files that used to write their own prose."""

    def _source(self):
        import commands.combat.jump as jump
        import commands.combat.movement as movement
        return {
            "commands/combat/jump.py": inspect.getsource(jump),
            "commands/combat/movement.py": inspect.getsource(movement),
            "world/combat/movement_resolution.py":
                inspect.getsource(movement_resolution),
        }

    def test_no_door_still_writes_its_own_sentence(self):
        bad = [f"{path}: {old}"
               for path, src in self._source().items()
               for old in OLD_LINES if old in src]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_each_door_asks_the_helper_for_its_phase(self):
        src = self._source()
        for path, phase in (
                ("commands/combat/jump.py", "release_jump"),
                ("commands/combat/jump.py", "release_blast"),
                ("commands/combat/movement.py", "release_intent"),
                ("world/combat/movement_resolution.py", "release_charge"),
                ("world/combat/movement_resolution.py",
                 "release_charge_away")):
            with self.subTest(f"{path}:{phase}"):
                self.assertIn("speak_grapple_beat", src[path])
                self.assertIn(f'"{phase}"', src[path])


# ── (c) the queue-time preview ──────────────────────────────────────

class TestTheQueuedChargeIsAnActorOnlyPreview(_AHoldInARoom):
    """`charge <someone else>` while holding a victim prints an
    intention, not an event: the hold does not end until the charge
    resolves, so only the person forming the intention hears it."""

    def queue_a_charge(self, args=ACTOR_SEES):
        from commands.combat.movement import CmdCharge

        cmd = CmdCharge()
        cmd.caller = self.A
        cmd.args = f" {args}"
        with mock.patch.object(grappling, "msg_room_identity") as room:
            cmd.func()
        return room

    def expected_actor(self):
        return [_actor_line(v,
                            target_name=get_display_name_safe(self.B, self.A),
                            charge_target=ACTOR_SEES)
                for v in MESSAGES["release_intent"]]

    def test_the_charger_reads_the_preview(self):
        self.queue_a_charge()
        self.assert_beat(self.A, self.expected_actor(), "the charger")
        self.assert_no_old_line()

    def test_it_names_the_person_about_to_be_charged(self):
        self.queue_a_charge()
        self.assertIn(ACTOR_SEES, self.text(self.A))

    def test_the_victim_is_told_nothing(self):
        """They have not been let go. Telling them so is a lie the old
        line did not tell either -- the preview must not become one."""
        self.queue_a_charge()
        self.assertEqual(self.told(self.B), [])

    def test_the_room_is_told_nothing(self):
        room = self.queue_a_charge()
        room.assert_not_called()

    def test_the_hold_is_still_held(self):
        """Control: a preview that ended the hold would be a bug the
        prose cannot see."""
        self.queue_a_charge()
        self.assertIs(self.handler.get_grappling_obj(self.entry(self.A)),
                      self.B)

    def test_the_charge_is_actually_queued(self):
        """Control: without it the four tests above pass on a command
        that refused the target and returned."""
        self.queue_a_charge()
        entry = self.entry(self.A)
        self.assertEqual(entry.get(DB_COMBAT_ACTION), COMBAT_ACTION_CHARGE)
        self.assertIs(entry.get(DB_COMBAT_ACTION_TARGET), self.C)

    def test_nobody_s_view_is_rendered_for_a_line_they_never_get(self):
        """Rendering a name through the identity system rolls -- and
        caches -- a disguise pierce for that observer. A preview only
        the charger reads must not spend the victim's roll against the
        third party, nor the victim's roll against the charger (review
        of #3615). The accessor renders only the audiences it is asked
        to deliver."""
        import world.combat.messages as messages
        seen = []
        real = messages.get_display_name_safe

        def recording(obj, observer, *a, **k):
            seen.append((obj, observer))
            return real(obj, observer, *a, **k)

        with mock.patch.object(messages, "get_display_name_safe", recording):
            self.queue_a_charge()
        self.assertNotIn((self.C, self.B), seen, "the victim's view of the third party was rendered")
        self.assertNotIn((self.A, self.B), seen, "the victim's view of the charger was rendered")
        self.assertIn((self.C, self.A), seen, "control: the charger's own view IS rendered")


# ── (d) the accessor's own contract ─────────────────────────────────

class TestTheAccessorRendersAThirdPartyPerAudience(_AHoldInARoom):

    def ask(self, phase="release_charge"):
        return get_combat_message("grapple", phase, attacker=self.A,
                                  target=self.B,
                                  extra_chars={"charge_target": self.C})

    def test_the_actor_line_uses_the_actors_view(self):
        msgs = self.ask()
        self.assertIn(ACTOR_SEES, msgs["attacker_msg"])
        self.assertNotIn(VICTIM_SEES, msgs["attacker_msg"])

    def test_the_victim_line_uses_the_victims_view(self):
        msgs = self.ask()
        self.assertIn(VICTIM_SEES, msgs["victim_msg"])
        self.assertNotIn(ACTOR_SEES, msgs["victim_msg"])

    def test_the_legacy_observer_line_uses_the_key(self):
        """The pre-resolved line is what a caller with no identity layer
        gets; it names the third party the same way it names the other
        two."""
        msgs = self.ask()
        self.assertIn(THIRD_PARTY_KEY, msgs["observer_msg"])

    def test_the_room_template_keeps_the_placeholder(self):
        msgs = self.ask()
        self.assertIn("{charge_target}", msgs["observer_template"])

    def test_the_room_refs_carry_the_object(self):
        msgs = self.ask()
        self.assertIs(msgs["observer_char_refs"]["charge_target"], self.C)
        self.assertIs(msgs["observer_char_refs"]["actor"], self.A)
        self.assertIs(msgs["observer_char_refs"]["target_char"], self.B)

    def test_a_phase_given_no_third_party_gains_no_ref(self):
        """Control: the refs grew because `extra_chars` was passed, not
        because the accessor now always adds the key."""
        msgs = get_combat_message("grapple", "release_charge_away",
                                  attacker=self.A, target=self.B)
        self.assertNotIn("charge_target", msgs["observer_char_refs"])


# ── (e) every authored variant ──────────────────────────────────────

class TestEveryNewVariantRenders(TestCase):
    """The accessor swallows a bad placeholder into
    `"(Error: Missing placeholder ...)"` and delivers THAT to the
    player, so a broken variant is invisible until someone reads it in
    play. All eleven are rendered here, one at a time."""

    def render(self, phase, index):
        with mock.patch("world.combat.messages.random.choice",
                        lambda seq, _i=index: seq[_i]):
            return get_combat_message(
                "grapple", phase, attacker=None, target=None,
                extra_chars={"charge_target": _Stranger()})

    def test_no_variant_names_anything_but_the_three_people(self):
        bad = []
        for phase in NEW_PHASES:
            for index, variant in enumerate(MESSAGES[phase]):
                for key in ("attacker_msg", "victim_msg", "observer_msg"):
                    stray = (set(re.findall(r"\{(\w+)\}", variant[key]))
                             - ALLOWED_PLACEHOLDERS)
                    if stray:
                        bad.append(f"{phase}[{index}].{key} names "
                                   f"{sorted(stray)}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_every_variant_formats_with_no_residual_braces(self):
        bad = []
        for phase in NEW_PHASES:
            for index in range(len(MESSAGES[phase])):
                msgs = self.render(phase, index)
                for key in ("attacker_msg", "victim_msg", "observer_msg"):
                    text = msgs[key]
                    if "{" in text or "}" in text or "Error:" in text:
                        bad.append(f"{phase}[{index}].{key}: {text}")
                leftover = set(re.findall(r"\{(\w+)\}",
                                          msgs["observer_template"]))
                stray = leftover - {"actor", "target_char", "charge_target"}
                if stray:
                    bad.append(f"{phase}[{index}].observer_template leaves "
                               f"{sorted(stray)}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_the_third_party_actually_reaches_the_prose(self):
        used = [(phase, i)
                for phase in NEW_PHASES
                for i, v in enumerate(MESSAGES[phase])
                if "{charge_target}" in v["attacker_msg"]]
        self.assertTrue(used, "no new variant names the person charged")
        for phase, index in used:
            self.assertIn(THIRD_PARTY_KEY,
                          self.render(phase, index)["attacker_msg"])

    def test_the_preview_has_nothing_to_say_to_anyone_else(self):
        """`release_intent` is authored with two empty strings, and an
        empty message comes back empty -- uncoloured, unformatted, and
        so never sent."""
        for index in range(len(MESSAGES["release_intent"])):
            msgs = self.render("release_intent", index)
            self.assertTrue(msgs["attacker_msg"])
            self.assertEqual(msgs["victim_msg"], "")
            self.assertEqual(msgs["observer_msg"], "")
            self.assertEqual(msgs["observer_template"], "")

    def test_the_pin_really_walks_the_bank(self):
        """Guards the guard: if the `random.choice` pin stopped
        selecting, the sweeps above would render one variant eleven
        times and prove nothing."""
        for phase in NEW_PHASES:
            rendered = {self.render(phase, i)["attacker_msg"]
                        for i in range(len(MESSAGES[phase]))}
            self.assertEqual(len(rendered), len(MESSAGES[phase]),
                             f"the {phase} sweep did not visit every variant")


# ── (f) colour ──────────────────────────────────────────────────────

class TestALostGripIsYellow(TestCase):
    """A hold taken or let go on purpose is green; one that fails, or is
    torn away, is yellow -- the colour the old hardcoded lines at all
    four doors already wore."""

    def render(self, phase, index):
        with mock.patch("world.combat.messages.random.choice",
                        lambda seq, _i=index: seq[_i]):
            return get_combat_message(
                "grapple", phase, attacker=None, target=None,
                extra_chars={"charge_target": _Stranger()})

    def test_every_new_line_comes_back_yellow(self):
        bad = []
        for phase in NEW_PHASES:
            for index in range(len(MESSAGES[phase])):
                msgs = self.render(phase, index)
                for key in ("attacker_msg", "victim_msg", "observer_msg",
                            "observer_template"):
                    text = msgs[key]
                    if not text:
                        continue
                    if not (text.startswith(LOST_GRIP) and text.endswith("|n")):
                        bad.append(f"{phase}[{index}].{key}: {text}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_an_empty_line_is_never_painted(self):
        """A colour code wrapped around nothing is a line: it would be
        delivered, and the victim of a queued charge would read a blink
        of yellow saying they had been let go."""
        msgs = self.render("release_intent", 0)
        self.assertEqual(msgs["victim_msg"], "")
        self.assertNotIn("|y", msgs["victim_msg"])


# ── (g) controls ────────────────────────────────────────────────────

class TestTheDeliberateReleaseIsUnchanged(_AHoldInARoom):
    """The phase that was already wired must render exactly as it did:
    green, all three audiences, nothing about a third party."""

    def test_a_chosen_release_is_still_green(self):
        msgs = get_combat_message("grapple", "release", attacker=self.A,
                                  target=self.B)
        self.assertTrue(msgs["attacker_msg"].startswith("|g"))
        self.assertTrue(msgs["attacker_msg"].endswith("|n"))
        self.assertNotIn("charge_target", msgs["observer_char_refs"])

    def test_the_helper_still_tells_all_three_by_default(self):
        with mock.patch.object(grappling, "msg_room_identity") as room:
            grappling.speak_grapple_beat(self.A, self.B, "release")
        self.assertTrue(self.told(self.A), "the actor was told nothing")
        self.assertTrue(self.told(self.B), "the victim was told nothing")
        room.assert_called_once()

    def test_audiences_narrows_delivery_on_a_phase_that_has_all_three(self):
        """The narrowing is `audiences`, not the empty strings the
        preview happens to be authored with: a phase with three real
        lines and an actor-only audience still reaches one person."""
        with mock.patch.object(grappling, "msg_room_identity") as room:
            grappling.speak_grapple_beat(self.A, self.B, "release",
                                         audiences=("actor",))
        self.assertTrue(self.told(self.A))
        self.assertEqual(self.told(self.B), [])
        room.assert_not_called()

    def test_the_helper_is_public_now(self):
        """Three modules outside `grappling` import it by name; a
        rename back behind an underscore breaks them silently at import
        time inside a function body."""
        self.assertTrue(callable(getattr(grappling, "speak_grapple_beat",
                                         None)))
        self.assertIsNone(getattr(grappling, "_say_from_bank", None))
