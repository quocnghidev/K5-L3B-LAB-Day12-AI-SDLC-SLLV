"""Contract v1.2 (Ticket-03): kho cá thể, độ tươi trong giỏ, spoiled, file kho. Hộp đen qua headless."""

import json
import unittest

from helpers import Workdir, close, events, frames, items, read_jsonl, run_headless, snapshots, write_json

from chonoi.inventory import read_inventory, write_inventory
from chonoi.items import UNITS, new_item

NO_FISH = {"random_fish": False, "monsters": []}


def run(w, scenario, inputs=None, ticks=1, every=1, inv=False, expect=0):
    args = ["--mode", "gather", "--seed", "1", "--ticks", str(ticks), "--snapshot-every", str(every),
            "--scenario", write_json(w.path("sc.json"), {"gather": dict(NO_FISH, **scenario)}), "--out", w.path("o.jsonl")]
    if inputs is not None:
        args += ["--inputs", write_json(w.path("in.json"), inputs)]
    if inv:
        args += ["--inventory-out", w.path("inv.json")]
    code, err = run_headless(*args)
    assert code == expect, (code, err)
    return read_jsonl(w.path("o.jsonl")) if expect == 0 else None


class Threshold(unittest.TestCase):
    def test_ticket_example_fresh_30_spoils_on_first_step(self):
        with Workdir() as w:
            rows = run(w, {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 30}]})
            sp = events(rows, "spoiled")
            self.assertEqual([(e["tick"], e["phase"], e["data"]) for e in sp],
                             [(1, "gather", {"item_id": "I1", "kind": "ca_linh", "location": "hold"})])

    def test_spoiled_once_and_by_id(self):
        with Workdir() as w:
            hold = [{"id": "I10", "kind": "ca_loc", "fresh": 30}, {"id": "I2", "kind": "ca_linh", "fresh": 30},
                    {"id": "I3", "kind": "bong_sung", "fresh": 31}]
            rows = run(w, {"hold": hold}, ticks=200, every=200)
            sp = [(e["tick"], e["data"]["item_id"]) for e in events(rows, "spoiled")]
            # I3 từ 31 xuống < 30 cần 1 điểm = 240 đơn vị / 2 mỗi tick -> tick 121
            self.assertEqual(sp, [(1, "I2"), (1, "I10"), (121, "I3")])

    def test_just_above_threshold_not_spoiled(self):
        with Workdir() as w:
            rows = run(w, {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 30 + 2 / UNITS}]})
            self.assertEqual(events(rows, "spoiled"), [])
            self.assertEqual(snapshots(rows)[-1]["hold"][0]["fresh"], 30)


class Decay(unittest.TestCase):
    def test_hold_loses_half_point_per_second_and_clamps_at_zero(self):
        with Workdir() as w:
            rows = run(w, {"hold": items("ca_loc", "ca_linh", fresh=100) + [{"id": "I3", "kind": "keo_neo", "fresh": 0.004}]},
                       ticks=60, every=60)
            s = snapshots(rows)[-1]["hold"]
            self.assertEqual([x["fresh"] for x in s], [99.5, 99.5, 0])

    def test_new_item_starts_at_100_and_decays_from_next_step(self):
        with Workdir() as w:
            sc = {"player": {"pos": [20, 0]}, "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20, 0]}],
                  "hold": [{"id": "I7", "kind": "ca_loc", "fresh": 80}]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            s = {x["tick"]: x for x in snapshots(rows)}
            self.assertEqual(s[1]["hold"][1], {"id": "I8", "kind": "bong_sung", "fresh": 100})  # id nối sau I7
            self.assertTrue(close(s[2]["hold"][1]["fresh"], 100 - 2 / UNITS, 0.001))

    def test_pause_stops_decay(self):
        with Workdir() as w:
            rows = run(w, {"hold": items("ca_loc")}, frames({"tick": 0, "pause": True}), ticks=50, every=50)
            self.assertEqual(snapshots(rows)[-1]["hold"][0]["fresh"], 100)


class InventoryFile(unittest.TestCase):
    def test_count_schema_and_bad_items_exit_2(self):
        bad = [{"items": {"ca_loc": 1}}, {"items": [{"id": "I1", "kind": "ca_loc"}]},
               {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I1", "kind": "ca_linh", "fresh": 1}]},
               {"items": [{"id": "I1", "kind": "ca_la_lung", "fresh": 1}]},
               {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100.5}]}, {"items": [{"id": "", "kind": "ca_loc", "fresh": 1}]},
               {"items": [{"id": "I1", "kind": "ca_loc", "fresh": True}]}]
        for inv in bad:
            with Workdir() as w:
                p = write_json(w.path("inv.json"), inv)
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", p,
                                       "--out", w.path("q.jsonl"))
                self.assertEqual(code, 2, inv)

    def test_bad_scenario_hold_exit_2(self):
        for hold in (["ca_loc"], [{"id": "I1", "kind": "ca_loc", "fresh": -1}],
                     [{"id": "I1", "kind": "ca_loc", "fresh": 1}, {"id": "I1", "kind": "ca_loc", "fresh": 1}]):
            with Workdir() as w:
                run(w, {"hold": hold}, ticks=0, expect=2)

    def test_written_file_round_trips_exact_units_near_threshold(self):
        with Workdir() as w:
            its = [new_item("I2", "ca_linh", 30), new_item("I1", "ca_loc", 100)]
            its[0]["units"] -= 1  # 29.99583… : làm tròn 3 chữ số sẽ thành 29.996, phải giữ đúng nhánh ươn
            write_inventory(w.path("inv.json"), its)
            with open(w.path("inv.json"), encoding="utf-8") as f:
                self.assertEqual([x["id"] for x in json.load(f)["items"]], ["I1", "I2"])  # sắp theo id
            back = {x["id"]: x["units"] for x in read_inventory(w.path("inv.json"))}
            self.assertEqual(back, {"I1": 100 * UNITS, "I2": 30 * UNITS - 1})

    def test_dock_writes_items_after_one_decay(self):
        with Workdir() as w:
            rows = run(w, {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100}]},
                       frames({"tick": 0, "interact": True}), inv=True)
            with open(w.path("inv.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100 - 2 / UNITS}]})
            self.assertEqual(events(rows, "gather_end")[0]["data"]["inventory"]["items"][0]["id"], "I1")


if __name__ == "__main__":
    unittest.main()
