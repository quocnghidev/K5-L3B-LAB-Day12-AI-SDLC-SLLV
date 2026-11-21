"""Lát 4b (Ticket-02 mục 2, 4.2, 4.5): `--mode day`, đổi pha, pause.

Shop thật là lát 4a (`chonoi/sim/shop.py`); ở đây dùng FakeShop theo giao diện trong docs/contracts/README.md
mục 4 để kiểm đổi pha độc lập với Shop.
"""

import json
import unittest

from helpers import Workdir, events, frames, items, read_jsonl, run_headless, snapshots, write_json

from chonoi.contract import load_contract
from chonoi.inputs import InputPlayer
from chonoi.items import new_item, public_list
from chonoi.runner import run

TUNING = load_contract()["tuning"]


class FakeShop:
    mode = phase = "shop"

    def __init__(self, tuning, money, earned, reputation, upgrades, stock):
        self.money, self.earned, self.reputation = money, earned, reputation
        self.upgrades, self.stock = dict(upgrades), list(stock)
        self.time_left_ticks = tuning["shop"]["max_ticks"]
        self.done, self.reason = False, None

    def step(self, inp):
        ev = []
        self.time_left_ticks -= 1
        if inp.buy:
            self.upgrades[inp.buy] = self.upgrades.get(inp.buy, 0) + 1
            ev.append(("bought", {"upgrade": inp.buy}))
        if inp.pressed("shop_done") or self.time_left_ticks <= 0:
            self.done, self.reason = True, "done"
            ev.append(("shop_end", {"reason": "done" if inp.pressed("shop_done") else "time"}))
        return ev

    def snapshot(self):
        return {"stock": public_list(self.stock), "upgrades": self.upgrades}


def run_day(w, scenario=None, fr=(), ticks=20, days=1, every=1):
    out = w.path("d.jsonl")
    run("day", TUNING, scenario or {}, 1, list(fr), ticks, out, every, days=days, shop_factory=FakeShop)
    return read_jsonl(out)


def names(rows):
    return [(r["tick"], r["phase"], r.get("day"), r["name"]) for r in events(rows)]


def raw_items(*kinds):
    return [new_item(f"I{i}", k, 100) for i, k in enumerate(kinds, 1)]


DOCK = {"gather": {"hold": items("ca_loc", "bong_sung", "bong_sung"), "random_fish": False}}
DOCK_RAW = {"gather": {"hold": raw_items("ca_loc", "bong_sung", "bong_sung"), "random_fish": False}}
SHORT_QUAN = {"quan": {"time_left_ticks": 2, "random_customers": False}}


class DayFlow(unittest.TestCase):
    def test_day_opens_with_plan_events_at_tick_0(self):
        with Workdir() as w:
            rows = run_day(w, ticks=0)
            self.assertEqual(names(rows), [(0, "gather", 1, "day_start"), (0, "gather", 1, "day_plan"),
                                           (0, "gather", 1, "phase_start")])
            plan = events(rows, "day_plan")[0]["data"]
            self.assertEqual(plan, {"dishes": {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3},
                                    "ingredients": {"bong_sung": 6, "ca_loc": 3}})
            s = snapshots(rows)[0]
            self.assertEqual((s["mode"], s["phase"], s["day"], s["upgrades"], s["active_upgrades"]),
                             ("day", "gather", 1, {}, {}))

    def test_dock_hands_inventory_to_quan_same_tick(self):
        with Workdir() as w:
            sc = dict(DOCK_RAW, day={"money": 200, "earned": 200})
            rows = run_day(w, sc, [{"tick": 0, "interact": True}], ticks=1)
            self.assertEqual(names(rows)[3:], [(1, "gather", 1, "gather_end"), (1, "quan", 1, "phase_start")])
            s = snapshots(rows)[-1]
            self.assertEqual((s["phase"], s["phase_tick"], s["money"], s["earned"]), ("quan", 0, 200, 200))
            self.assertEqual([(it["id"], it["kind"]) for it in s["stock"]],
                             [("I1", "ca_loc"), ("I2", "bong_sung"), ("I3", "bong_sung")])
            self.assertTrue(all(abs(it["fresh"] - 23998 / 240) < 0.01 for it in s["stock"]))

    def test_faint_still_opens_quan_with_empty_stock(self):
        with Workdir() as w:
            sc = {"gather": {"random_fish": False, "hold": raw_items("ca_loc"),
                             "player": {"pos": [50, 10], "oxygen_ticks": 0, "hp": 1}}}
            rows = run_day(w, sc, ticks=61)
            self.assertIn((60, "quan", 1, "phase_start"), names(rows))
            self.assertEqual(snapshots(rows)[-1]["stock"], [])

    def test_full_day_ends_after_shop_closes(self):
        with Workdir() as w:
            sc = dict(DOCK_RAW, **SHORT_QUAN)
            fr = [{"tick": 0, "interact": True}, {"tick": 3, "shop_done": True}]
            rows = run_day(w, sc, fr, ticks=50)
            self.assertEqual([n for n in names(rows) if n[3] in ("quan_end", "phase_start", "shop_end")],
                             [(0, "gather", 1, "phase_start"), (1, "quan", 1, "phase_start"),
                              (3, "quan", 1, "quan_end"), (3, "shop", 1, "phase_start"), (4, "shop", 1, "shop_end")])
            end = rows[-1]
            self.assertEqual((end["reason"], end["days_completed"], end["ticks"]), ("days_complete", 1, 4))

    def test_next_day_uses_bought_upgrade_and_new_plan(self):
        with Workdir() as w:
            sc = dict(DOCK_RAW, **SHORT_QUAN)
            fr = [{"tick": 0, "interact": True}, {"tick": 3, "buy": "oxygen", "shop_done": True}]
            rows = run_day(w, sc, fr, ticks=5, days=2)
            self.assertEqual([n for n in names(rows) if n[0] == 4],
                             [(4, "shop", 1, "bought"), (4, "shop", 1, "shop_end"), (4, "gather", 2, "day_start"),
                              (4, "gather", 2, "day_plan"), (4, "gather", 2, "phase_start")])
            s = {x["tick"]: x for x in snapshots(rows)}
            self.assertEqual(s[3]["upgrades"], {})  # cấp vừa mua chưa hiệu lực trong Ngày 1
            self.assertEqual((s[4]["day"], s[4]["active_upgrades"], s[4]["player"]["oxygen_max_ticks"]),
                             (2, {"oxygen": 1}, 45 * 60))
            self.assertEqual(s[4]["day_plan"]["dishes"], {"ca_loc_nuong_trui": 2, "lau_ca_linh_dien_dien": 2})
            self.assertEqual(rows[-1]["reason"], "tick_limit")

    def test_hp_upgrade_from_scenario(self):
        with Workdir() as w:
            s = snapshots(run_day(w, {"day": {"upgrades": {"hp": 2}}}, ticks=0))[0]
            self.assertEqual((s["player"]["hp"], s["player"]["hp_max"]), (5, 5))


class Pause(unittest.TestCase):
    def test_pause_freezes_gameplay_and_ignores_actions(self):
        with Workdir() as w:
            inp = write_json(w.path("in.json"), frames(
                {"tick": 5, "pause": True}, {"tick": 6, "pause": False}, {"tick": 7, "interact": True},
                {"tick": 8, "interact": False}, {"tick": 10, "pause": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "14", "--inputs", inp,
                                     "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual([(r["tick"], r["name"]) for r in events(rows) if r["name"] in ("paused", "resumed")],
                             [(6, "paused"), (11, "resumed")])
            self.assertEqual(events(rows, "gather_end"), [], "interact lúc pause (ở bến) bị bỏ qua")
            s = {x["tick"]: x for x in snapshots(rows)}
            self.assertEqual((s[8]["state"], s[8]["sim_tick"], s[8]["time_left_ticks"]), ("paused", 5, 10800 - 5))
            self.assertEqual((s[11]["state"], s[11]["sim_tick"], s[11]["phase_tick"]), ("playing", 6, 6))
            self.assertEqual((rows[-1]["ticks"], rows[-1]["sim_tick"]), (14, 9))

    def test_pause_in_day_mode(self):
        with Workdir() as w:
            rows = run_day(w, fr=[{"tick": 0, "pause": True}], ticks=3)
            self.assertEqual(snapshots(rows)[-1]["state"], "paused")
            self.assertEqual(snapshots(rows)[-1]["phase_tick"], 0)


class Cli(unittest.TestCase):
    def test_days_flag_rules(self):
        with Workdir() as w:
            out = w.path("o.jsonl")
            for args in (["--mode", "day", "--days", "0"], ["--mode", "day", "--days", "6"],
                         ["--mode", "gather", "--days", "1"]):
                self.assertEqual(run_headless(*args, "--seed", "1", "--ticks", "0", "--out", out)[0], 2, args)
            self.assertEqual(run_headless("--mode", "day", "--days", "5", "--seed", "1", "--ticks", "0", "--out", out)[0], 0)

    def test_bad_day_scenarios_exit_2(self):
        bad = [{"quan": {"stock": {"ca_loc": 1}}}, {"quan": {"reputation": 4}},
               {"day": {"money": 300, "earned": 200}}, {"day": {"money": 50}},
               {"day": {"upgrades": {"oxygen": 3}}}, {"day": {"upgrades": {"laser": 1}}},
               {"day": {"day_plan": [{"day": 1, "dishes": {"goi_bong_sung": 1}, "ingredients": {"bong_sung": 3}}]}},
               {"day": {"day_plan": [{"day": 1, "dishes": {"mon_la": 1}}]}}, {"day": {"vip": True}}]
        for sc in bad:
            with Workdir() as w:
                p = write_json(w.path("sc.json"), sc)
                code, _ = run_headless("--mode", "day", "--seed", "1", "--ticks", "0", "--scenario", p,
                                       "--out", w.path("o.jsonl"))
                self.assertEqual(code, 2, sc)

    def test_day_plan_override(self):
        with Workdir() as w:
            sc = {"day": {"day_plan": [{"day": 1, "dishes": {"lau_mam": 1}}]}}
            plan = events(run_day(w, sc, ticks=0), "day_plan")[0]["data"]
            self.assertEqual(plan["ingredients"], {"bong_dien_dien": 1, "ca_keo": 1, "ca_linh": 2, "keo_neo": 1})


class RealShopHeadless(unittest.TestCase):
    """Tích hợp day + ShopSim thật (lát 4a) qua headless_cmd."""

    def run_h(self, w, sc, fr, ticks, days=1):
        args = ["--mode", "day", "--days", str(days), "--seed", "3", "--ticks", str(ticks), "--snapshot-every", "1",
                "--scenario", write_json(w.path("sc.json"), sc), "--out", w.path("o.jsonl")]
        if fr:
            args += ["--inputs", write_json(w.path("in.json"), {"frames": fr})]
        code, err = run_headless(*args)
        self.assertEqual(code, 0, err)
        return read_jsonl(w.path("o.jsonl"))

    def test_buy_in_shop_applies_from_next_day(self):
        with Workdir() as w:
            sc = dict(DOCK, day={"money": 450, "earned": 450}, **SHORT_QUAN)
            fr = [{"tick": 0, "interact": True}, {"tick": 3, "buy": "oxygen"},
                  {"tick": 4, "buy": "hp", "shop_done": True}]
            rows = self.run_h(w, sc, fr, ticks=6, days=2)
            self.assertEqual([e["data"] for e in events(rows, "bought")],
                             [{"upgrade": "oxygen", "level": 1, "price": 200, "money": 250},
                              {"upgrade": "hp", "level": 1, "price": 250, "money": 0}])
            s = {x["tick"]: x for x in snapshots(rows)}
            self.assertEqual((s[4]["phase"], s[4]["upgrades"], s[4]["active_upgrades"]), ("shop", {"oxygen": 1}, {}))
            p = s[5]["player"]
            self.assertEqual((s[5]["day"], s[5]["active_upgrades"], p["oxygen_max_ticks"], p["hp"], p["hp_max"]),
                             (2, {"hp": 1, "oxygen": 1}, 2700, 4, 4))
            self.assertEqual((s[5]["money"], s[5]["earned"]), (0, 450))

    def test_buy_failed_funds_and_shop_timeout(self):
        with Workdir() as w:
            sc = dict(DOCK, **SHORT_QUAN)
            rows = self.run_h(w, sc, [{"tick": 0, "interact": True}, {"tick": 3, "buy": "oxygen"}], ticks=1000)
            self.assertEqual(events(rows, "buy_failed")[0]["data"], {"action": "oxygen", "reason": "funds"})
            end = events(rows, "shop_end")[0]
            self.assertEqual((end["tick"], end["data"]), (3 + TUNING["shop"]["max_ticks"], {"reason": "time"}))
            self.assertEqual((rows[-1]["reason"], rows[-1]["days_completed"]), ("days_complete", 1))

    def test_items_hand_off_same_tick_and_ids_continue_across_days(self):
        with Workdir() as w:
            sc = dict(SHORT_QUAN, gather={"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}], "random_fish": False})
            fr = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False}, {"tick": 3, "shop_done": True},
                  {"tick": 4, "interact": True}]
            rows = self.run_h(w, sc, fr, ticks=5, days=2)
            s = {x["tick"]: x for x in snapshots(rows)}
            # tick 1: bàn giao cùng tick, chỉ hao 1 lần ở bước gather (2 đơn vị), không hao thêm khi chuyển pha
            self.assertEqual((s[1]["phase"], s[1]["stock"]), ("quan", [{"id": "I1", "kind": "ca_loc", "fresh": 99.992}]))
            # Ngày 2: mẫu gather.hold nhận id MỚI (I2) với kind/fresh ban đầu
            self.assertEqual((s[4]["day"], s[4]["phase"], s[4]["hold"]), (2, "gather", [{"id": "I2", "kind": "ca_loc", "fresh": 100}]))
            self.assertEqual([x["id"] for x in events(rows, "gather_end")[-1]["data"]["inventory"]["items"]], ["I2"])

    def test_quan_in_day_only_orders_planned_dishes(self):
        with Workdir() as w:
            # kho có đủ cho cả lẩu cá linh (ngoài kế hoạch D1) lẫn 2 món trong kế hoạch D1
            hold = items(*(["ca_linh"] * 3 + ["bong_dien_dien", "ca_loc", "bong_sung", "bong_sung"]))
            sc = {"gather": {"hold": hold, "random_fish": False}}
            rows = self.run_h(w, sc, [{"tick": 0, "interact": True}], ticks=1 + 120 + 900 * 3 + 1)
            dishes = {e["data"]["dish_id"] for e in events(rows, "customer_arrived")}
            self.assertTrue(dishes)
            self.assertLessEqual(dishes, {"ca_loc_nuong_trui", "goi_bong_sung"})


if __name__ == "__main__":
    unittest.main()
