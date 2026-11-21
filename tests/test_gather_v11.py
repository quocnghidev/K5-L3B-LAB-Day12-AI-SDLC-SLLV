"""Gather v1.1 (Ticket-02 mục 1.1, 1.2, 4.5): đàn cá bơi/sinh và Cá Sấu. Hộp đen qua headless."""

import json
import math
import unittest

from helpers import Workdir, close, events, frames, items, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    G = json.load(_f)["tuning"]["gather"]
SP = G["monsters"]["species"]["ca_sau"]


def run(w, scenario=None, inputs=None, ticks=10, every=1, seed=1, out="o.jsonl", expect=0):
    args = ["--mode", "gather", "--seed", str(seed), "--ticks", str(ticks), "--out", w.path(out),
            "--snapshot-every", str(every)]
    if scenario is not None:
        args += ["--scenario", write_json(w.path("sc.json"), {"gather": scenario})]
    if inputs is not None:
        args += ["--inputs", write_json(w.path("in.json"), inputs)]
    code, err = run_headless(*args)
    assert code == expect, (code, err)
    return read_jsonl(w.path(out)) if expect == 0 else None


def ev(rows, name):
    return [(r["tick"], r["data"]) for r in events(rows, name)]


def snap(rows):
    return {s["tick"]: s for s in snapshots(rows)}


NO_MON = {"monsters": []}


class InitialFish(unittest.TestCase):
    def test_eight_schools_on_distinct_standard_points(self):
        with Workdir() as w:
            fish = snapshots(run(w, ticks=0))[0]["fish"]
            self.assertEqual(len(fish), G["fish_initial"])
            self.assertEqual([f["id"] for f in fish], [f"F{i}" for i in range(1, 9)])
            self.assertEqual(len({tuple(f["pos"]) for f in fish}), len(fish))
            for f in fish:
                self.assertIn(f["pos"][0], G["fish_spawn_x"])
                self.assertIn(f["pos"][1], G["fish_spawn_depths"][f["kind"]])
                self.assertEqual(f["age_ticks"], 0)

    def test_same_seed_same_bytes_different_seed_differs(self):
        with Workdir() as w:
            run(w, ticks=800, every=10, seed=4, out="a.jsonl")
            run(w, ticks=800, every=10, seed=4, out="b.jsonl")
            run(w, ticks=800, every=10, seed=5, out="c.jsonl")
            def read(n):
                with open(w.path(n), "rb") as f:
                    return f.read()
            a, b, c = read("a.jsonl"), read("b.jsonl"), read("c.jsonl")
            self.assertEqual(a, b)
            self.assertNotEqual(a, c)


class Swimming(unittest.TestCase):
    def fish(self, **kw):
        f = {"id": "F1", "kind": "ca_loc", "pos": [50, 15], "heading_deg": 0}
        f.update(kw)
        return f

    def test_speed_and_age(self):
        with Workdir() as w:
            rows = run(w, dict(NO_MON, fish=[self.fish()]), ticks=60)
            f = snap(rows)[60]["fish"][0]
            self.assertTrue(close(f["pos"][0], 50 + G["fish_speed"], 0.01), f)
            self.assertEqual(f["age_ticks"], 60)

    def test_reflect_at_edge_flips_heading(self):
        with Workdir() as w:
            rows = run(w, dict(NO_MON, fish=[self.fish(pos=[95.99, 15])]), ticks=1)
            f = snap(rows)[1]["fish"][0]
            self.assertTrue(close(f["pos"][0], 96 - (95.99 + G["fish_speed"] / 60 - 96), 0.001), f)
            self.assertTrue(close(f["heading_deg"], 180, 0.001), f)

    def test_depth_band_kept(self):
        with Workdir() as w:
            rows = run(w, dict(NO_MON, fish=[self.fish(pos=[50, 19.99], heading_deg=90)]), ticks=30)
            for s in snapshots(rows):
                lo, hi = G["fish_depths"]["ca_loc"]
                self.assertTrue(lo <= s["fish"][0]["pos"][1] <= hi)

    def test_turn_on_swim_step_120(self):
        with Workdir() as w:
            rows = run(w, dict(NO_MON, fish=[self.fish(age_ticks=118)]), ticks=2)
            s = snap(rows)
            self.assertEqual(s[1]["fish"][0]["heading_deg"], 0)
            self.assertNotEqual(s[2]["fish"][0]["heading_deg"], 0)

    def test_random_fish_false_keeps_fixture_still(self):
        with Workdir() as w:
            rows = run(w, dict(NO_MON, fish=[self.fish()], random_fish=False), ticks=400, every=400)
            f = snapshots(rows)[-1]["fish"]
            self.assertEqual([(x["pos"], x["age_ticks"]) for x in f], [([50, 15], 0)])
            self.assertEqual(events(rows, "fish_spawned"), [])

    def test_catch_uses_position_before_swimming(self):
        with Workdir() as w:
            # cá ở x=20 bơi +x; người ở x=18 (đúng mép 2.0 m trước khi cá bơi)
            sc = dict(NO_MON, fish=[self.fish(pos=[20, 10])], player={"pos": [18, 10]})
            rows = run(w, sc, frames({"tick": 0, "catch": True}), ticks=1)
            self.assertEqual(ev(rows, "fish_caught"), [(1, {"fish_id": "F1", "kind": "ca_loc", "yield": 1})])


class Spawning(unittest.TestCase):
    def test_spawn_every_360_ticks_with_new_id(self):
        with Workdir() as w:
            sc = dict(NO_MON, fish=[{"id": "F7", "kind": "ca_linh", "pos": [50, 7]}])
            rows = run(w, sc, ticks=721, every=360)
            sp = ev(rows, "fish_spawned")
            self.assertEqual([t for t, _ in sp], [360, 720])
            self.assertEqual([d["id"] for _, d in sp], ["F8", "F9"])
            for _, d in sp:
                self.assertIn(d["pos"][0], G["fish_spawn_x"])
                self.assertIn(d["pos"][1], G["fish_spawn_depths"][d["kind"]])
            spawned = [f for f in snap(rows)[360]["fish"] if f["id"] == "F8"][0]
            self.assertEqual(spawned["age_ticks"], 0)  # tham gia bơi từ bước sau

    def test_no_spawn_at_cap(self):
        with Workdir() as w:
            fish = [{"id": f"F{i}", "kind": "ca_keo", "pos": [5 + 7 * i, 25]} for i in range(1, G["fish_max"] + 1)]
            rows = run(w, dict(NO_MON, fish=fish), ticks=361, every=361)
            self.assertEqual(events(rows, "fish_spawned"), [])


class Crocodile(unittest.TestCase):
    def test_default_day1_layout_only_m1(self):
        with Workdir() as w:
            mons = snapshots(run(w, ticks=0))[0]["monsters"]
            self.assertEqual([(m["id"], m["pos"], m["target_idx"], m["state"]) for m in mons],
                             [("M1", [60, 24], 1, "patrol")])

    def test_patrol_speed_and_turn_at_waypoint(self):
        with Workdir() as w:
            rows = run(w, {"random_fish": False}, ticks=241, every=1)
            s = snap(rows)
            self.assertTrue(close(s[60]["monsters"][0]["pos"][0], 61, 0.01))
            self.assertEqual(s[240]["monsters"][0]["pos"], [64, 24])
            self.assertEqual(s[240]["monsters"][0]["target_idx"], 0)

    def test_chase_when_deep_and_close_only(self):
        with Workdir() as w:
            rows = run(w, {"random_fish": False, "player": {"pos": [70, 24]}}, ticks=1)
            m = snap(rows)[1]["monsters"][0]
            self.assertEqual(m["state"], "chase")
            self.assertTrue(close(m["pos"][0], 60 + SP["chase_speed"] / 60, 0.001))
            rows = run(w, {"random_fish": False, "player": {"pos": [60, 9]}}, ticks=1)
            self.assertEqual(snap(rows)[1]["monsters"][0]["state"], "patrol")

    def test_hit_loses_hp_half_hold_lifo_and_recoils(self):
        with Workdir() as w:
            hold = items("ca_loc", "bong_sung", "ca_linh", "ca_linh", "keo_neo")
            sc = {"random_fish": False, "hold": hold, "player": {"pos": [61, 24]}}
            rows = run(w, sc, ticks=62)
            hit = ev(rows, "monster_hit")
            self.assertEqual(len(hit), 1)
            t, d = hit[0]
            self.assertEqual((t, d["monster_id"], d["hp"], [x["id"] for x in d["lost"]]), (1, "M1", 2, ["I5", "I4"]))
            s = snap(rows)
            self.assertEqual([x["id"] for x in s[1]["hold"]], ["I1", "I2", "I3"])
            self.assertEqual(s[1]["player"]["invuln_ticks"], G["monsters"]["invuln_ticks"])
            m1 = s[1]["monsters"][0]
            self.assertEqual((m1["state"], m1["state_ticks_left"], m1["recoil_dir"]), ("recoil", SP["recoil_ticks"], [-1, 0]))
            step = SP["recoil_dist"] / SP["recoil_ticks"]
            self.assertTrue(close(s[2]["monsters"][0]["pos"][0], m1["pos"][0] - step, 0.001))
            self.assertEqual(s[61]["monsters"][0]["state"], "patrol")

    def test_no_hit_while_invulnerable_or_shallow(self):
        with Workdir() as w:
            rows = run(w, {"random_fish": False, "player": {"pos": [61, 24], "invuln_ticks": 50}}, ticks=5)
            self.assertEqual(events(rows, "monster_hit"), [])
            rows = run(w, {"random_fish": False, "player": {"pos": [60, 9.5]},
                           "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 10], "waypoints": [[60, 10], [60, 10]]}]},
                       ticks=5)
            self.assertEqual(events(rows, "monster_hit"), [])

    def test_faint_by_monster(self):
        with Workdir() as w:
            sc = {"random_fish": False, "hold": items("ca_loc", "bong_sung", "ca_linh"), "player": {"pos": [61, 24], "hp": 1}}
            rows = run(w, sc, ticks=10)
            self.assertEqual([x["id"] for x in ev(rows, "monster_hit")[0][1]["lost"]], ["I3"])
            faint = ev(rows, "faint")[0]
            self.assertEqual((faint[0], faint[1]["cause"], [x["id"] for x in faint[1]["lost"]]), (1, "monster", ["I2", "I1"]))
            self.assertEqual(ev(rows, "gather_end"), [(1, {"reason": "fainted", "inventory": {"items": []}})])

    def test_bad_monster_fixture_exit_2(self):
        bad = [{"id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]], "state": "recoil"},
               {"id": "M1", "kind": "rong", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]]},
               {"id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24]]}]
        for m in bad:
            with Workdir() as w:
                run(w, {"monsters": [m]}, ticks=0, expect=2)


if __name__ == "__main__":
    unittest.main()
