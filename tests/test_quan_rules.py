"""Test luật quán (lát 3 + 4, Contract v1.2 kho cá thể có độ tươi). Hộp đen: chạy headless, đọc JSONL."""

import json
import os
import unittest

from helpers import Workdir, events, frames, items, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    TUNING = json.load(_f)["tuning"]
Q, MENU = TUNING["quan"], TUNING["menu"]
PATIENCE = Q["patience_s"] * 60
EAT = Q["eat_s"] * 60
AT_STOVE, AT_TABLE = [2, 8], [9, 2]


def run(w, scenario=None, inputs=None, ticks=100, every=None, seed=1, out="o.jsonl", expect=0):
    args = ["--mode", "quan", "--seed", str(seed), "--ticks", str(ticks), "--out", w.path(out)]
    if scenario is not None:
        args += ["--scenario", write_json(w.path("sc.json"), {"quan": scenario})]
    if inputs is not None:
        args += ["--inputs", write_json(w.path("in.json"), inputs)]
    if every:
        args += ["--snapshot-every", str(every)]
    code, err = run_headless(*args)
    assert code == expect, (code, err)
    return read_jsonl(w.path(out)) if expect == 0 else None


def ev(rows, name):
    return [(r["tick"], r["data"]) for r in events(rows, name)]


def cust(cid="C1", **kw):
    c = {"id": cid, "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}
    c.update(kw)
    return c


PAYLOAD = {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}


class Arrivals(unittest.TestCase):
    def test_first_customer_at_scheduled_tick_picks_doable_dish_and_reserves(self):
        with Workdir() as w:
            rows = run(w, {"stock": items("ca_loc")}, ticks=Q["first_customer_tick"] + 1, every=1)
            self.assertEqual(ev(rows, "customer_arrived"),
                             [(120, {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})])
            snap = snapshots(rows)
            self.assertEqual(snap[119]["customers"], [])
            c = snap[120]["customers"][0]
            self.assertEqual((c["state"], c["order_status"], c["reserved"], c["order_tick"]),
                             ("waiting", "reserved", ["I1"], 120))
            self.assertEqual(c["patience_ticks_left"], PATIENCE)
            self.assertEqual(snap[121]["customers"][0]["patience_ticks_left"], PATIENCE - 1)
            self.assertEqual(snap[120]["tables"][0]["customer_id"], "C1")

    def test_no_dish_when_stock_cannot_cook_anything(self):
        with Workdir() as w:
            rows = run(w, {"stock": items("bong_sung")}, ticks=121)
            self.assertEqual(ev(rows, "no_dish"), [(120, {})])
            self.assertEqual(events(rows, "customer_arrived"), [])

    def test_random_customers_false_disables_spawn(self):
        with Workdir() as w:
            rows = run(w, {"stock": items("ca_loc", "ca_loc", "ca_loc"), "random_customers": False}, ticks=200)
            self.assertEqual(events(rows, "customer_arrived"), [])
            self.assertEqual(events(rows, "no_dish"), [])

    def test_reserved_stock_is_not_available_to_next_customer(self):
        # v1.1 có 4 bàn: T2 còn trống nhưng ca_loc duy nhất đã bị C1 giữ -> no_dish
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "customers": [cust(patience_ticks_left=PATIENCE)]}
            rows = run(w, sc, ticks=130)
            self.assertEqual(events(rows, "customer_arrived"), [])
            self.assertEqual(ev(rows, "no_dish"), [(120, {})])

    def test_no_spawn_when_all_tables_full(self):
        with Workdir() as w:
            tables = [t["id"] for t in Q["tables"]]
            stock = items(*(["ca_loc"] * (len(tables) + 1)))
            custs = [cust(f"C{i}", table_id=tid, patience_ticks_left=PATIENCE) for i, tid in enumerate(tables, 1)]
            rows = run(w, {"stock": stock, "customers": custs}, ticks=130)
            self.assertEqual(events(rows, "customer_arrived") + events(rows, "no_dish"), [])

    def test_same_seed_same_bytes_and_schedule_repeats(self):
        with Workdir() as w:
            kinds = ["ca_loc"] * 5 + ["bong_sung"] * 5 + ["ca_linh"] * 5 + ["bong_dien_dien"] * 5
            sc = {"stock": items(*kinds)}
            t = 120 + 15 * 60 + 5
            run(w, sc, ticks=t, seed=9, out="a.jsonl")
            run(w, sc, ticks=t, seed=9, out="b.jsonl")
            with open(w.path("a.jsonl"), "rb") as a, open(w.path("b.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())


class Kitchen(unittest.TestCase):
    def test_cook_ready_pick_up_flow(self):
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "customers": [cust()], "player": {"pos": AT_STOVE},
                  "random_customers": False}
            cook = MENU["ca_loc_nuong_trui"]["cook_s"] * 60
            inp = frames({"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                         {"tick": 1 + cook, "interact": True})
            rows = run(w, sc, inp, ticks=cook + 5, every=1)
            # v1.2: hao 1/240 tươi ở bước 1 -> base_price = floor(60 * 23999 / 24000) = 59
            cs = ev(rows, "cook_started")
            self.assertEqual(len(cs), 1)
            self.assertEqual(cs[0][0], 1)
            d = cs[0][1]
            self.assertEqual((d["stove_id"], d["order_id"], d["dish_id"], d["base_price"]),
                             ("B1", "C1", "ca_loc_nuong_trui", 59))
            self.assertEqual(len(d["items"]), 1)
            self.assertEqual((d["items"][0]["id"], d["items"][0]["kind"]), ("I1", "ca_loc"))
            self.assertAlmostEqual(d["items"][0]["fresh"], 23999 / 240, places=2)
            self.assertEqual(ev(rows, "dish_ready")[0][0], 1 + cook)
            self.assertEqual(ev(rows, "dish_picked"), [(2 + cook, {"stove_id": "B1", "order_id": "C1",
                                                                    "dish_id": "ca_loc_nuong_trui"})])
            snap = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snap[1]["stock"], [])  # nguyên liệu đã tiêu
            self.assertEqual(snap[1]["customers"][0]["order_status"], "assigned")
            self.assertEqual(snap[1]["customers"][0]["reserved"], [])
            self.assertEqual(snap[1]["stoves"][0]["state"], "cooking")
            self.assertEqual(snap[1 + cook]["stoves"][0]["state"], "ready")
            self.assertEqual(snap[1 + cook + 2]["hand"],
                             {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 59})
            self.assertEqual(snap[1 + cook + 2]["stoves"][0]["state"], "idle")

    def test_ready_ticks_counts_after_ready(self):
        with Workdir() as w:
            sc = {"stock": [], "customers": [cust(order_status="assigned", reserved=[])],
                  "stoves": [{"id": "B1", "state": "ready", "dish": PAYLOAD, "ready_ticks": 5}],
                  "random_customers": False}
            rows = run(w, sc, ticks=3, every=1)
            self.assertEqual([s["stoves"][0]["ready_ticks"] for s in snapshots(rows)], [5, 6, 7, 8])

    def test_cook_picks_reserved_order_and_ignores_assigned_ones(self):
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "player": {"pos": AT_STOVE}, "random_customers": False,
                  "customers": [cust("C1", order_tick=3)]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(ev(rows, "cook_started")[0][1]["order_id"], "C1")

    def test_stove_ignored_when_out_of_radius_or_nothing_to_cook(self):
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "customers": [cust()], "random_customers": False}  # đứng giữa phòng
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(events(rows), [])
            sc = {"stock": [], "player": {"pos": AT_STOVE}, "random_customers": False}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(events(rows), [])


class Serving(unittest.TestCase):
    def serve(self, w, patience, **extra):
        sc = {"stock": [], "hand": PAYLOAD, "player": {"pos": AT_TABLE}, "random_customers": False,
              "customers": [cust(order_status="assigned", reserved=[], patience_ticks_left=patience)]}
        sc.update(extra)
        return run(w, sc, frames({"tick": 0, "interact": True}), ticks=EAT + 5, every=1)

    def test_serve_with_tip_then_eat_then_paid_and_reputation(self):
        with Workdir() as w:
            rows = self.serve(w, PATIENCE)
            self.assertEqual(ev(rows, "served"), [(1, {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                                       "patience_ticks_left": PATIENCE - 1, "base_price": 60, "tip": 12})])
            self.assertEqual(ev(rows, "paid"), [(1 + EAT, {"order_id": "C1", "table_id": "T1", "base_price": 60,
                                                            "tip": 12, "amount": 72, "reason": "finished_eating"})])
            snap = {s["tick"]: s for s in snapshots(rows)}
            self.assertIsNone(snap[1]["hand"])
            self.assertEqual(snap[1]["customers"][0]["state"], "eating")
            self.assertEqual(snap[EAT]["customers"][0]["eat_ticks_left"], 1)
            last = snapshots(rows)[-1]
            self.assertEqual((last["money"], last["earned"], last["customers"]), (72, 72, []))
            self.assertAlmostEqual(last["reputation"], 3.2, places=6)
            self.assertEqual(last["score"], 72 + 100 * 3)

    def test_tip_threshold_is_exact(self):
        half = PATIENCE // 2
        with Workdir() as w:  # sau bước 1 còn đúng half -> có boa
            self.assertEqual(ev(self.serve(w, half + 1), "served")[0][1]["tip"], 12)
        with Workdir() as w:  # sau bước 1 còn half - 1 -> không boa, không cộng uy tín
            rows = self.serve(w, half)
            self.assertEqual(ev(rows, "served")[0][1]["tip"], 0)
            self.assertEqual(ev(rows, "paid")[0][1]["amount"], 60)
            self.assertEqual(snapshots(rows)[-1]["reputation"], 3.0)

    def test_serve_valid_on_the_tick_patience_hits_zero(self):
        with Workdir() as w:
            rows = self.serve(w, 1)
            self.assertEqual(len(ev(rows, "served")), 1)
            self.assertEqual(events(rows, "customer_left"), [])

    def test_wrong_order_or_empty_hand_ignored(self):
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "player": {"pos": AT_TABLE}, "random_customers": False,
                  "customers": [cust(patience_ticks_left=PATIENCE)]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(events(rows), [])


class Leaving(unittest.TestCase):
    def test_patience_runs_out_reduces_reputation_and_drops_everything(self):
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "random_customers": False, "hand": PAYLOAD,
                  "customers": [cust(order_status="assigned", reserved=[], patience_ticks_left=2)],
                  "stoves": [{"id": "B1"}]}
            rows = run(w, sc, ticks=5)
            self.assertEqual(ev(rows, "customer_left"),
                             [(2, {"order_id": "C1", "table_id": "T1", "reason": "patience", "reputation": 2.5})])
            last = snapshots(rows)[-1]
            self.assertEqual((last["customers"], last["hand"], last["reputation"]), ([], None, 2.5))

    def test_leaving_releases_reservation_and_clears_cooking_stove(self):
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "random_customers": False,
                  "customers": [cust(patience_ticks_left=1)]}
            rows = run(w, sc, ticks=3)
            st = snapshots(rows)[-1]["stock"]
            self.assertEqual(len(st), 1)
            self.assertEqual((st[0]["id"], st[0]["kind"]), ("I1", "ca_loc"))
            sc = {"stock": [], "random_customers": False,
                  "customers": [cust(order_status="assigned", reserved=[], patience_ticks_left=1)],
                  "stoves": [{"id": "B1", "state": "cooking", "dish": PAYLOAD, "cook_ticks_left": 100}]}
            rows = run(w, sc, ticks=3)
            stove = snapshots(rows)[-1]["stoves"][0]
            self.assertEqual((stove["state"], stove["dish"], stove["cook_ticks_left"]), ("idle", None, 0))

    def test_reputation_clamped_at_min(self):
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "random_customers": False, "reputation": 0.2,
                  "customers": [cust(patience_ticks_left=1)]}
            self.assertEqual(snapshots(run(w, sc, ticks=3))[-1]["reputation"], 0)

    def test_closing_pays_eaters_and_waiters_leave_without_penalty(self):
        with Workdir() as w:
            sc = {"stock": [], "random_customers": False, "time_left_ticks": 3,
                  "customers": [cust(state="eating", order_status="served", eat_ticks_left=100, base_price=40, tip=8)]}
            rows = run(w, sc, ticks=50)
            self.assertEqual(ev(rows, "paid"), [(3, {"order_id": "C1", "table_id": "T1", "base_price": 40, "tip": 8,
                                                      "amount": 48, "reason": "closing"})])
            end = ev(rows, "quan_end")
            self.assertEqual(end[0][1]["shift_earned"], 48)
            self.assertEqual(end[0][1]["money"], 48)
            self.assertEqual(rows[-1]["reason"], "time")
            self.assertEqual(rows[-1]["score"], 48 + 100 * 3)
        with Workdir() as w:
            sc = {"stock": items("ca_loc"), "random_customers": False, "time_left_ticks": 3,
                  "customers": [cust(patience_ticks_left=3)]}  # kiên nhẫn về 0 đúng bước cuối: vẫn là closing
            rows = run(w, sc, ticks=50)
            self.assertEqual(ev(rows, "customer_left"),
                             [(3, {"order_id": "C1", "table_id": "T1", "reason": "closing", "reputation": 3.0})])

    def test_just_served_customer_pays_on_closing_step(self):
        with Workdir() as w:
            sc = {"stock": [], "random_customers": False, "time_left_ticks": 1, "hand": PAYLOAD,
                  "player": {"pos": AT_TABLE},
                  "customers": [cust(order_status="assigned", reserved=[], patience_ticks_left=PATIENCE)]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=5)
            self.assertEqual([r["name"] for r in events(rows)], ["served", "paid", "quan_end"])
            self.assertEqual(ev(rows, "paid")[0][1]["reason"], "closing")


class BadFixtures(unittest.TestCase):
    def test_exit_2_for_inconsistent_orders(self):
        bad = [
            {"stock": [], "customers": [cust()]},                                               # giữ chỗ quá tồn
            {"stock": items("ca_loc"), "customers": [cust(reserved=["I2"])]},                   # id không có trong kho
            {"stock": items("ca_loc"), "customers": [cust(reserved=["I1", "I1"])]},             # id trùng trong đơn
            {"stock": items("ca_loc", fresh=29), "customers": [cust(reserved=["I1"])]},         # cá thể đã ươn
            {"stock": items("bong_sung"), "customers": [cust(reserved=["I1"])]},                # giữ khác công thức
            {"stock": items("ca_loc", "ca_loc"), "customers": [
                cust("C1", table_id="T1", reserved=["I1"]),
                cust("C2", table_id="T2", reserved=["I1"]),
            ]},                                                                                 # dùng chung id giữa 2 đơn
            {"stock": [], "customers": [cust(order_status="assigned", reserved=[])]},           # assigned không có món
            {"stock": items("ca_loc"), "customers": [cust(dish_id="mon_la")]},                  # món lạ
            {"stock": [], "customers": [cust(state="eating")]},                                 # eating chưa served
            {"stock": [], "customers": [cust(state="eating", order_status="served")]},          # thiếu timer ăn
            {"stock": [], "customers": [cust(order_status="assigned", reserved=[])], "hand": PAYLOAD,
             "stoves": [{"id": "B1", "state": "ready", "dish": PAYLOAD}]},                      # bếp + tay cùng đơn
            {"stock": [], "stoves": [{"id": "B1", "state": "cooking", "dish": PAYLOAD, "cook_ticks_left": 5}]},  # không có khách
            {"stock": [], "customers": [cust(order_status="assigned", reserved=[])],
             "stoves": [{"id": "B1", "state": "cooking", "dish": PAYLOAD, "cook_ticks_left": 0}]},  # timer không dương
            {"stock": items("ca_loc"), "customers": [cust(patience_ticks_left=PATIENCE + 1)]},  # kiên nhẫn quá đầy
        ]
        for sc in bad:
            with Workdir() as w:
                run(w, sc, ticks=0, expect=2)
                self.assertFalse(os.path.exists(w.path("o.jsonl")), sc)

    def test_valid_assigned_fixture_accepted(self):
        with Workdir() as w:
            sc = {"stock": [], "random_customers": False, "hand": PAYLOAD,
                  "customers": [cust(order_status="assigned", reserved=[])]}
            run(w, sc, ticks=0)


class Phase2QuanExpansion(unittest.TestCase):
    def test_two_stoves_cook_concurrently_and_four_tables_fill_by_id(self):
        with Workdir() as w:
            sc = {
                "stock": items(*(["ca_loc"] * 10)),
                "player": {"pos": [2, 8]},
                "customers": [
                    cust("C1", table_id="T1", order_tick=10),
                    cust("C2", table_id="T2", order_tick=20),
                ],
                "random_customers": False,
            }
            inp = frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False, "move": [1, 0]},
                {"tick": 46, "move": [0, 0], "interact": True},
            )
            rows = run(w, sc, inp, ticks=60, every=1)
            started = ev(rows, "cook_started")
            self.assertEqual(len(started), 2)
            self.assertEqual((started[0][1]["stove_id"], started[0][1]["order_id"]), ("B1", "C1"))
            self.assertEqual((started[1][1]["stove_id"], started[1][1]["order_id"]), ("B2", "C2"))

        # 4 bàn lấp đầy theo thứ tự T1 -> T2 -> T3 -> T4 (trước khi C1 hết kiên nhẫn ở tick 3720)
        with Workdir() as w:
            rows = run(w, {"stock": items(*(["ca_loc"] * 10))}, ticks=120 + 900 * 3 + 10)
            arrived = ev(rows, "customer_arrived")
            self.assertEqual([d["table_id"] for _, d in arrived], ["T1", "T2", "T3", "T4"])
            self.assertEqual([t for t, _ in arrived], [120, 1020, 1920, 2820])

    def test_standalone_quan_uses_all_six_dishes(self):
        from chonoi.ids import IdAllocator
        from chonoi.inputs import InputPlayer
        from chonoi.items import new_item
        from chonoi.rng import Streams
        from chonoi.sim.quan import QuanSim

        kinds = ["ca_loc", "bong_sung", "ca_linh", "bong_dien_dien", "ca_keo", "keo_neo"]
        stock = [new_item(f"I{i}", k, 100) for i, k in enumerate([x for x in kinds for _ in range(20)], 1)]
        seen = set()
        for seed in range(1, 20):
            sim = QuanSim(TUNING, {"stock": [dict(x) for x in stock]}, Streams(seed), IdAllocator())
            ip = InputPlayer([])
            for t in range(121):
                for name, data in sim.step(ip.advance(t)):
                    if name == "customer_arrived":
                        seen.add(data["dish_id"])
        self.assertEqual(seen, set(MENU.keys()))

    def test_day_plan_dishes_filters_before_ingredients(self):
        from chonoi.errors import BadInput
        from chonoi.ids import IdAllocator
        from chonoi.inputs import InputPlayer
        from chonoi.items import new_item
        from chonoi.rng import Streams
        from chonoi.sim.quan import QuanSim

        # Kho chỉ có nguyên liệu nấu ca_keo_nuong, nhưng kế hoạch D1 chỉ có ca_loc_nuong_trui & goi_bong_sung -> no_dish
        stock_keo = [new_item(f"I{i}", "ca_keo", 100) for i in range(1, 11)]
        sim = QuanSim(TUNING, {"stock": stock_keo}, Streams(1), IdAllocator(),
                      plan_dishes={"ca_loc_nuong_trui", "goi_bong_sung"})
        ip = InputPlayer([])
        evs = []
        for t in range(121):
            evs.extend((t + 1, n, d) for n, d in sim.step(ip.advance(t)))
        self.assertEqual([e for e in evs if e[1] in ("customer_arrived", "no_dish")], [(120, "no_dish", {})])

        # Kho đủ cả 6 món, nhưng plan_dishes chỉ cho phép ca_keo_nuong -> chỉ gọi ca_keo_nuong
        kinds = ["ca_loc", "bong_sung", "ca_linh", "bong_dien_dien", "ca_keo", "keo_neo"]
        full_stock = [new_item(f"I{i}", k, 100) for i, k in enumerate([x for x in kinds for _ in range(20)], 1)]
        sim2 = QuanSim(TUNING, {"stock": full_stock}, Streams(1), IdAllocator(), plan_dishes={"ca_keo_nuong"})
        arrived = []
        for t in range(1050):
            for n, d in sim2.step(ip.advance(t)):
                if n == "customer_arrived":
                    arrived.append(d["dish_id"])
        self.assertEqual(arrived, ["ca_keo_nuong", "ca_keo_nuong"])

        # Fixture khách có món ngoài kế hoạch -> BadInput
        with self.assertRaises(BadInput):
            QuanSim(TUNING, {"stock": [new_item("I1", "ca_loc", 100)], "customers": [cust()]},
                    Streams(1), IdAllocator(), plan_dishes={"goi_bong_sung"})


class Phase3Freshness(unittest.TestCase):
    def test_reserve_picks_freshest_then_lowest_id(self):
        with Workdir() as w:
            stock = [
                {"id": "I1", "kind": "ca_loc", "fresh": 50},
                {"id": "I2", "kind": "ca_loc", "fresh": 90},
                {"id": "I10", "kind": "ca_loc", "fresh": 90},
                {"id": "I3", "kind": "ca_loc", "fresh": 25},  # đã ươn -> bỏ qua
            ]
            rows = run(w, {"stock": stock}, ticks=121, every=120)
            c = snapshots(rows)[-1]["customers"][0]
            # Tươi nhất là 90; hòa 90 giữa I2 và I10 -> chọn I2 (id_key nhỏ hơn)
            self.assertEqual(c["reserved"], ["I2"])

    def test_spoiled_reservation_re_reserves_once_or_turns_unfulfillable(self):
        with Workdir() as w:
            # I1 (fresh=30 -> ươn ngay bước 1) bị C1 (order_tick=10) giữ, I2 (fresh=30) bị C2 (order_tick=20) giữ,
            # I3 (fresh=80) còn trống. Bước 1: cả I1 và I2 đều spoiled -> C1 (order_tick nhỏ hơn) giữ lại được I3,
            # C2 không còn cá thể khả dụng -> chuyển unfulfillable và chờ tới hết kiên nhẫn.
            stock = [
                {"id": "I1", "kind": "ca_loc", "fresh": 30},
                {"id": "I2", "kind": "ca_loc", "fresh": 30},
                {"id": "I3", "kind": "ca_loc", "fresh": 80},
            ]
            sc = {
                "stock": stock,
                "random_customers": False,
                "customers": [
                    cust("C1", table_id="T1", order_tick=10, reserved=["I1"], patience_ticks_left=5),
                    cust("C2", table_id="T2", order_tick=20, reserved=["I2"], patience_ticks_left=5),
                ],
            }
            rows = run(w, sc, ticks=6, every=1)
            self.assertEqual(ev(rows, "spoiled"), [
                (1, {"item_id": "I1", "kind": "ca_loc", "location": "stock"}),
                (1, {"item_id": "I2", "kind": "ca_loc", "location": "stock"}),
            ])
            s1 = snapshots(rows)[1]["customers"]
            by_id = {c["id"]: c for c in s1}
            self.assertEqual((by_id["C1"]["order_status"], by_id["C1"]["reserved"]), ("reserved", ["I3"]))
            self.assertEqual((by_id["C2"]["order_status"], by_id["C2"]["reserved"]), ("unfulfillable", []))
            # C2 tiếp tục chờ tới tick 5 mới hết kiên nhẫn và bỏ đi
            left = ev(rows, "customer_left")
            self.assertEqual([t for t, _ in left], [5, 5])

    def test_base_price_and_tip_computed_from_average_freshness(self):
        with Workdir() as w:
            # Món goi_bong_sung (giá 40): cần 2 bong_sung -> I1 fresh=60, I2 fresh=80
            # Sau 1 bước hao 1/240 điểm tươi mỗi cá thể: avg_units = ((60*240 - 1) + (80*240 - 1)) / 2 = 16799
            # base_price = floor(40 * 33598 / (100 * 2 * 240)) = floor(1343920 / 48000) = 27
            # Giao còn >= 50% kiên nhẫn -> tip = floor(27 * 0.2) = 5, amount = 32
            stock = [
                {"id": "I1", "kind": "bong_sung", "fresh": 60},
                {"id": "I2", "kind": "bong_sung", "fresh": 80},
            ]
            sc = {
                "stock": stock,
                "player": {"pos": AT_STOVE},
                "random_customers": False,
                "customers": [cust("C1", dish_id="goi_bong_sung", reserved=["I1", "I2"])],
            }
            cook = MENU["goi_bong_sung"]["cook_s"] * 60
            # Tick 0: nấu ở B1 [2,8]; Tick 1+cook: nhặt; đi sang x=9 (108 tick) rồi xuống z=2 (90 tick) để giao
            inp = frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": 1 + cook, "interact": True},
                {"tick": 2 + cook, "interact": False, "move": [1, 0]},
                {"tick": 110 + cook, "move": [0, -1]},
                {"tick": 200 + cook, "move": [0, 0], "interact": True},
            )
            rows = run(w, sc, inp, ticks=210 + cook + EAT)
            cs = ev(rows, "cook_started")[0][1]
            self.assertEqual(cs["base_price"], 27)
            self.assertEqual([it["id"] for it in cs["items"]], ["I1", "I2"])
            srv = ev(rows, "served")[0][1]
            self.assertEqual((srv["base_price"], srv["tip"]), (27, 5))
            paid = ev(rows, "paid")[0][1]
            self.assertEqual(paid["amount"], 32)


if __name__ == "__main__":
    unittest.main()
