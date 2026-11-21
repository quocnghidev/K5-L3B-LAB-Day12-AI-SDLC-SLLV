"""Test luật gather (lát 1 + 2) theo PRD-0 mục F. Hộp đen: chạy headless, đọc JSONL / file kho."""

import json
import unittest

from helpers import Workdir, events, frames, items, kinds_of, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    G = json.load(_f)["tuning"]["gather"]
OXY = G["oxygen_max_s"] * 60


def run(w, scenario=None, inputs=None, ticks=600, inv=False, every=None):
    args = ["--mode", "gather", "--seed", "1", "--ticks", str(ticks), "--out", w.path("o.jsonl")]
    if scenario is not None:
        args += ["--scenario", write_json(w.path("sc.json"), {"gather": scenario})]
    if inputs is not None:
        args += ["--inputs", write_json(w.path("in.json"), inputs)]
    if inv:
        args += ["--inventory-out", w.path("inv.json")]
    if every:
        args += ["--snapshot-every", str(every)]
    code, err = run_headless(*args)
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def ev(rows, name):
    return [(r["tick"], r["data"]) for r in events(rows, name)]


class Oxygen(unittest.TestCase):
    def test_dive_and_surface_events(self):
        with Workdir() as w:
            sc = {"player": {"pos": [50, 0]}, "random_fish": False}
            inp = frames({"tick": 0, "move": [0, 1]}, {"tick": 30, "move": [0, -1]}, {"tick": 120, "move": [0, 0]})
            rows = run(w, sc, inp, ticks=200)
            dives, surfs = ev(rows, "dive"), ev(rows, "surface")
            self.assertEqual(len(dives), 1)
            self.assertEqual(len(surfs), 1)
            self.assertGreater(dives[0][1]["pos"][1], 0.5)
            self.assertLessEqual(surfs[0][1]["pos"][1], 0.5)

    def test_oxygen_drains_underwater_and_refills_at_surface(self):
        with Workdir() as w:
            sc = {"player": {"pos": [50, 10], "oxygen_ticks": 100}, "random_fish": False}
            rows = run(w, sc, None, ticks=10, every=1)
            self.assertEqual([s["player"]["oxygen_ticks"] for s in snapshots(rows)][:3], [100, 99, 98])
            sc = {"player": {"pos": [50, 0], "oxygen_ticks": 100}, "random_fish": False}
            rows = run(w, sc, None, ticks=3, every=1)
            self.assertEqual([s["player"]["oxygen_ticks"] for s in snapshots(rows)], [100, 106, 112, 118])

    def test_refill_clamped_at_max(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [50, 0], "oxygen_ticks": OXY - 2}}, None, ticks=2, every=1)
            self.assertEqual(snapshots(rows)[-1]["player"]["oxygen_ticks"], OXY)

    def test_oxygen_empty_event_once_and_first_choke_after_60_steps(self):
        with Workdir() as w:
            # oxy 3 ở tick 0: chạm 0 ở tick 3; ngạt đầu tiên ở tick 3 + 59 = 62
            sc = {"player": {"pos": [50, 10], "oxygen_ticks": 3}, "random_fish": False}
            rows = run(w, sc, None, ticks=200)
            self.assertEqual(ev(rows, "oxygen_empty"), [(3, {"oxygen_ticks": 0})])
            chokes = ev(rows, "choke")
            self.assertEqual(chokes[0], (62, {"hp": 2}))
            self.assertEqual(chokes[1], (122, {"hp": 1}))

    def test_faint_loses_hold_lifo_and_writes_empty_inventory(self):
        with Workdir() as w:
            sc = {"player": {"pos": [50, 10], "oxygen_ticks": 0, "hp": 1}, "hold": items("ca_loc", "bong_sung", "ca_linh"),
                  "random_fish": False}
            rows = run(w, sc, None, ticks=300, inv=True)
            self.assertEqual(ev(rows, "choke"), [(60, {"hp": 0})])
            faint = ev(rows, "faint")
            self.assertEqual([(t, d["cause"], d["hp"]) for t, d in faint], [(60, "choke", 0)])
            # v1.2: lost là mảng cá thể theo thứ tự bỏ LIFO (I3 vào giỏ sau cùng mất trước)
            self.assertEqual([x["id"] for x in faint[0][1]["lost"]], ["I3", "I2", "I1"])
            end = ev(rows, "gather_end")
            self.assertEqual(end, [(60, {"reason": "fainted", "inventory": {"items": []}})])
            self.assertEqual(rows[-1]["reason"], "fainted")
            with open(w.path("inv.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

    def test_surfacing_on_choke_step_saves_player(self):
        with Workdir() as w:
            # oxy 0, zero_oxy_ticks 59, ở d=1.0 bơi lên: bước 1 d giảm xuống ≤ 0.5 -> hồi oxy, không ngạt
            sc = {"player": {"pos": [50, 0.51], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "vel": [0, -4]},
                  "random_fish": False}
            inp = frames({"tick": 0, "move": [0, -1]})
            rows = run(w, sc, inp, ticks=5)
            self.assertEqual(ev(rows, "choke"), [])
            self.assertEqual(snapshots(rows)[-1]["player"]["hp"], 3)


class Gathering(unittest.TestCase):
    def test_gather_node_at_exact_radius_and_regrow(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 0]}, "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [22, 0]}],
                  "fish": [], "random_fish": False}
            inp = frames({"tick": 0, "interact": True}, {"tick": 1, "interact": False})
            rows = run(w, sc, inp, ticks=G["regrow_s"] * 60 + 5, inv=False)
            self.assertEqual(ev(rows, "gather")[0], (1, {"node_id": "N1", "kind": "bong_dien_dien", "amount": 1}))
            self.assertEqual(kinds_of(snapshots(rows)[1]["hold"]), ["bong_dien_dien"])
            self.assertEqual(ev(rows, "node_regrown")[0][0], 1 + G["regrow_s"] * 60)

    def test_node_out_of_radius_ignored(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 0]}, "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [22.1, 0]}],
                  "fish": [], "random_fish": False}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=3)
            self.assertEqual(ev(rows, "gather"), [])

    def test_nearest_node_then_lowest_id_on_tie(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 0]}, "random_fish": False,
                  "nodes": [{"id": "N10", "kind": "bong_sung", "pos": [21, 0]},
                            {"id": "N2", "kind": "bong_dien_dien", "pos": [19, 0]}]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=1)
            self.assertEqual(ev(rows, "gather")[0][1]["node_id"], "N2")

    def test_underwater_cannot_gather(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 1]}, "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20, 0]}],
                  "random_fish": False}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(ev(rows, "gather"), [])

    def test_hold_full_when_gathering(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 0]}, "hold": items(*["ca_loc"] * G["hold_capacity"]), "random_fish": False,
                  "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20, 0]}]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(ev(rows, "hold_full"), [(1, {"action": "gather", "node_id": "N1", "required": 1, "free": 0})])
            self.assertTrue(snapshots(rows)[-1]["nodes"][0]["ready"])


class Catching(unittest.TestCase):
    FISH = [{"id": "F1", "kind": "ca_linh", "pos": [20, 5]}, {"id": "F2", "kind": "ca_loc", "pos": [21, 5]}]

    def test_catch_nearest_adds_yield_removes_fish_and_cooldown(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 5]}, "fish": self.FISH, "random_fish": False, "nodes": []}
            inp = frames({"tick": 0, "catch": True}, {"tick": 1, "catch": False}, {"tick": 10, "catch": True})
            rows = run(w, sc, inp, ticks=40, every=1)
            self.assertEqual(ev(rows, "fish_caught")[0], (1, {"fish_id": "F1", "kind": "ca_linh", "yield": 3}))
            self.assertEqual(len(ev(rows, "fish_caught")), 1, "đang hồi chiêu 30 tick: lần bấm ở tick 10 bị bỏ qua")
            snap = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snap[1]["hold"], items("ca_linh", "ca_linh", "ca_linh"))  # mới bắt: fresh 100
            self.assertEqual([f["id"] for f in snap[1]["fish"]], ["F2"])
            self.assertEqual(snap[1]["player"]["catch_cd_ticks"], 30)

    def test_catch_again_after_cooldown(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 5]}, "fish": self.FISH, "random_fish": False, "nodes": []}
            inp = frames({"tick": 0, "catch": True}, {"tick": 1, "catch": False}, {"tick": 30, "catch": True})
            rows = run(w, sc, inp, ticks=40)
            self.assertEqual([t for t, _ in ev(rows, "fish_caught")], [1, 31])

    def test_catch_hold_full_keeps_fish_and_no_cooldown(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 5]}, "fish": self.FISH, "random_fish": False, "nodes": [],
                  "hold": items(*["bong_sung"] * (G["hold_capacity"] - 2))}
            rows = run(w, sc, frames({"tick": 0, "catch": True}), ticks=2)
            self.assertEqual(ev(rows, "hold_full"), [(1, {"action": "catch", "fish_id": "F1", "required": 3, "free": 2})])
            last = snapshots(rows)[-1]
            self.assertEqual(len(last["fish"]), 2)
            self.assertEqual(last["player"]["catch_cd_ticks"], 0)

    def test_no_fish_in_range_no_event_no_cooldown(self):
        with Workdir() as w:
            sc = {"player": {"pos": [50, 5]}, "fish": self.FISH, "random_fish": False, "nodes": []}
            rows = run(w, sc, frames({"tick": 0, "catch": True}), ticks=2)
            self.assertEqual(events(rows, "fish_caught"), [])
            self.assertEqual(snapshots(rows)[-1]["player"]["catch_cd_ticks"], 0)

    def test_cannot_catch_at_surface(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 0.5]}, "fish": [{"id": "F1", "kind": "ca_loc", "pos": [20, 1]}],
                  "random_fish": False, "nodes": []}
            rows = run(w, sc, frames({"tick": 0, "catch": True}), ticks=2)
            self.assertEqual(events(rows, "fish_caught"), [])


class Docking(unittest.TestCase):
    def test_dock_edge_beats_gather_and_writes_inventory(self):
        with Workdir() as w:
            # bến tâm [2,0], bán kính 3: đứng ở x=5 là đúng mép; nút N1 cũng ở cùng chỗ nhưng bến xét trước
            sc = {"player": {"pos": [5, 0]}, "hold": items("ca_loc"), "random_fish": False,
                  "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [5, 0]}]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=50, inv=True)
            self.assertEqual(ev(rows, "gather"), [])
            self.assertEqual(ev(rows, "gather_end"), [(1, {"reason": "docked", "inventory": {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 99.992}]}})])
            self.assertEqual(rows[-1]["reason"], "docked")

    def test_time_end_after_catch_keeps_new_fish(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 5]}, "time_left_ticks": 1, "random_fish": False, "nodes": [],
                  "fish": [{"id": "F1", "kind": "ca_loc", "pos": [20, 5]}]}
            rows = run(w, sc, frames({"tick": 0, "catch": True}), ticks=5, inv=True)
            self.assertEqual(ev(rows, "gather_end"), [(1, {"reason": "time", "inventory": {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}})])
            with open(w.path("inv.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100.0}]})


if __name__ == "__main__":
    unittest.main()
