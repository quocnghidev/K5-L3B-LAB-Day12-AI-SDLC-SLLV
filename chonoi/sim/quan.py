"""Buổi tối — Mở Quán (PRD-0 mục F, "Quán").

Một bước = (1) đồng hồ + timer, (2) bếp chín, (3) đi + tối đa MỘT interact, (4) khách ăn xong / hết kiên nhẫn,
(5) khách mới theo lịch, (6) hết ca thì dọn quán rồi `quan_end`.
Số liệu chỉ đọc từ tuning["quan"] và tuning["menu"]; ngẫu nhiên chỉ qua Streams (luồng "customer_dish").
"""

import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..items import UNITS, decay, public, public_list, spoiled, units_per_tick
from .ramp import ramp_velocity

TICK = 60.0
CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left", "eat_ticks_left",
                 "order_status", "reserved", "base_price", "tip"}
ORDER_STATUS = ("reserved", "assigned", "unfulfillable", "served")


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None,
                 plan_dishes=None, planned_dishes=None, money=0, earned=0, reputation=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.fr = tuning["freshness"]
        self.decay_per_tick = units_per_tick(self.fr["quan_decay_per_s"])
        self.rng = streams
        self.ids = ids
        raw_plan = plan_dishes if plan_dishes is not None else planned_dishes
        if raw_plan is None:
            raw_plan = scenario.get("plan_dishes", scenario.get("planned_dishes"))
        if raw_plan is not None:
            if isinstance(raw_plan, dict) and "dishes" in raw_plan and isinstance(raw_plan["dishes"], dict):
                raw_plan = raw_plan["dishes"]
            if not isinstance(raw_plan, (list, tuple, set, dict)):
                raise BadInput("plan_dishes phải là danh sách hoặc map id món")
            for d in raw_plan:
                if d not in self.menu:
                    raise BadInput(f"plan_dishes có món không tồn tại: {d}")
            self.plan_dishes = set(raw_plan)
        else:
            self.plan_dishes = None
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho v1.2: list cá thể nội bộ {id, kind, units} (--inventory HOẶC scenario.stock)
        raw_stock = inventory if inventory is not None else scenario.get("stock", [])
        self.stock = [dict(it) for it in raw_stock]
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        default_rep = t["reputation_initial"] if reputation is None else reputation
        self.reputation = scenario.get("reputation", default_rep)
        self.random_customers = scenario.get("random_customers", True)
        self.patience_full = int(round(t["patience_s"] * TICK))
        self.phase_tick = 0
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.customers = self._build_customers(scenario.get("customers", []))
        for e in self.customers:
            ids.reserve(e["id"])
        self._check_links()
        self.money = int(scenario.get("money", money))
        self.earned = int(scenario.get("earned", earned))
        self.shift_earned = 0
        self.done = False
        self.reason = None

    # --- dựng fixture + kiểm mâu thuẫn mức luật (BadInput -> mã 2, trước khi ghi đầu ra) --------------------
    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def _build_customers(self, raw):
        out = []
        for c in raw:
            extra = set(c) - CUSTOMER_KEYS
            if extra:
                raise BadInput(f"customers.{c['id']}: trường lạ/chưa hỗ trợ {sorted(extra)}")
            dish = c.get("dish_id")
            if dish not in self.menu:
                raise BadInput(f"customers.{c['id']}: dish_id phải là món có thật")
            status = c.get("order_status", "reserved")
            if status not in ORDER_STATUS:
                raise BadInput(f"customers.{c['id']}: order_status không hợp lệ")
            state = c.get("state", "waiting")
            if state not in ("waiting", "eating"):
                raise BadInput(f"customers.{c['id']}: state phải là waiting hoặc eating")
            cust = {
                "id": c["id"], "table_id": c["table_id"], "dish_id": dish,
                "order_tick": c.get("order_tick", 0), "state": state,
                "patience_ticks_left": c.get("patience_ticks_left", self.patience_full),
                "eat_ticks_left": c.get("eat_ticks_left", 0), "order_status": status,
                "reserved": list(c["reserved"]) if c.get("reserved") is not None else None,
                "base_price": c.get("base_price", self.menu[dish]["price"]), "tip": c.get("tip", 0),
            }
            for key in ("order_tick", "patience_ticks_left", "eat_ticks_left", "base_price", "tip"):
                v = cust[key]
                if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                    raise BadInput(f"customers.{c['id']}.{key} phải là số nguyên không âm")
            if cust["patience_ticks_left"] > self.patience_full:
                raise BadInput(f"customers.{c['id']}: kiên nhẫn vượt mức đầy")
            out.append(cust)
        # đơn reserved thiếu `reserved` thì cấp theo công thức, theo (order_tick, id bàn)
        taken = {iid for cust in out if cust["reserved"] for iid in cust["reserved"]}
        for cust in sorted(out, key=lambda e: (e["order_tick"], id_key(e["table_id"]))):
            if cust["order_status"] == "reserved":
                if cust["reserved"] is None:
                    picked = self._pick_for_recipe(self.menu[cust["dish_id"]]["recipe"], extra_held=taken)
                    if picked is None:
                        raise BadInput(f"customers.{cust['id']}: không đủ nguyên liệu để giữ chỗ")
                    cust["reserved"] = picked
                    taken.update(picked)
            else:
                if cust["reserved"]:
                    raise BadInput(f"customers.{cust['id']}: đơn {cust['order_status']} phải có giữ chỗ rỗng")
                cust["reserved"] = []
        return sort_by_id(out)

    def _check_links(self):
        by_id = {c["id"]: c for c in self.customers}
        held = {}  # order_id -> số nơi giữ món (bếp / tay)
        for s in self.stoves:
            if s["state"] == "idle":
                if s["dish"] is not None:
                    raise BadInput(f"bếp {s['id']} idle không được có món")
                continue
            d = s["dish"]
            if not isinstance(d, dict) or d.get("order_id") not in by_id:
                raise BadInput(f"bếp {s['id']}: món không khớp đơn nào")
            if d.get("dish_id") != by_id[d["order_id"]]["dish_id"]:
                raise BadInput(f"bếp {s['id']}: món không khớp đơn")
            if s["state"] == "cooking" and not s["cook_ticks_left"] > 0:
                raise BadInput(f"bếp {s['id']} cooking cần timer dương")
            held[d["order_id"]] = held.get(d["order_id"], 0) + 1
        if self.hand is not None:
            h = self.hand
            if not isinstance(h, dict) or h.get("order_id") not in by_id or h.get("dish_id") != by_id[h["order_id"]]["dish_id"]:
                raise BadInput("hand không khớp đơn nào")
            held[h["order_id"]] = held.get(h["order_id"], 0) + 1
        for c in self.customers:
            n = held.get(c["id"], 0)
            if n > 1:
                raise BadInput(f"đơn {c['id']} có món ở cả bếp và tay")
            if c["order_status"] == "assigned" and n != 1:
                raise BadInput(f"đơn assigned {c['id']} phải có đúng một món ở bếp hoặc tay")
            if c["order_status"] != "assigned" and n:
                raise BadInput(f"đơn {c['id']} không phải assigned nhưng có món đang nấu/trên tay")
            if c["state"] == "eating":
                if c["order_status"] != "served" or c["eat_ticks_left"] <= 0:
                    raise BadInput(f"khách eating {c['id']} phải served và có timer ăn dương")
            elif c["order_status"] == "served" or c["eat_ticks_left"] != 0:
                raise BadInput(f"khách waiting {c['id']} không được served / có timer ăn")
        stock_by_id = {it["id"]: it for it in self.stock}
        used_ids = set()
        for c in self.customers:
            if c["order_status"] == "reserved":
                r = c["reserved"]
                if len(r) != len(set(r)):
                    raise BadInput(f"customers.{c['id']}: reserved chứa id trùng")
                counts = {}
                for iid in r:
                    if iid not in stock_by_id:
                        raise BadInput(f"customers.{c['id']}: reserved id {iid} không có trong kho")
                    if iid in used_ids:
                        raise BadInput(f"customers.{c['id']}: id {iid} dùng chung với đơn khác")
                    it = stock_by_id[iid]
                    if spoiled(it, self.fr):
                        raise BadInput(f"customers.{c['id']}: cá thể {iid} đã ươn")
                    used_ids.add(iid)
                    counts[it["kind"]] = counts.get(it["kind"], 0) + 1
                if counts != self.menu[c["dish_id"]]["recipe"]:
                    raise BadInput(f"customers.{c['id']}: giữ chỗ khác công thức")
            elif c["reserved"]:
                raise BadInput(f"customers.{c['id']}: đơn {c['order_status']} phải có giữ chỗ rỗng")
        if self.plan_dishes is not None:
            for c in self.customers:
                if c["dish_id"] not in self.plan_dishes:
                    raise BadInput(f"customers.{c['id']}: món {c['dish_id']} không nằm trong kế hoạch ngày")

    # --- snapshot ---------------------------------------------------------------------------------------
    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": public_list(self.stock),
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    # --- một bước ---------------------------------------------------------------------------------------
    def step(self, inp):
        events = []
        # 1. đồng hồ, kiên nhẫn / ăn; hao tươi kho thô (kể cả giữ chỗ), xử lý giữ chỗ bị ươn; bếp chín
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.phase_tick += 1
        for c in self.customers:
            if c["state"] == "waiting":
                c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)
            else:
                c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)
        just_spoiled = decay(self.stock, self.decay_per_tick, self.fr, "stock", events)
        if just_spoiled:
            self._recheck_reserved(set(just_spoiled))
        for s in self.stoves:  # đã sắp theo id
            if s["state"] == "ready":
                s["ready_ticks"] += 1
            elif s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
                if s["cook_ticks_left"] == 0:
                    s["state"], s["ready_ticks"] = "ready", 0
                    events.append(("dish_ready", self._dish_data(s)))
        # 2. đi + tối đa một interact
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        # 3. khách theo id bàn: ăn xong trả tiền; còn giờ thì hết kiên nhẫn là bỏ đi
        open_shift = self.time_left_ticks > 0
        for c in self._by_table():
            if c["state"] == "eating" and c["eat_ticks_left"] == 0:
                self._pay(c, "finished_eating", events)
            elif open_shift and c["state"] == "waiting" and c["patience_ticks_left"] == 0:
                self.reputation = self._clamp_rep(self.reputation + self.t["left_reputation_delta"])
                self._leave(c, "patience", events)
        # 4. khách mới theo lịch (bước sau mới tương tác)
        if open_shift:
            self._maybe_spawn(events)
        # 5. hết ca: khách đang ăn trả ngay, khách đang chờ rời (không trừ uy tín), rồi quan_end
        if self.time_left_ticks <= 0:
            for c in self._by_table():
                if c["state"] == "eating":
                    self._pay(c, "closing", events)
                else:
                    self._leave(c, "closing", events)
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        return events

    # --- tiện ích ---------------------------------------------------------------------------------------
    def _clamp_rep(self, v):
        return round(min(self.t["reputation_max"], max(self.t["reputation_min"], v)), 9)

    def _by_table(self):
        return sorted(self.customers, key=lambda c: id_key(c["table_id"]))

    @staticmethod
    def _dish_data(stove):
        d = stove["dish"]
        return {"stove_id": stove["id"], "order_id": d["order_id"], "dish_id": d["dish_id"]}

    def _pick_for_recipe(self, recipe: dict, extra_held=None):
        """Chọn cá thể chưa ươn, tươi nhất trước (hòa id nhỏ) cho công thức; thiếu trả None."""
        held = {iid for c in getattr(self, "customers", ()) for iid in c["reserved"]}
        if extra_held:
            held |= set(extra_held)
        chosen = []
        for kind, need in sorted(recipe.items()):
            cands = [it for it in self.stock
                     if it["kind"] == kind and it["id"] not in held and not spoiled(it, self.fr)]
            if len(cands) < need:
                return None
            cands.sort(key=lambda it: (-it["units"], id_key(it["id"])))
            chosen.extend(it["id"] for it in cands[:need])
        return sorted(chosen, key=id_key)

    def _recheck_reserved(self, spoiled_ids: set):
        """Khi cá thể giữ vừa ươn: nhả toàn bộ phần giữ và giữ lại đúng 1 lần theo (order_tick, table_id)."""
        affected = [c for c in self.customers
                    if c["order_status"] == "reserved" and any(iid in spoiled_ids for iid in c["reserved"])]
        for c in sorted(affected, key=lambda e: (e["order_tick"], id_key(e["table_id"]))):
            c["reserved"] = []
            picked = self._pick_for_recipe(self.menu[c["dish_id"]]["recipe"])
            if picked is not None:
                c["reserved"] = picked
            else:
                c["order_status"] = "unfulfillable"

    def _interact(self, events):
        radius = self.t["interact_radius"]
        cands = []
        for kind_rank, objs in ((0, self.stoves), (1, self.tables)):
            for o in objs:
                d = math.dist(self.pos, o["pos"])
                if d <= radius:
                    cands.append((d, kind_rank, id_key(o["id"]), kind_rank, o))
        if not cands:
            return
        *_, rank, obj = min(cands, key=lambda c: c[:3])
        if rank == 0:
            self._use_stove(obj, events)
        else:
            self._use_table(obj, events)

    def _use_stove(self, s, events):
        if s["state"] == "idle":
            waiting = [c for c in self.customers if c["order_status"] == "reserved"]
            if not waiting:
                return
            c = min(waiting, key=lambda e: (e["order_tick"], id_key(e["table_id"])))
            recipe = self.menu[c["dish_id"]]
            rset = set(c["reserved"])
            used = [it for it in self.stock if it["id"] in rset]
            self.stock = [it for it in self.stock if it["id"] not in rset]
            total_units = sum(it["units"] for it in used)
            base_price = (recipe["price"] * total_units) // (100 * len(used) * UNITS)
            c["base_price"] = base_price
            items = [public(it) for it in sorted(used, key=lambda it: (it["kind"], id_key(it["id"])))]
            c["reserved"], c["order_status"] = [], "assigned"
            s["state"] = "cooking"
            s["dish"] = {"order_id": c["id"], "dish_id": c["dish_id"], "base_price": base_price}
            s["cook_ticks_left"] = int(round(recipe["cook_s"] * TICK))
            s["ready_ticks"] = 0
            data = self._dish_data(s)
            data.update(items=items, base_price=base_price)
            events.append(("cook_started", data))
        elif s["state"] == "ready" and self.hand is None:
            data = self._dish_data(s)
            self.hand = s["dish"]
            s["state"], s["dish"], s["cook_ticks_left"], s["ready_ticks"] = "idle", None, 0, 0
            events.append(("dish_picked", data))

    def _use_table(self, tb, events):
        if self.hand is None:
            return
        c = next((x for x in self.customers if x["table_id"] == tb["id"]), None)
        if c is None or c["id"] != self.hand["order_id"] or c["state"] != "waiting":
            return
        ratio_ok = c["patience_ticks_left"] >= self.t["tip_min_patience_ratio"] * self.patience_full
        tip = math.floor(c["base_price"] * self.t["tip_rate"] + 1e-9) if ratio_ok else 0
        c["state"], c["order_status"] = "eating", "served"
        c["eat_ticks_left"] = int(round(self.t["eat_s"] * TICK))
        c["tip"] = tip
        self.hand = None
        events.append(("served", {"order_id": c["id"], "table_id": c["table_id"], "dish_id": c["dish_id"],
                                  "patience_ticks_left": c["patience_ticks_left"],
                                  "base_price": c["base_price"], "tip": tip}))

    def _pay(self, c, reason, events):
        amount = c["base_price"] + c["tip"]
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if c["tip"] > 0:
            self.reputation = self._clamp_rep(self.reputation + self.t["tip_reputation"])
        events.append(("paid", {"order_id": c["id"], "table_id": c["table_id"], "base_price": c["base_price"],
                                "tip": c["tip"], "amount": amount, "reason": reason}))
        self.customers.remove(c)

    def _leave(self, c, reason, events):
        """Khách rời: nhả giữ chỗ thô, bỏ món của đơn (đang nấu, ready, trên tay). Nguyên liệu đã dùng không hoàn."""
        for s in self.stoves:
            if s["dish"] is not None and s["dish"]["order_id"] == c["id"]:
                s["state"], s["dish"], s["cook_ticks_left"], s["ready_ticks"] = "idle", None, 0, 0
        if self.hand is not None and self.hand["order_id"] == c["id"]:
            self.hand = None
        self.customers.remove(c)
        events.append(("customer_left", {"order_id": c["id"], "table_id": c["table_id"], "reason": reason,
                                         "reputation": self.reputation}))

    def _maybe_spawn(self, events):
        first = int(self.t["first_customer_tick"])
        gap = int(round(self.t["customer_interval_s"] * TICK))
        if not self.random_customers or self.phase_tick < first or (self.phase_tick - first) % gap != 0:
            return
        taken = {c["table_id"] for c in self.customers}
        free = [tb for tb in self.tables if tb["id"] not in taken]
        if not free:
            return
        table = free[0]  # self.tables đã sắp theo id
        pool = [d for d in sorted(self.menu)
                if self.plan_dishes is None or d in self.plan_dishes]
        doable = [d for d in pool if self._pick_for_recipe(self.menu[d]["recipe"]) is not None]
        if not doable:
            events.append(("no_dish", {}))
            return
        dish = doable[self.rng.get("customer_dish").randrange(len(doable))]
        reserved = self._pick_for_recipe(self.menu[dish]["recipe"])
        cid = self.ids.new("C")
        self.customers.append({
            "id": cid, "table_id": table["id"], "dish_id": dish, "order_tick": self.phase_tick,
            "state": "waiting", "patience_ticks_left": self.patience_full, "eat_ticks_left": 0,
            "order_status": "reserved", "reserved": reserved,
            "base_price": self.menu[dish]["price"], "tip": 0})
        events.append(("customer_arrived", {"order_id": cid, "table_id": table["id"], "dish_id": dish}))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
