"""Every weapon message bank must be loadable (#2823).

`get_combat_message` reads `getattr(module, "MESSAGES", {})`. A bank that
exports its table under any other name returns `{}`, finds no templates,
and falls through to the generic fallback set — silently, because an
empty bank and a weapon that was never given one are indistinguishable
at that call site.

Four banks (scalpel, scimitar, semi-auto_rifle, streetlight) shipped with
their own `<WEAPON>_MESSAGES` name, so 478 authored lines were unreachable.
This pins the contract structurally rather than listing weapons, so a bank
added later under the wrong name fails here instead of going quiet.
"""

from __future__ import annotations

import importlib
import pkgutil
from unittest import TestCase

import world.combat.messages as messages_pkg

#: Modules in the package that are helpers, not banks.
_NOT_BANKS = {"severance"}

#: The phases `get_combat_message` asks for.
_CORE_PHASES = {"initiate", "hit", "miss", "kill"}


def _bank_modules():
    for mod in pkgutil.iter_modules(messages_pkg.__path__):
        if mod.name in _NOT_BANKS or mod.ispkg:
            continue
        yield mod.name


class TestEveryBankExportsMESSAGES(TestCase):
    def test_every_bank_exports_the_name_the_loader_reads(self):
        missing = []
        for name in _bank_modules():
            mod = importlib.import_module(f"world.combat.messages.{name}")
            table = getattr(mod, "MESSAGES", None)
            if not isinstance(table, dict) or not table:
                other = [n for n in vars(mod)
                         if n.isupper() and isinstance(vars(mod)[n], dict)]
                missing.append(f"{name} (exports {other or 'nothing'})")
        self.assertEqual(
            missing, [],
            "banks whose table the loader cannot see: " + ", ".join(missing),
        )

    def test_every_bank_offers_at_least_one_populated_phase(self):
        """A bank with no entries is a bank the loader will fall through.

        Deliberately NOT asserting the four core phases: `grapple` serves
        grapple/escape/release phases instead, which is correct for what
        it is. The contract is that a bank has something to return, not
        that every weapon fights the same way.
        """
        empty = []
        for name in _bank_modules():
            mod = importlib.import_module(f"world.combat.messages.{name}")
            table = getattr(mod, "MESSAGES", None) or {}
            if not any(entries for entries in table.values()):
                empty.append(name)
        self.assertEqual(empty, [], "banks with no usable entries: " + ", ".join(empty))

    def test_every_entry_carries_all_three_observer_roles(self):
        """A message that omits a role leaves that observer with nothing."""
        bad = []
        for name in _bank_modules():
            mod = importlib.import_module(f"world.combat.messages.{name}")
            for phase, entries in (getattr(mod, "MESSAGES", None) or {}).items():
                for i, entry in enumerate(entries or []):
                    if not isinstance(entry, dict):
                        continue
                    missing = {"attacker_msg", "victim_msg",
                               "observer_msg"} - set(entry)
                    if missing:
                        bad.append(f"{name}[{phase}][{i}] missing {sorted(missing)}")
        self.assertEqual(bad[:10], [], f"{len(bad)} incomplete message entries")
