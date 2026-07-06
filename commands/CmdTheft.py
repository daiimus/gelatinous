"""``steal`` / ``pickpocket`` — applied stealth (STEALTH_AND_DETECTION_SPEC §6.2).

Theft is the hide/search contest (world/stealth.py) pointed at taking things.
Same room is the only spatial gate — theft is a stealth move, not a combat one,
so it never requires proximity or an advance. A subdued / unconscious / dead
mark is free looting (the trust predicate). An awake mark is a contest whose
whole risk is *getting caught*: a botched lift spikes the victim and every
witness to Alert (keyed on the thief's apparent-uid — a disguise protects you)
and raises a sourceless disturbance so the block runs hot.
"""

from random import choice, randint

from evennia import Command

from world.consent import can_contest
from world.stealth import (
    AMBUSH_CONTEST_BONUS, ALERT, contest, is_ambush, set_awareness,
)


def _stealable_inventory(target):
    """Carried items only — not worn, not held. What a pickpocket's fingers
    can reach without a struggle."""
    worn = set()
    get_worn = getattr(target, "get_worn_items", None)
    if callable(get_worn):
        worn = {id(i) for i in (get_worn() or [])}
    held = {id(i) for i in (getattr(target, "hands", None) or {}).values() if i}
    return [obj for obj in target.contents
            if id(obj) not in worn and id(obj) not in held]


def _caught(thief, victim):
    """The lift failed and the mark noticed. Victim + everyone who can see
    the thief jump to Alert (recognition keys on apparent-uid), and a
    sourceless disturbance runs the block hot — a witnessed-but-unidentified
    theft is exactly the situational cause the hunt reads."""
    from world.perception import can_see
    room = thief.location
    set_awareness(victim, thief, ALERT)
    for obs in (room.contents if room else []):
        if obs is thief or obs is victim or not hasattr(obs, "get_sdesc"):
            continue
        try:
            if can_see(obs):
                set_awareness(obs, thief, ALERT)
        except Exception:  # noqa: BLE001
            continue
    # The report rides the REAL pipeline (RADIO_COMMS_SPEC / dispatch §5.1):
    # report_crime rolls the crowd-gated witness, who calls it in over an
    # actual walkie after the interdiction window — no magic radio. Empty
    # alley = no witness = the force never learns; and the thief gets the
    # window to silence the snitch. perp stays None by design: the theft is
    # witnessed-but-unidentified (the situational cause the hunt reads).
    try:
        from world.director.crime import report_crime
        report_crime("pickpocketing", room, perp=None)
    except Exception:  # noqa: BLE001 — dispatch down ≠ theft crash
        pass


class CmdSteal(Command):
    """
    Steal from someone — lift an item off them without their notice.

    Usage:
        steal <target>
        steal <item> from <target>

    ``steal <target>`` picks something at random from what they're carrying
    (not worn, not in-hand) — you don't need to know what they've got. If
    you DO know (you frisked them, someone tipped you, it's in plain sight),
    ``steal <item> from <target>`` lets you go for that piece specifically.

    Against an awake mark it's a contest — their notice against your nerve,
    helped by a crowd and by striking from concealment. Fail and they feel
    it: you're made, and so is anyone watching. A subdued, unconscious, or
    dead mark is simply looted.
    """

    key = "steal"
    locks = "cmd:all()"
    help_category = "General"

    def parse(self):
        raw = (self.args or "").strip()
        self.item_name = self.target_name = ""
        if " from " in raw:
            item, _, target = raw.partition(" from ")
            self.item_name, self.target_name = item.strip(), target.strip()
        else:
            self.target_name = raw

    def func(self):
        caller = self.caller
        if not self.target_name:
            caller.msg("Steal from whom?")
            return
        target = caller.search(self.target_name)
        if not target:
            return
        if target is caller:
            caller.msg("You pat your own pockets. All present.")
            return
        if not hasattr(target, "get_sdesc"):
            caller.msg("You can't steal from that.")
            return

        inventory = _stealable_inventory(target)
        if self.item_name:
            item = caller.search(self.item_name, location=target, quiet=True)
            item = item[0] if isinstance(item, list) and item else item
            if not item or id(item) not in {id(i) for i in inventory}:
                # The precision path only works on what you can actually
                # reach — a named item you can't perceive isn't a free tell.
                caller.msg(f"You can't get at any '{self.item_name}' on "
                           f"{target.get_display_name(caller)}.")
                return
        else:
            if not inventory:
                caller.msg(f"{target.get_display_name(caller)} has nothing "
                           f"loose to lift.")
                return
            item = choice(inventory)

        self._lift(caller, target, item)

    def _lift(self, caller, target, item):
        # Free action on a mark who can't contest (trust predicate).
        if not can_contest(target):
            item.move_to(caller, quiet=True)
            caller.msg(f"You lift {item.get_display_name(caller)} off "
                       f"{target.get_display_name(caller)}.")
            return
        # Awake mark: a contest, ambush + crowd folded in by world.stealth.
        bonus = AMBUSH_CONTEST_BONUS if is_ambush(caller, target) else 0
        # Positive margin = the OBSERVER (victim) wins = the thief is caught.
        if contest(caller, target, hider_bonus=bonus) > 0:
            caller.msg(f"Your fingers find {item.get_display_name(caller)} — "
                       f"but {target.get_display_name(caller)} feels it.")
            target.msg(f"{caller.get_display_name(target)} is stealing "
                       f"from you!")
            _caught(caller, target)
            return
        item.move_to(caller, quiet=True)
        caller.msg(f"You lift {item.get_display_name(caller)} off "
                   f"{target.get_display_name(caller)}, clean.")


class CmdPickpocket(Command):
    """
    Pick someone's pocket for loose currency.

    Usage:
        pickpocket <target>

    A blind grab for tokens — you don't choose an amount, you lift what your
    fingers close on. Lower-stakes and more deniable than lifting a specific
    item. Same contest, same consequences if you're caught; a crowd and
    concealment both help.
    """

    key = "pickpocket"
    aliases = ["pick"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Pickpocket whom?")
            return
        target = caller.search(self.args.strip())
        if not target:
            return
        if target is caller:
            caller.msg("Your own tokens are right where you left them.")
            return
        if not hasattr(target, "get_sdesc"):
            caller.msg("That has no pockets.")
            return
        tokens = int(getattr(target.db, "tokens", 0) or 0)
        if tokens <= 0:
            caller.msg(f"{target.get_display_name(caller)} is carrying no "
                       f"tokens.")
            return

        lift = min(tokens, randint(1, max(1, tokens // 3)))

        if not can_contest(target):
            self._transfer(caller, target, lift)
            caller.msg(f"You lift {lift} tokens off "
                       f"{target.get_display_name(caller)}.")
            return
        bonus = AMBUSH_CONTEST_BONUS if is_ambush(caller, target) else 0
        if contest(caller, target, hider_bonus=bonus) > 0:
            caller.msg(f"Your hand's in {target.get_display_name(caller)}'s "
                       f"pocket when they turn — caught.")
            target.msg(f"{caller.get_display_name(target)} has a hand in "
                       f"your pocket!")
            _caught(caller, target)
            return
        self._transfer(caller, target, lift)
        caller.msg(f"You lift {lift} tokens off "
                   f"{target.get_display_name(caller)}, clean.")

    @staticmethod
    def _transfer(caller, target, amount):
        target.db.tokens = int(getattr(target.db, "tokens", 0) or 0) - amount
        caller.db.tokens = int(getattr(caller.db, "tokens", 0) or 0) + amount
