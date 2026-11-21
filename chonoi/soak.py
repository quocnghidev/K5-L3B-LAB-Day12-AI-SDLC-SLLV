"""Soak headless (Ticket-04 mục 2): python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Chạy N Ngày (D1–D5 lặp ở Ngày 6–10) trong MỘT tiến trình bằng bot tất định đọc trạng thái sim:
  - sáng: bơi dọc mặt nước hái nút sẵn sàng theo x tăng dần, rồi về bến cập (`interact`);
  - tối: món chín -> bưng; tay có món -> tới bàn của đơn; có đơn reserved + bếp rảnh -> nấu;
  - Shop: mua oxy rồi áo phao nếu đủ tiền, rồi `shop_done`.
Tiền, earned, uy tín, cấp, số Ngày và id cá thể tiếp tục xuyên suốt (cùng `DaySim`).
soak.json: {days, days_completed, crashes, results[{day, earned, reputation, score}], duration_s}.
Trường gameplay tất định theo seed; `duration_s` là thời gian thực (bỏ qua khi so).
"""

import argparse
import json
import math
import sys
import time
import traceback

from .contract import load_contract
from .errors import BadInput
from .inputs import InputState
from .runner import Session


class Bot:
    """Sinh InputState cho từng bước từ trạng thái sim (không đọc đồng hồ thật, không ngẫu nhiên)."""

    def __init__(self, tuning):
        self.t = tuning
        self.tap = False  # nút chỉ tác động ở cạnh lên: bấm / nhả xen kẽ
        self.visited = set()
        self.day = None
        self.bought = False

    def _press(self, name):
        self.tap = not self.tap
        return {name} if self.tap else set()

    @staticmethod
    def _toward(pos, target, slow_r=0.6):
        dx, dy = target[0] - pos[0], target[1] - pos[1]
        n = math.hypot(dx, dy)
        if n < 1e-9:
            return (0.0, 0.0), 0.0
        k = 1.0 if n > slow_r else max(0.2, n / slow_r)
        return (dx / n * k, dy / n * k), n

    def act(self, day_sim) -> InputState:
        if day_sim.day != self.day:  # Ngày mới
            self.day, self.visited, self.bought = day_sim.day, set(), False
        sim, phase = day_sim.cur, day_sim.phase
        if phase == "gather":
            move, edges = self._gather(sim)
            return InputState(move, {}, edges)
        if phase == "quan":
            move, edges = self._quan(sim)
            return InputState(move, {}, edges)
        return self._shop(sim)

    def _gather(self, sim):
        g = self.t["gather"]
        pos = sim.pos
        dock = g["dock_pos"]
        free = g["hold_capacity"] - len(sim.hold)
        back_ticks = (abs(pos[0] - dock[0]) / g["swim_speed"] + 2) * 60
        todo = [n for n in sorted(sim.nodes, key=lambda n: (n["pos"][0], n["id"]))
                if n["id"] not in self.visited]
        if free <= 0 or not todo or sim.time_left_ticks <= back_ticks:
            move, dist = self._toward(pos, dock)
            return move, (self._press("interact") if dist <= g["dock_radius"] - 0.5 else set())
        node = todo[0]
        move, dist = self._toward(pos, node["pos"])
        if dist <= g["interact_radius"] - 0.5:
            if node["regrow_ticks"] > 0:
                self.visited.add(node["id"])  # đã hái (hoặc chưa mọc) -> sang nút kế
                return move, set()
            return (0.0, 0.0), self._press("interact")
        return move, set()

    def _quan(self, sim):
        q = self.t["quan"]
        target = None
        if sim.hand is not None:
            c = next((c for c in sim.customers if c["id"] == sim.hand["order_id"]), None)
            if c is not None:
                target = next(tb["pos"] for tb in sim.tables if tb["id"] == c["table_id"])
        if target is None:
            ready = [s for s in sim.stoves if s["state"] == "ready"]
            idle = [s for s in sim.stoves if s["state"] == "idle"]
            waiting = any(c["order_status"] == "reserved" for c in sim.customers)
            if ready and sim.hand is None:
                target = ready[0]["pos"]
            elif idle and waiting:
                target = idle[0]["pos"]
        if target is None:
            return self._toward(sim.pos, q["start_pos"])[0], set()
        move, dist = self._toward(sim.pos, target)
        if dist <= 0.8:
            return (0.0, 0.0), self._press("interact")
        return move, set()

    def _shop(self, sim):
        if not self.bought:
            ups = self.t["shop"]["upgrades"]
            for key in ("oxygen", "hp"):
                nxt = next((u for u in ups[key] if u["level"] == sim.upgrades.get(key, 0) + 1), None)
                if nxt is not None and sim.money >= nxt["price"]:
                    return InputState((0.0, 0.0), {}, set(), buy=key)
            self.bought = True
        return InputState((0.0, 0.0), {}, self._press("shop_done"))


def soak(seed, days, tuning):
    t0 = time.perf_counter()
    results, crashes = [], 0
    sess = Session("day", tuning, {}, seed, days=days)
    bot = Bot(tuning)
    limit = days * 22200 + 1000
    try:
        while not sess.done and sess.tick < limit:
            rows = sess.step(bot.act(sess.sim))
            for r in rows:
                if r["name"] == "shop_end":
                    sim = sess.sim
                    mult = tuning["score"]["reputation_multiplier"]
                    results.append({"day": r["day"], "earned": sim.earned, "reputation": sim.reputation,
                                    "score": sim.earned + mult * math.floor(sim.reputation)})
    except Exception:  # lỗi runtime trong luật: đếm crash, báo stderr, dừng lượt
        crashes += 1
        traceback.print_exc()
    return {"days": days, "days_completed": sess.sim.days_completed, "crashes": crashes,
            "results": results, "duration_s": round(time.perf_counter() - t0, 3)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.soak")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--days", type=int, required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        if a.days < 1:
            raise BadInput("--days phải >= 1")
        tuning = load_contract()["tuning"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    out = soak(a.seed, a.days, tuning)
    try:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    print(f"soak: {out['days_completed']}/{out['days']} Ngày, crashes={out['crashes']}, {out['duration_s']} s")
    return 0 if out["crashes"] == 0 and out["days_completed"] == out["days"] else 1


if __name__ == "__main__":
    sys.exit(main())
