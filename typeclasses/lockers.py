"""The locker bank — ONE integrated fixture that is the whole locker.

Modelled on ``typeclasses.bar.BarCounter``: an ``@integrate`` Item carrying
its own command set, so it needs no changes to core inventory (the game has
no generic ``put``, and ``get from`` isn't access-gated). Everything routes
through the bank's own verbs — ``rent``, ``locker`` (open/close/status),
``stash``, ``retrieve`` — each gated to the caller's SLEEVE.

Per-sleeve isolation: every lease gets its own hidden *compartment* object
nested inside the bank; stashed items live one level down, inside that
compartment, so the ungated core ``get <x> from lockers`` (which only reads
the bank's own contents) can never reach — or even see — another person's
things. You touch only your own locker; to everyone else it's a wall of
shut steel doors.

Economy: 100 tokens per week (``RENT``/``WEEK``); pay again to extend. Miss
it and the lease lapses, but you get a one-month grab window (``GRACE``)
before the house empties your locker into the lost-property bin.
"""
import time

from evennia import Command, CmdSet, create_object

from typeclasses.items import Item
from world.access import sleeve_uid_of

RENT = 100
WEEK = 7 * 24 * 3600
GRACE = 30 * 24 * 3600


def _uid(char):
    return sleeve_uid_of(char)


# --------------------------------------------------------------- the verbs
class _LockerCmd(Command):
    locks = "cmd:all()"
    help_category = "Bathhouse"

    @property
    def bank(self):
        return self.obj


class CmdLockerRent(_LockerCmd):
    """
    Lease a locker at the bank for a week.

    Usage:
        rent            (feeds 100 tokens into the slot; pay again to extend)
    """
    key = "rent"
    aliases = ["rent locker", "lease locker"]

    def func(self):
        self.bank.rent(self.caller)


class CmdLocker(_LockerCmd):
    """
    Your locker: check it, open it, or shut it.

    Usage:
        locker              show your locker (and its contents, if open)
        locker open         unlock and open it
        locker close        shut and lock it
    """
    key = "locker"
    aliases = ["check locker", "my locker"]

    def func(self):
        arg = self.args.strip().lower()
        if arg in ("open", "unlock"):
            self.bank.set_open(self.caller, True)
        elif arg in ("close", "shut", "lock"):
            self.bank.set_open(self.caller, False)
        else:
            self.caller.msg(self.bank.status_line(self.caller))


class CmdLockerStash(_LockerCmd):
    """
    Put something from your hands into your open locker.

    Usage:
        stash <item>
        put <item> in locker
    """
    key = "stash"
    aliases = ["deposit", "put"]

    def func(self):
        name = self.args.strip()
        for tail in (" in my locker", " in the locker", " in locker"):
            if name.lower().endswith(tail):
                name = name[: -len(tail)].strip()
        self.bank.stash(self.caller, name)


class CmdLockerRetrieve(_LockerCmd):
    """
    Take something out of your open locker.

    Usage:
        retrieve <item>
    """
    key = "retrieve"
    aliases = ["withdraw", "unstash"]

    def func(self):
        name = self.args.strip()
        for tail in (" from my locker", " from the locker", " from locker"):
            if name.lower().endswith(tail):
                name = name[: -len(tail)].strip()
        self.bank.retrieve(self.caller, name)


class LockerCmdSet(CmdSet):
    key = "locker_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdLockerRent())
        self.add(CmdLocker())
        self.add(CmdLockerStash())
        self.add(CmdLockerRetrieve())


# --------------------------------------------------------------- the fixture
class LockerBank(Item):
    """A wall of rentable lockers presented as one fixture."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.integrate = True
        self.locks.add("get:false()")
        self.cmdset.add(LockerCmdSet, persistent=True)
        self.db.leases = {}        # sleeve uid -> paid_until (epoch secs)
        self.db.opened = {}        # sleeve uid -> bool
        self.db.forfeit_bin = None
        self.db.integration_fallback = (
            "A wall of |cscuffed steel lockers|n stands along one side, most "
            "of them shut. A coin slot takes tokens; the doors answer sleeves. "
            "|wrent|n leases one for the week.")

    # -- compartments (per-sleeve, nested so core `get from` can't reach) --
    def _store(self, uid, create=False):
        if not uid:
            return None
        for o in self.contents:
            if o.db.locker_owner == uid:
                return o
        if create:
            s = create_object(Item, key="locker compartment", location=self)
            s.db.locker_owner = uid
            s.db.integrate = True
            s.locks.add("get:false()")
            return s
        return None

    def _prune(self):
        now = time.time()
        for uid, paid in list((self.db.leases or {}).items()):
            if now > paid + GRACE:
                self._repossess(uid)

    def _repossess(self, uid):
        store = self._store(uid)
        binx = self.db.forfeit_bin
        if store is not None:
            for it in list(store.contents):
                it.db.locker_owner = None
                if binx is not None:
                    it.move_to(binx, quiet=True, move_hooks=False)
            store.delete()
        leases = dict(self.db.leases or {}); leases.pop(uid, None)
        opened = dict(self.db.opened or {}); opened.pop(uid, None)
        self.db.leases, self.db.opened = leases, opened

    def _leased(self, caller):
        self._prune()
        return _uid(caller) in (self.db.leases or {})

    def _is_open(self, caller):
        return bool((self.db.opened or {}).get(_uid(caller)))

    def _contents_line(self, caller):
        store = self._store(_uid(caller))
        items = list(store.contents) if store is not None else []
        if not items:
            return "Your locker is empty."
        return ("Your locker holds: "
                + ", ".join(i.get_display_name(caller) for i in items) + ".")

    # -- verbs -----------------------------------------------------------
    def rent(self, caller):
        self._prune()
        uid = _uid(caller)
        if not uid:
            caller.msg("The slot can't read your sleeve.")
            return
        if int(getattr(caller, "tokens", 0) or 0) < RENT:
            caller.msg(f"A locker runs {RENT} tokens for the week — you're "
                       f"short.")
            return
        caller.tokens -= RENT
        now = time.time()
        leases = dict(self.db.leases or {})
        base = max(now, leases.get(uid, now))          # extend, don't reset
        renewing = uid in leases
        leases[uid] = base + WEEK
        self.db.leases = leases
        self._store(uid, create=True)
        caller.msg(f"You feed {RENT} tokens into the slot. "
                   + ("Your lease runs another week."
                      if renewing else
                      "A locker's yours for the week; it answers your sleeve now."))
        if caller.location:
            caller.location.msg_contents(
                f"{caller.get_display_name(caller)} leases a locker.",
                exclude=[caller])

    def set_open(self, caller, opened):
        if not self._leased(caller):
            caller.msg("You've no locker here. |wrent|n leases one.")
            return
        o = dict(self.db.opened or {}); o[_uid(caller)] = opened
        self.db.opened = o
        if opened:
            caller.msg("You put your sleeve to the plate and swing your "
                       "locker open. " + self._contents_line(caller))
        else:
            caller.msg("You shut your locker; it locks with a clack.")

    def _can_use(self, caller):
        if not self._leased(caller):
            caller.msg("You've no locker here. |wrent|n leases one.")
            return False
        if not self._is_open(caller):
            caller.msg("Your locker's shut — |wlocker open|n first.")
            return False
        return True

    def stash(self, caller, name):
        if not self._can_use(caller):
            return
        if not name:
            caller.msg("Stash what?")
            return
        item = caller.search(name, candidates=caller.contents,
                             nofound_string=f"You aren't carrying '{name}'.")
        if not item:
            return
        item.move_to(self._store(_uid(caller), create=True), quiet=True,
                     move_hooks=False)
        item.db.locker_owner = _uid(caller)
        caller.msg(f"You stow {item.get_display_name(caller)} in your locker.")

    def retrieve(self, caller, name):
        if not self._can_use(caller):
            return
        if not name:
            caller.msg("Retrieve what?")
            return
        store = self._store(_uid(caller))
        cands = list(store.contents) if store is not None else []
        item = caller.search(name, candidates=cands,
                             nofound_string=f"Your locker holds no '{name}'.")
        if not item:
            return
        item.db.locker_owner = None
        item.move_to(caller, quiet=True, move_hooks=False)
        caller.msg(f"You take {item.get_display_name(caller)} from your locker.")

    def status_line(self, caller):
        self._prune()
        uid = _uid(caller)
        leases = self.db.leases or {}
        if uid not in leases:
            return ("You've no locker here. |wrent|n leases one — 100 tokens "
                    "the week.")
        now, paid = time.time(), leases[uid]
        state = ("open" if self._is_open(caller) else "shut")
        if now <= paid:
            days = max(0, int((paid - now) // 86400))
            return (f"Your locker ({state}) is paid through about {days} more "
                    f"day(s). " + self._contents_line(caller))
        left = max(0, int((paid + GRACE - now) // 86400))
        return (f"|rYour locker's lease has LAPSED.|n About {left} day(s) to "
                f"clear it before the house empties it into lost property. "
                + self._contents_line(caller))

    def return_appearance(self, looker, **kwargs):
        self._prune()
        base = super().return_appearance(looker, **kwargs)
        uid = _uid(looker)
        if uid in (self.db.leases or {}):
            if self._is_open(looker):
                return f"{base}\n\n{self._contents_line(looker)}"
            return f"{base}\n\nYour locker here is shut."
        return base
