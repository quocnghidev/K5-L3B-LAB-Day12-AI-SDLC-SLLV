"""Contract v1.3 (Ticket-04): bench_cmd, soak_cmd khai ở gốc manifest; soak 10 Ngày; bench.json đúng cấu trúc."""

import json
import shlex
import subprocess
import unittest

from helpers import ROOT, Workdir

from chonoi.bench import find_browser
from chonoi.contract import load_contract
from chonoi.sim.day import plan_for

with open(f"{ROOT}/game.contract.json", encoding="utf-8") as _f:
    C = json.load(_f)


def run_cmd(key, *args):
    p = subprocess.run([*shlex.split(C[key]), *args], cwd=ROOT, capture_output=True, text=True, timeout=180)
    return p.returncode, p.stdout + p.stderr


class Manifest(unittest.TestCase):
    def test_v13_declares_bench_and_soak(self):
        self.assertEqual(C["contract_version"], "1.3")
        for key in ("bench_cmd", "soak_cmd", "headless_cmd", "run_cmd", "build_cmd"):
            self.assertTrue(isinstance(C.get(key), str) and C[key], key)

    def test_plan_repeats_after_day_5(self):
        t = load_contract()["tuning"]
        for d in range(1, 6):
            self.assertEqual(plan_for(t, d + 5), plan_for(t, d))


class Soak(unittest.TestCase):
    def test_ten_days_no_crash_and_gameplay_deterministic(self):
        with Workdir() as w:
            outs = []
            for name in ("a.json", "b.json"):
                code, log = run_cmd("soak_cmd", "--seed", "7", "--days", "10", "--out", w.path(name))
                self.assertEqual(code, 0, log)
                with open(w.path(name), encoding="utf-8") as f:
                    outs.append(json.load(f))
            a, b = outs
            self.assertEqual(set(a), {"days", "days_completed", "crashes", "results", "duration_s"})
            self.assertEqual((a["days"], a["days_completed"], a["crashes"]), (10, 10, 0))
            self.assertEqual([r["day"] for r in a["results"]], list(range(1, 11)))
            for r in a["results"]:
                self.assertEqual(set(r), {"day", "earned", "reputation", "score"})
            self.assertEqual(a["results"], b["results"])  # bỏ duration_s (thời gian thực) khi so
            earned = [r["earned"] for r in a["results"]]
            self.assertEqual(earned, sorted(earned), "earned cộng dồn xuyên Ngày")

    def test_bad_args_exit_2(self):
        with Workdir() as w:
            self.assertEqual(run_cmd("soak_cmd", "--seed", "7", "--days", "0", "--out", w.path("s.json"))[0], 2)


@unittest.skipIf(find_browser() is None, "không có Chrome/Chromium để đo render")
class Bench(unittest.TestCase):
    def test_bench_json_has_five_fields(self):
        with Workdir() as w:
            code, log = run_cmd("bench_cmd", "--seed", "42", "--duration", "1", "--out", w.path("bench.json"))
            self.assertEqual(code, 0, log)
            with open(w.path("bench.json"), encoding="utf-8") as f:
                b = json.load(f)
            self.assertEqual(set(b), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
            self.assertGreater(b["frames"], 0)
            self.assertAlmostEqual(b["avg_fps"], b["frames"] / b["measured_s"], delta=0.05)
            self.assertLessEqual(b["p1_low_fps"], b["avg_fps"] + 0.01)
            self.assertGreater(b["load_ms"], 0)


if __name__ == "__main__":
    unittest.main()
