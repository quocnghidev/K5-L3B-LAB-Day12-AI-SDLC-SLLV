"""Test luật quán (lát 3 + 4) theo PRD-0 mục F. Hộp đen: chạy headless, đọc JSONL."""

import json
import os
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json

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
            rows = run(w, {"stock": {"ca_loc": 1}}, ticks=Q["first_customer_tick"] + 1, every=1)
            self.assertEqual(ev(rows, "customer_arrived"),
                             [(120, {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})])
            snap = snapshots(rows)
            self.assertEqual(snap[119]["customers"], [])
            c = snap[120]["customers"][0]
            self.assertEqual((c["state"], c["order_status"], c["reserved"], c["order_tick"]),
                             ("waiting", "reserved", {"ca_loc": 1}, 120))
            self.assertEqual(c["patience_ticks_left"], PATIENCE)
            self.assertEqual(snap[121]["customers"][0]["patience_ticks_left"], PATIENCE - 1)
            self.assertEqual(snap[120]["tables"][0]["customer_id"], "C1")

    def test_no_dish_when_stock_cannot_cook_anything(self):
        with Workdir() as w:
            rows = run(w, {"stock": {"bong_sung": 1}}, ticks=121)
            self.assertEqual(ev(rows, "no_dish"), [(120, {})])
            self.assertEqual(events(rows, "customer_arrived"), [])

    def test_random_customers_false_disables_spawn(self):
        with Workdir() as w:
            rows = run(w, {"stock": {"ca_loc": 3}, "random_customers": False}, ticks=200)
            self.assertEqual(events(rows, "customer_arrived"), [])
            self.assertEqual(events(rows, "no_dish"), [])

    def test_no_spawn_when_table_full_and_reservation_blocks_stock(self):
        with Workdir() as w:
            sc = {"stock": {"ca_loc": 1}, "customers": [cust(patience_ticks_left=PATIENCE)]}
            rows = run(w, sc, ticks=130)
            self.assertEqual(events(rows, "customer_arrived") + events(rows, "no_dish"), [])

    def test_same_seed_same_bytes_and_schedule_repeats(self):
        with Workdir() as w:
            sc = {"stock": {"ca_loc": 5, "bong_sung": 5, "ca_linh": 5, "bong_dien_dien": 5}}
            t = 120 + 15 * 60 + 5
            run(w, sc, ticks=t, seed=9, out="a.jsonl")
            run(w, sc, ticks=t, seed=9, out="b.jsonl")
            with open(w.path("a.jsonl"), "rb") as a, open(w.path("b.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())


class Kitchen(unittest.TestCase):
    def test_cook_ready_pick_up_flow(self):
        with Workdir() as w:
            sc = {"stock": {"ca_loc": 1}, "customers": [cust()], "player": {"pos": AT_STOVE}, "random_customers": False}
            cook = MENU["ca_loc_nuong_trui"]["cook_s"] * 60
            inp = frames({"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                         {"tick": 1 + cook, "interact": True})
            rows = run(w, sc, inp, ticks=cook + 5, every=1)
            self.assertEqual(ev(rows, "cook_started"),
                             [(1, {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui",
                                   "items": ["ca_loc"], "base_price": 60})])
            self.assertEqual(ev(rows, "dish_ready")[0][0], 1 + cook)
            self.assertEqual(ev(rows, "dish_picked"), [(2 + cook, {"stove_id": "B1", "order_id": "C1",
                                                                    "dish_id": "ca_loc_nuong_trui"})])
            snap = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snap[1]["stock"], {})  # nguyên liệu đã tiêu
            self.assertEqual(snap[1]["customers"][0]["order_status"], "assigned")
            self.assertEqual(snap[1]["customers"][0]["reserved"], {})
            self.assertEqual(snap[1]["stoves"][0]["state"], "cooking")
            self.assertEqual(snap[1 + cook]["stoves"][0]["state"], "ready")
            self.assertEqual(snap[1 + cook + 2]["hand"], PAYLOAD)
            self.assertEqual(snap[1 + cook + 2]["stoves"][0]["state"], "idle")

    def test_ready_ticks_counts_after_ready(self):
        with Workdir() as w:
            sc = {"stock": {}, "customers": [cust(order_status="assigned", reserved={})],
                  "stoves": [{"id": "B1", "state": "ready", "dish": PAYLOAD, "ready_ticks": 5}],
                  "random_customers": False}
            rows = run(w, sc, ticks=3, every=1)
            self.assertEqual([s["stoves"][0]["ready_ticks"] for s in snapshots(rows)], [5, 6, 7, 8])

    def test_cook_picks_reserved_order_and_ignores_assigned_ones(self):
        with Workdir() as w:
            sc = {"stock": {"ca_loc": 1}, "player": {"pos": AT_STOVE}, "random_customers": False,
                  "customers": [cust("C1", order_tick=3)]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(ev(rows, "cook_started")[0][1]["order_id"], "C1")

    def test_stove_ignored_when_out_of_radius_or_nothing_to_cook(self):
        with Workdir() as w:
            sc = {"stock": {"ca_loc": 1}, "customers": [cust()], "random_customers": False}  # đứng giữa phòng
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(events(rows), [])
            sc = {"stock": {}, "player": {"pos": AT_STOVE}, "random_customers": False}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(events(rows), [])


class Serving(unittest.TestCase):
    def serve(self, w, patience, **extra):
        sc = {"stock": {}, "hand": PAYLOAD, "player": {"pos": AT_TABLE}, "random_customers": False,
              "customers": [cust(order_status="assigned", reserved={}, patience_ticks_left=patience)]}
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
            sc = {"stock": {"ca_loc": 1}, "player": {"pos": AT_TABLE}, "random_customers": False,
                  "customers": [cust(patience_ticks_left=PATIENCE)]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=2)
            self.assertEqual(events(rows), [])


class Leaving(unittest.TestCase):
    def test_patience_runs_out_reduces_reputation_and_drops_everything(self):
        with Workdir() as w:
            sc = {"stock": {"ca_loc": 1}, "random_customers": False, "hand": PAYLOAD,
                  "customers": [cust(order_status="assigned", reserved={}, patience_ticks_left=2)],
                  "stoves": [{"id": "B1"}]}
            rows = run(w, sc, ticks=5)
            self.assertEqual(ev(rows, "customer_left"),
                             [(2, {"order_id": "C1", "table_id": "T1", "reason": "patience", "reputation": 2.5})])
            last = snapshots(rows)[-1]
            self.assertEqual((last["customers"], last["hand"], last["reputation"]), ([], None, 2.5))

    def test_leaving_releases_reservation_and_clears_cooking_stove(self):
        with Workdir() as w:
            sc = {"stock": {"ca_loc": 1}, "random_customers": False,
                  "customers": [cust(patience_ticks_left=1)]}
            rows = run(w, sc, ticks=3)
            self.assertEqual(snapshots(rows)[-1]["stock"], {"ca_loc": 1})  # giữ chỗ nhả, kho còn nguyên
            sc = {"stock": {}, "random_customers": False,
                  "customers": [cust(order_status="assigned", reserved={}, patience_ticks_left=1)],
                  "stoves": [{"id": "B1", "state": "cooking", "dish": PAYLOAD, "cook_ticks_left": 100}]}
            rows = run(w, sc, ticks=3)
            stove = snapshots(rows)[-1]["stoves"][0]
            self.assertEqual((stove["state"], stove["dish"], stove["cook_ticks_left"]), ("idle", None, 0))

    def test_reputation_clamped_at_min(self):
        with Workdir() as w:
            sc = {"stock": {"ca_loc": 1}, "random_customers": False, "reputation": 0.2,
                  "customers": [cust(patience_ticks_left=1)]}
            self.assertEqual(snapshots(run(w, sc, ticks=3))[-1]["reputation"], 0)

    def test_closing_pays_eaters_and_waiters_leave_without_penalty(self):
        with Workdir() as w:
            sc = {"stock": {}, "random_customers": False, "time_left_ticks": 3,
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
            sc = {"stock": {"ca_loc": 1}, "random_customers": False, "time_left_ticks": 3,
                  "customers": [cust(patience_ticks_left=3)]}  # kiên nhẫn về 0 đúng bước cuối: vẫn là closing
            rows = run(w, sc, ticks=50)
            self.assertEqual(ev(rows, "customer_left"),
                             [(3, {"order_id": "C1", "table_id": "T1", "reason": "closing", "reputation": 3.0})])

    def test_just_served_customer_pays_on_closing_step(self):
        with Workdir() as w:
            sc = {"stock": {}, "random_customers": False, "time_left_ticks": 1, "hand": PAYLOAD,
                  "player": {"pos": AT_TABLE},
                  "customers": [cust(order_status="assigned", reserved={}, patience_ticks_left=PATIENCE)]}
            rows = run(w, sc, frames({"tick": 0, "interact": True}), ticks=5)
            self.assertEqual([r["name"] for r in events(rows)], ["served", "paid", "quan_end"])
            self.assertEqual(ev(rows, "paid")[0][1]["reason"], "closing")


class BadFixtures(unittest.TestCase):
    def test_exit_2_for_inconsistent_orders(self):
        bad = [
            {"stock": {"ca_loc": 0}, "customers": [cust()]},                                   # giữ chỗ quá tồn
            {"stock": {"ca_loc": 1}, "customers": [cust(reserved={"bong_sung": 1})]},          # giữ khác công thức
            {"stock": {}, "customers": [cust(order_status="assigned", reserved={})]},          # assigned không có món
            {"stock": {"ca_loc": 1}, "customers": [cust(dish_id="mon_la")]},                   # món lạ
            {"stock": {}, "customers": [cust(state="eating")]},                                # eating chưa served
            {"stock": {}, "customers": [cust(state="eating", order_status="served")]},         # thiếu timer ăn
            {"stock": {}, "customers": [cust(order_status="assigned", reserved={})], "hand": PAYLOAD,
             "stoves": [{"id": "B1", "state": "ready", "dish": PAYLOAD}]},                     # bếp + tay cùng đơn
            {"stock": {}, "stoves": [{"id": "B1", "state": "cooking", "dish": PAYLOAD, "cook_ticks_left": 5}]},  # không có khách
            {"stock": {}, "customers": [cust(order_status="assigned", reserved={})],
             "stoves": [{"id": "B1", "state": "cooking", "dish": PAYLOAD, "cook_ticks_left": 0}]},  # timer không dương
            {"stock": {"ca_loc": 1}, "customers": [cust(patience_ticks_left=PATIENCE + 1)]},   # kiên nhẫn quá đầy
        ]
        for sc in bad:
            with Workdir() as w:
                run(w, sc, ticks=0, expect=2)
                self.assertFalse(os.path.exists(w.path("o.jsonl")), sc)

    def test_valid_assigned_fixture_accepted(self):
        with Workdir() as w:
            sc = {"stock": {}, "random_customers": False, "hand": PAYLOAD,
                  "customers": [cust(order_status="assigned", reserved={})]}
            run(w, sc, ticks=0)


if __name__ == "__main__":
    unittest.main()
