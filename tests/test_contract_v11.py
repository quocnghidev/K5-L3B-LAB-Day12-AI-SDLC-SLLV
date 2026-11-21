"""Dữ liệu chuẩn Ticket-02 (Test Contract v1.1) trong game.contract.json và các nguyên liệu mới."""

import json
import unittest

from helpers import Workdir, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    C = json.load(_f)
T = C["tuning"]


class StandardData(unittest.TestCase):
    def test_version_and_rooms(self):
        self.assertEqual(C["contract_version"], "1.3")  # Ticket-04 nâng lên v1.3 (thêm bench/soak); dữ liệu v1.1 giữ nguyên
        self.assertEqual([s["id"] for s in T["quan"]["stoves"]], ["B1", "B2"])
        self.assertEqual([t["id"] for t in T["quan"]["tables"]], ["T1", "T2", "T3", "T4"])

    def test_menu_has_six_dishes(self):
        self.assertEqual(sorted(T["menu"]), sorted([
            "ca_loc_nuong_trui", "goi_bong_sung", "lau_ca_linh_dien_dien",
            "canh_chua_ca_loc", "ca_keo_nuong", "lau_mam"]))
        self.assertEqual(T["menu"]["lau_mam"], {"recipe": {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1},
                                                "cook_s": 12, "price": 200})

    def test_day_plan_ingredients_equal_recipes_times_portions(self):
        self.assertEqual([d["day"] for d in T["day_plan"]], [1, 2, 3, 4, 5])
        for d in T["day_plan"]:
            want = {}
            for dish, n in d["dishes"].items():
                for k, v in T["menu"][dish]["recipe"].items():
                    want[k] = want.get(k, 0) + v * n
            self.assertEqual(d["ingredients"], want, d["day"])

    def test_shop_upgrades(self):
        up = T["shop"]["upgrades"]
        self.assertEqual(T["shop"]["max_ticks"], 600)
        self.assertEqual([(u["level"], u["price"], u["oxygen_max_s"]) for u in up["oxygen"]], [(1, 200, 45), (2, 400, 60)])
        self.assertEqual([(u["level"], u["price"], u["hp_max"]) for u in up["hp"]], [(1, 250, 4), (2, 500, 5)])


class NewIngredients(unittest.TestCase):
    def test_quan_reads_inventory_with_new_kinds(self):
        with Workdir() as w:
            inv = write_json(w.path("inv.json"), {"items": [{"id": "I1", "kind": "ca_keo", "fresh": 100},
                                                            {"id": "I2", "kind": "ca_keo", "fresh": 50},
                                                            {"id": "I3", "kind": "keo_neo", "fresh": 100}]})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", inv,
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            stock = snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"]
            self.assertEqual([(x["id"], x["kind"]) for x in stock], [("I1", "ca_keo"), ("I2", "ca_keo"), ("I3", "keo_neo")])

    def test_gather_default_has_keo_neo_nodes(self):
        with Workdir() as w:
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "0", "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            nodes = snapshots(read_jsonl(w.path("g.jsonl")))[0]["nodes"]
            self.assertEqual([(n["id"], n["kind"]) for n in nodes if n["kind"] == "keo_neo"], [("N5", "keo_neo"), ("N6", "keo_neo")])


class ShopInputs(unittest.TestCase):
    def test_buy_only_on_its_frame_and_shop_done_edge(self):
        from chonoi.inputs import InputPlayer
        ip = InputPlayer([{"tick": 2, "buy": "oxygen", "shop_done": True}])
        s0, s1, s2, s3 = (ip.advance(k) for k in range(4))
        self.assertEqual([s.buy for s in (s0, s1, s2, s3)], [None, None, "oxygen", None])
        self.assertTrue(s2.pressed("shop_done"))
        self.assertFalse(s3.pressed("shop_done"))

    def test_bad_buy_exit_2_and_shop_inputs_ignored_in_gather(self):
        with Workdir() as w:
            for bad, code_want in (({"tick": 0, "buy": ""}, 2), ({"tick": 0, "buy": 3}, 2),
                                   ({"tick": 0, "buy": "hp", "shop_done": True}, 0)):
                inp = write_json(w.path("in.json"), {"frames": [bad]})
                code, _ = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2", "--inputs", inp,
                                       "--out", w.path("o.jsonl"))
                self.assertEqual(code, code_want, bad)


if __name__ == "__main__":
    unittest.main()
