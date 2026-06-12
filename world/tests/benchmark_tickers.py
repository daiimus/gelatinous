"""Stress benchmark: per-character MedicalScript vs TickerHandler.

NOT part of the normal suite (filename doesn't match test_*.py, so
discovery skips it).  Run explicitly:

    evennia test --keepdb world.tests.benchmark_tickers

Everything runs inside the test database with per-test transaction
rollback — the live game is never touched.

What's measured per scale (10/100/500/1000 wounded characters):

* SCRIPT setup    — create_script(MedicalScript) for every character
                    (ScriptDB row each)
* SCRIPT tick-all — every script's at_repeat() back-to-back: this is
                    the worst-case synchronized slice (also exactly
                    what a TickerHandler subscription pass would do,
                    since the per-character work is identical)
* SCRIPT teardown — stop() + delete() for every script
* TICKER add      — TICKER_HANDLER.add() per character (note: the
                    handler re-serializes its whole storage blob to
                    ServerConfig on every add — suspected O(N²))
* TICKER remove   — symmetric removal
* TICKER blob     — persisted ServerConfig payload size at peak
"""

from __future__ import annotations

import time as _time

from evennia import TICKER_HANDLER, create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.medical.conditions import PainCondition
from world.medical.script import MedicalScript

SCALES = [10, 100, 500, 1000]


def _ms(seconds: float) -> str:
    return f"{seconds * 1000:8.1f}ms"


class BenchmarkTickers(EvenniaTest):
    character_typeclass = Character

    def _make_wounded(self, count, start_index):
        chars = []
        for i in range(count):
            char = create_object(
                Character, key=f"bench-{start_index + i}", location=None,
            )
            state = char.medical_state
            # Heavy enough pain that decay across passes never zeroes
            # it (a zeroed roster would let scripts self-delete and
            # skew teardown numbers).
            state.add_condition(PainCondition(10, location="chest"))
            chars.append(char)
        return chars

    def test_benchmark(self):
        results = []
        chars = []

        for scale in SCALES:
            # Grow the wounded population incrementally.
            t0 = _time.perf_counter()
            chars += self._make_wounded(scale - len(chars), len(chars))
            t_create = _time.perf_counter() - t0

            # ---------------- per-character scripts ----------------
            t0 = _time.perf_counter()
            scripts = [
                create_script(MedicalScript, obj=char) for char in chars
            ]
            t_script_setup = _time.perf_counter() - t0

            t0 = _time.perf_counter()
            for script in scripts:
                script.at_repeat()
            t_tick_all = _time.perf_counter() - t0

            t0 = _time.perf_counter()
            for script in scripts:
                if script.pk:
                    script.stop()
                    script.delete()
            t_script_teardown = _time.perf_counter() - t0

            # ---------------- TickerHandler subscriptions ----------
            t0 = _time.perf_counter()
            for char in chars:
                TICKER_HANDLER.add(
                    interval=60,
                    callback=char.save_medical_state,  # any typeclass method
                    idstring=f"bench-{char.id}",
                )
            t_ticker_add = _time.perf_counter() - t0

            blob = ""
            try:
                from evennia.server.models import ServerConfig
                blob = str(
                    ServerConfig.objects.conf(key="ticker_storage") or ""
                )
            except Exception:
                pass

            t0 = _time.perf_counter()
            for char in chars:
                TICKER_HANDLER.remove(
                    interval=60,
                    callback=char.save_medical_state,
                    idstring=f"bench-{char.id}",
                )
            t_ticker_remove = _time.perf_counter() - t0

            results.append(
                (scale, t_create, t_script_setup, t_tick_all,
                 t_script_teardown, t_ticker_add, t_ticker_remove,
                 len(blob))
            )

        print("\n")
        print(
            f"{'N':>5} | {'chars':>10} | {'scr setup':>10} | "
            f"{'tick-all':>10} | {'scr teardn':>10} | "
            f"{'tick add':>10} | {'tick rm':>10} | blob"
        )
        for (scale, t_create, t_setup, t_tick, t_teardown,
             t_add, t_rm, blob_len) in results:
            print(
                f"{scale:>5} | {_ms(t_create)} | {_ms(t_setup)} | "
                f"{_ms(t_tick)} | {_ms(t_teardown)} | "
                f"{_ms(t_add)} | {_ms(t_rm)} | {blob_len/1024:.0f}KB"
            )
        print()
        # Benchmarks don't assert — the numbers are the deliverable.
        self.assertTrue(results)
