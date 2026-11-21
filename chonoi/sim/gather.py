"""Buổi sáng — Lặn & Hái (`gather`), Test Contract v1.1.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.

Giỏ (v1.2, Ticket-03): mảng cá thể {id, kind, units} theo thứ tự vào giỏ; id `I<n>` cấp từ `item_ids`.

Thứ tự một bước (Ticket-02 mục 4.5, Ticket-03):
  1. đồng hồ, phase_tick, hồi bắt, bất tử, hồi nút (node_regrown), hao tươi giỏ (spoiled theo id)
  2. bơi + chặn mép, dive/surface, oxy theo d cuối bước, ngạt (choke) -> ngất (faint) thì dừng
  3. Cá Sấu theo id (patrol/chase/recoil), tối đa một hit (monster_hit) -> ngất thì dừng
  4. interact: bến trước, rồi hái ở mặt nước
  5. catch: đàn gần nhất theo vị trí cá TRƯỚC khi bơi
  6. hết giờ -> gather_end(time)
  7. còn giờ: cá bơi, rồi sinh cá theo lịch (fish_spawned); cá mới tham gia từ bước sau
Số liệu chỉ đọc từ tuning["gather"]; ngẫu nhiên qua Streams ("fish_spawn", "fish_turn").
"""

import math

from ..ids import id_key, sort_by_id
from ..items import decay, new_item, public, public_list, units_per_tick
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


def _unit(dx, dd):
    n = math.hypot(dx, dd)
    return (1.0, 0.0) if n == 0 else (dx / n, dd / n)


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1, item_ids=None, creative=False):
        t = tuning["gather"]
        self.t = t
        self.creative = creative
        self.rng = streams
        self.ids = ids
        self.item_ids = item_ids if item_ids is not None else ids  # `day` truyền bộ cấp id cá thể xuyên pha/Ngày
        self.fr = tuning["freshness"]
        self.decay_units = units_per_tick(self.fr["gather_decay_per_s"])
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = int(round(t["oxygen_max_s"] * TICK))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", t["hp_max"])
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = [dict(it) for it in scenario.get("hold", [])]  # cá thể theo thứ tự nhặt, cuối là mới nhất
        for it in self.hold:
            self.item_ids.reserve(it["id"])
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = 0
        # nút, đàn cá, Cá Sấu: scenario THAY THẾ danh sách mặc định
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        # random_fish=false: tắt cá mặc định, cá bơi và sinh cá; cá fixture đứng yên
        self.random_fish = scenario.get("random_fish", True)
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                      "heading_deg": float(f.get("heading_deg", 0)), "age_ticks": f.get("age_ticks", 0)}
                     for f in scenario.get("fish", [])]
        mon = t.get("monsters", {})
        self.species = mon.get("species", {})
        if "monsters" in scenario:
            src_mon = scenario["monsters"]
        else:
            src_mon = [m for m in mon.get("spawns", []) if m.get("from_day", 1) <= day]
        self.monsters = sort_by_id([{
            "id": m["id"], "kind": m["kind"], "pos": [float(c) for c in m["pos"]],
            "waypoints": [[float(c) for c in w] for w in m["waypoints"]],
            "target_idx": m.get("target_idx", 1), "state": m.get("state", "patrol"),
            "state_ticks_left": m.get("state_ticks_left", 0),
            "recoil_dir": list(m["recoil_dir"]) if m.get("recoil_dir") is not None else None,
        } for m in src_mon])
        for coll in (self.nodes, self.fish, self.monsters):
            for e in coll:
                ids.reserve(e["id"])
        if "fish" not in scenario and self.random_fish:
            for _ in range(int(t["fish_initial"])):
                f = self._spawn_one()
                if f is None:
                    break
        if self.creative:
            self._init_creative(t)
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> list:
        """Kho bàn giao: cá thể nội bộ (bản sao), sắp theo id khi xuất."""
        return [dict(it) for it in self.hold]

    def snapshot(self) -> dict:
        p = {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
             "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
             "hp": self.hp, "hp_max": self.t["hp_max"], "zero_oxy_ticks": self.zero_oxy_ticks,
             "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
             "at_surface": self._at_surface()}
        if self.creative:
            p.update({
                "energy_ticks": round(self.energy_ticks, 1),
                "energy_max_ticks": self.energy_max,
                "sprinting": self.sprinting,
                "shoot_cd_ticks": self.shoot_cd_ticks,
                "ult_cd_ticks": self.ult_cd_ticks,
                "ult_cd_max_ticks": self.ult_cd_max,
                "ult_active_ticks": self.ult_active_ticks,
            })
        s = {
            "player": p,
            "hold": public_list(self.hold, by_id=False), "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"],
                      "age_ticks": f["age_ticks"]} for f in sort_by_id(self.fish)],
            "monsters": [dict(m) for m in self.monsters],
        }
        if self.creative:
            s["bullets"] = [{"id": b["id"], "pos": list(b["pos"]), "vel": list(b["vel"]), "ult": b["ult"]} for b in self.bullets]
            s["tongues"] = list(self.tongues)
        return s

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.phase_tick += 1
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        decay(self.hold, self.decay_units, self.fr, "hold", events)  # hàng có sẵn ở đầu bước
        # 2. bơi + chặn mép; so phân vùng đầu/cuối bước -> dive / surface; oxy, ngạt
        was_under = not self._at_surface()
        self._move(inp)
        under = not self._at_surface()
        if under != was_under:
            events.append(("dive" if under else "surface", {"pos": list(self.pos)}))
        if self._breathe(events):
            return events
        # 3. Cá Sấu
        if self._update_monsters(events):
            return events
        # 4. interact: bến trước, rồi hái
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if not under:
                self._gather_node(events)
        # 5. bắt cá (vị trí cá trước khi bơi)
        if inp.pressed("catch") and self.catch_cd_ticks == 0 and under:
            self._catch_fish(events)
        if self.creative:
            self._step_creative(inp, events)
        # 6. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events
        # 7. cá bơi, sinh cá
        if self.random_fish:
            self._swim_fish()
            self._maybe_spawn(events)
        return events

    # --- oxy -----------------------------------------------------------------------
    def _breathe(self, events) -> bool:
        """Trả True nếu người chơi ngất (đã phát faint + gather_end)."""
        if self._at_surface():
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + int(self.t["oxygen_refill_per_tick"]))
            self.zero_oxy_ticks = 0
            return False
        before = self.oxygen_ticks
        self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
        if before > 0 and self.oxygen_ticks == 0:
            events.append(("oxygen_empty", {"oxygen_ticks": 0}))
        if self.oxygen_ticks > 0:
            return False
        self.zero_oxy_ticks += 1
        if self.zero_oxy_ticks < int(self.t["choke_interval_ticks"]):
            return False
        self.zero_oxy_ticks = 0
        self.hp -= 1  # ngạt xuyên bất tử, không làm rơi hàng
        events.append(("choke", {"hp": self.hp}))
        return self._faint_if_dead("choke", events)

    def _faint_if_dead(self, cause, events) -> bool:
        if self.hp > 0:
            return False
        lost = [public(it) for it in reversed(self.hold)]  # nhặt sau bỏ trước (LIFO)
        self.hold = []
        events.append(("faint", {"cause": cause, "lost": lost, "hp": 0}))
        self._finish("fainted", events)
        return True

    # --- Cá Sấu ---------------------------------------------------------------------
    def _clamp_monster(self, m):
        sp = self.species[m["kind"]]
        lo_x, hi_x = self.t["bounds"]["x"]
        lo_d, hi_d = sp["depths"]
        m["pos"][0] = min(hi_x, max(lo_x, m["pos"][0]))
        m["pos"][1] = min(hi_d, max(lo_d, m["pos"][1]))

    @staticmethod
    def _toward(pos, target, step):
        dist = math.dist(pos, target)
        if dist <= step + 1e-9:  # cộng dồn n × (v/60) lệch vài ulp: coi như tới đúng bước dự kiến
            return [target[0], target[1]], True
        ux, ud = (target[0] - pos[0]) / dist, (target[1] - pos[1]) / dist
        return [pos[0] + ux * step, pos[1] + ud * step], False

    def _update_monsters(self, events) -> bool:
        for m in self.monsters:  # đã sắp theo id
            if m["kind"] != "ca_sau":
                continue
            sp = self.species[m["kind"]]
            if m["state"] == "recoil":
                step = sp["recoil_dist"] / sp["recoil_ticks"]
                m["pos"] = [m["pos"][0] + m["recoil_dir"][0] * step, m["pos"][1] + m["recoil_dir"][1] * step]
                self._clamp_monster(m)
                m["state_ticks_left"] -= 1
                if m["state_ticks_left"] <= 0:
                    m["state"], m["state_ticks_left"], m["recoil_dir"] = "patrol", 0, None
                continue
            dist = math.dist(m["pos"], self.pos)
            deep = self.pos[1] >= sp["depths"][0]
            if m["state"] == "patrol" and deep and dist <= sp["detect_radius"]:
                m["state"] = "chase"
            elif m["state"] == "chase" and (not deep or dist > sp["exit_radius"]):
                m["state"] = "patrol"
            if m["state"] == "chase":
                m["pos"], _ = self._toward(m["pos"], self.pos, sp["chase_speed"] / TICK)
            else:
                target = m["waypoints"][m["target_idx"]]
                m["pos"], reached = self._toward(m["pos"], target, sp["patrol_speed"] / TICK)
                if reached:
                    m["target_idx"] = 1 - m["target_idx"]
            self._clamp_monster(m)
        if self.creative and self._update_creative_monsters(events):
            return True
        if self.invuln_ticks > 0:
            return False
        cands = []
        for m in self.monsters:
            if m["kind"] != "ca_sau":
                continue
            sp = self.species[m["kind"]]
            if m["state"] == "recoil" or self.pos[1] < sp["depths"][0]:
                continue
            d = math.dist(m["pos"], self.pos)
            if d <= sp["hit_radius"]:
                cands.append((d, id_key(m["id"]), m))
        if not cands:
            return False
        _, _, m = min(cands, key=lambda c: c[:2])
        mon = self.t["monsters"]
        self.hp -= 1
        n = int(math.floor(len(self.hold) * mon["loss_ratio"]))
        lost = [public(it) for it in reversed(self.hold[len(self.hold) - n:])] if n else []
        if n:
            self.hold = self.hold[:len(self.hold) - n]
        self.invuln_ticks = int(mon["invuln_ticks"])
        m["state"] = "recoil"
        m["state_ticks_left"] = int(self.species[m["kind"]]["recoil_ticks"])
        m["recoil_dir"] = list(_unit(m["pos"][0] - self.pos[0], m["pos"][1] - self.pos[1]))
        events.append(("monster_hit", {"monster_id": m["id"], "hp": self.hp, "lost": lost, "pos": list(self.pos)}))
        return self._faint_if_dead("monster", events)

    # --- hái, bắt -------------------------------------------------------------------
    def _add(self, kind, amount):
        """Hàng mới fresh = initial, hao từ bước sau."""
        for _ in range(amount):
            self.hold.append(new_item(self.item_ids.new("I"), kind, self.fr["initial"]))

    def _free(self) -> int:
        return int(self.t["hold_capacity"]) - len(self.hold)

    def _nearest(self, items, radius):
        """Phần tử gần nhất trong bán kính (kể cả đúng mép), hòa thì id nhỏ (sort_by_id ổn định)."""
        best, best_d = None, None
        for e in sort_by_id(items):
            d = math.dist(self.pos, e["pos"])
            if d <= radius and (best is None or d < best_d):
                best, best_d = e, d
        return best

    def _gather_node(self, events):
        node = self._nearest([n for n in self.nodes if n["regrow_ticks"] == 0], self.t["interact_radius"])
        if node is None:
            return
        amount = int(self.t["node_yield"])
        free = self._free()
        if free < amount:
            events.append(("hold_full", {"action": "gather", "node_id": node["id"], "required": amount, "free": free}))
            return
        self._add(node["kind"], amount)
        node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
        events.append(("gather", {"node_id": node["id"], "kind": node["kind"], "amount": amount}))

    def _catch_fish(self, events):
        fish = self._nearest(self.fish, self.t["catch_radius"])
        if fish is None:
            return
        amount = int(self.t["fish_yield"][fish["kind"]])
        free = self._free()
        if free < amount:
            events.append(("hold_full", {"action": "catch", "fish_id": fish["id"], "required": amount, "free": free}))
            return
        self._add(fish["kind"], amount)
        self.fish.remove(fish)
        self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
        events.append(("fish_caught", {"fish_id": fish["id"], "kind": fish["kind"], "yield": amount}))

    # --- cá bơi, sinh cá ---------------------------------------------------------------
    def _swim_fish(self):
        t = self.t
        step = t["fish_speed"] / TICK
        turn = int(t["fish_turn_ticks"])
        lo_x, hi_x = t["fish_x"]
        for f in sort_by_id(self.fish):
            f["age_ticks"] += 1
            if f["age_ticks"] % turn == 0:  # đổi hướng TRƯỚC khi di chuyển
                f["heading_deg"] = self.rng.get("fish_turn").random() * 360.0
            rad = math.radians(f["heading_deg"])
            v = [math.cos(rad) * step, math.sin(rad) * step]
            lo_d, hi_d = t["fish_depths"][f["kind"]]
            flipped = False
            for i, (lo, hi) in enumerate(((lo_x, hi_x), (lo_d, hi_d))):
                c = f["pos"][i] + v[i]
                if c < lo:  # phản xạ phần quãng đường còn lại, đảo thành phần vuông góc với mép
                    c, v[i], flipped = lo + (lo - c), -v[i], True
                elif c > hi:
                    c, v[i], flipped = hi - (c - hi), -v[i], True
                f["pos"][i] = min(hi, max(lo, c))
            if flipped:
                f["heading_deg"] = math.degrees(math.atan2(v[1], v[0])) % 360.0

    def _spawn_one(self):
        """Sinh một đàn ở điểm chuẩn cách mọi đàn đang sống > clearance; None nếu hết điểm."""
        t = self.t
        clear = t["fish_spawn_clearance"]
        weights = t["fish_weights"]
        points = {}
        for kind in sorted(weights):  # id loài theo mã Unicode
            pts = [(x, d) for x in t["fish_spawn_x"] for d in t["fish_spawn_depths"][kind]
                   if all(math.dist((x, d), f["pos"]) > clear for f in self.fish)]
            if pts:
                points[kind] = pts
        if not points:
            return None
        rng = self.rng.get("fish_spawn")
        kinds = list(points)
        r = rng.random() * sum(weights[k] for k in kinds)
        kind = kinds[-1]
        for k in kinds:
            r -= weights[k]
            if r < 0:
                kind = k
                break
        x, d = points[kind][rng.randrange(len(points[kind]))]
        fish = {"id": self.ids.new("F"), "kind": kind, "pos": [float(x), float(d)],
                "heading_deg": rng.random() * 360.0, "age_ticks": 0}
        self.fish.append(fish)
        return fish

    def _maybe_spawn(self, events):
        every = int(self.t["fish_spawn_ticks"])
        if self.phase_tick % every != 0 or len(self.fish) >= int(self.t["fish_max"]):
            return
        f = self._spawn_one()
        if f is not None:
            events.append(("fish_spawned", {"id": f["id"], "kind": f["kind"], "pos": list(f["pos"])}))

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": public_list(self.hold)}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        if self.creative:
            want_sprint = bool(inp.held.get("sprint")) and (mx != 0.0 or md != 0.0)
            if want_sprint and self.energy_ticks > 0.0:
                self.sprinting = True
                self.energy_ticks = max(0.0, self.energy_ticks - 1.0)
                speed = speed * 1.65
            else:
                self.sprinting = False
                self.energy_ticks = min(float(self.energy_max), self.energy_ticks + 0.5)
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])

    # --- sáng tạo (chỉ bật ở live): năng lượng, súng, ultimate, cá voi sát thủ, ếch ---
    def _init_creative(self, t):
        self.energy_max = int(round(t.get("energy_max_s", 5) * TICK))
        self.energy_ticks = float(self.energy_max)
        self.sprinting = False
        self.shoot_cd_ticks = 0
        self.ult_cd_max = int(25 * TICK)
        self.ult_cd_ticks = self.ult_cd_max  # mặc định đang hồi chiêu 25s
        self.ult_active_ticks = 0
        self.ult_dir = self.heading
        self.bullets = []
        self.tongues = []
        for m in self.monsters:
            m.setdefault("hp", 4)
            m.setdefault("hp_max", 4)
            m.setdefault("hit_ticks", 0)
        # thêm cá sấu để sông nguy hiểm hơn
        if len(self.monsters) < 3 and "ca_sau" in self.species:
            extra_wps = [
                ([[22.0, 14.0], [46.0, 18.0]]),
                ([[58.0, 12.0], [88.0, 22.0]]),
            ]
            for wps in extra_wps:
                if len(self.monsters) >= 3:
                    break
                mid = self.ids.new("M")
                self.monsters.append({
                    "id": mid, "kind": "ca_sau", "pos": list(wps[0]),
                    "waypoints": wps, "target_idx": 1, "state": "patrol",
                    "state_ticks_left": 0, "recoil_dir": None,
                    "hp": 4, "hp_max": 4, "hit_ticks": 0,
                })
            self.monsters = sort_by_id(self.monsters)
        rng = self.rng.get("fish_spawn")
        self._orca_timer = rng.randint(300, 540)
        self._frog_timer = rng.randint(180, 420)

    def _fire_bullet(self, deg, is_ult=False):
        rad = math.radians(deg)
        spd = 34.0 if is_ult else 26.0
        bid = self.ids.new("B")
        self.bullets.append({
            "id": bid,
            "pos": [self.pos[0] + math.cos(rad) * 0.8, self.pos[1] + math.sin(rad) * 0.8],
            "vel": [math.cos(rad) * spd, math.sin(rad) * spd],
            "ttl": 90,
            "ult": is_ult,
        })

    def _step_creative(self, inp, events):
        self.shoot_cd_ticks = max(0, self.shoot_cd_ticks - 1)
        if self.ult_cd_ticks > 0:
            self.ult_cd_ticks -= 1
        aim = inp.aim_deg if inp.aim_deg is not None else self.heading
        if inp.pressed("ult") and self.ult_cd_ticks == 0:
            self.ult_cd_ticks = self.ult_cd_max
            self.ult_active_ticks = 90  # 1.5s bắn liên thanh kiểu Lucian
            self.ult_dir = aim
            events.append(("ult_used", {}))
        if self.ult_active_ticks > 0:
            if inp.aim_deg is not None:
                self.ult_dir = inp.aim_deg
            elif inp.move != (0.0, 0.0):
                self.ult_dir = self.heading
            if self.ult_active_ticks % 4 == 0:
                spread = ((self.ult_active_ticks % 12) - 4) * 0.8
                self._fire_bullet(self.ult_dir + spread, is_ult=True)
            self.ult_active_ticks -= 1
        elif (inp.pressed("shoot") or inp.held.get("shoot")) and self.shoot_cd_ticks == 0:
            self.shoot_cd_ticks = 18
            self._fire_bullet(aim, is_ult=False)

        # cập nhật đạn & va chạm quái
        b = self.t["bounds"]
        lo_x, hi_x = b["x"]
        lo_d, hi_d = b["d"]
        kept_bullets = []
        for bl in self.bullets:
            bl["pos"][0] += bl["vel"][0] / TICK
            bl["pos"][1] += bl["vel"][1] / TICK
            bl["ttl"] -= 1
            if bl["ttl"] <= 0 or not (lo_x - 2 <= bl["pos"][0] <= hi_x + 2 and lo_d <= bl["pos"][1] <= hi_d + 1):
                continue
            hit_m = None
            for m in self.monsters:
                hr = 2.0 if m["kind"] == "ca_voi_sat_thu" else 1.2
                if math.dist(bl["pos"], m["pos"]) <= hr:
                    hit_m = m
                    break
            if hit_m is not None:
                hit_m["hp"] = hit_m.get("hp", 4) - 1
                hit_m["hit_ticks"] = 8
                if hit_m["hp"] <= 0:
                    self.monsters.remove(hit_m)
                    events.append(("monster_defeated", {"id": hit_m["id"], "kind": hit_m["kind"], "pos": list(hit_m["pos"])}))
                continue
            kept_bullets.append(bl)
        self.bullets = kept_bullets

        # sinh Cá Voi Sát Thủ & Ếch ngẫu nhiên
        rng = self.rng.get("fish_spawn")
        self._orca_timer -= 1
        if self._orca_timer <= 0:
            self._spawn_orca(rng, events)
            self._orca_timer = rng.randint(720, 1140)
        self._frog_timer -= 1
        if self._frog_timer <= 0:
            self._spawn_frog(rng, events)
            self._frog_timer = rng.randint(600, 960)

    def _spawn_orca(self, rng, events):
        lo_x, hi_x = self.t["bounds"]["x"]
        lo_d, hi_d = self.t["bounds"]["d"]
        from_left = rng.random() < 0.5
        x = lo_x - 3.5 if from_left else hi_x + 3.5
        d = rng.uniform(max(6.0, lo_d + 5.0), max(8.0, hi_d - 4.0))
        vx = 13.0 if from_left else -13.0
        m = {
            "id": self.ids.new("M"), "kind": "ca_voi_sat_thu",
            "pos": [x, d], "vx": vx, "state": "swim",
            "hp": 6, "hp_max": 6, "hit_ticks": 0,
        }
        self.monsters.append(m)
        events.append(("orca_spawned", {"id": m["id"], "pos": list(m["pos"])}))

    def _spawn_frog(self, rng, events):
        if sum(1 for m in self.monsters if m["kind"] == "ech") >= 2:
            return
        lo_x, hi_x = self.t["bounds"]["x"]
        hi_d = self.t["bounds"]["d"][1]
        x = rng.uniform(lo_x + 12.0, hi_x - 8.0)
        d = hi_d - 0.7
        m = {
            "id": self.ids.new("M"), "kind": "ech",
            "pos": [x, d], "state": "idle", "state_ticks_left": 150,
            "life_ticks": rng.randint(720, 960), "target_pos": None,
            "hp": 3, "hp_max": 3, "hit_ticks": 0,
        }
        self.monsters.append(m)
        events.append(("frog_spawned", {"id": m["id"], "pos": list(m["pos"])}))

    def _update_creative_monsters(self, events) -> bool:
        lo_x, hi_x = self.t["bounds"]["x"]
        self.tongues = []
        to_remove = []
        for m in list(self.monsters):
            if m.get("hit_ticks", 0) > 0:
                m["hit_ticks"] -= 1
            k = m["kind"]
            if k == "ca_voi_sat_thu":
                m["pos"][0] += m["vx"] / TICK
                if m["pos"][0] < lo_x - 6.0 or m["pos"][0] > hi_x + 6.0:
                    to_remove.append(m)
                    continue
                if self.invuln_ticks == 0 and math.dist(m["pos"], self.pos) <= 1.85:
                    if self._apply_monster_damage(m, events):
                        return True
            elif k == "ech":
                m["life_ticks"] -= 1
                if m["life_ticks"] <= 0 and m["state"] == "idle":
                    to_remove.append(m)
                    continue
                if m["state"] == "idle":
                    m["state_ticks_left"] -= 1
                    if m["state_ticks_left"] <= 0:
                        if math.dist(m["pos"], self.pos) <= 22.0 and not self._at_surface():
                            m["state"] = "aiming"
                            m["state_ticks_left"] = 30
                            m["target_pos"] = list(self.pos)
                        else:
                            m["state_ticks_left"] = 45
                elif m["state"] == "aiming":
                    m["state_ticks_left"] -= 1
                    self.tongues.append({"from": list(m["pos"]), "to": list(m["target_pos"]), "prog": 0.0, "aiming": True})
                    if m["state_ticks_left"] <= 0:
                        m["state"] = "tongue"
                        m["state_ticks_left"] = 24
                elif m["state"] == "tongue":
                    m["state_ticks_left"] -= 1
                    t_left = m["state_ticks_left"]
                    prog = 1.0 - abs(t_left - 12) / 12.0  # phóng ra rồi thu về
                    fx, fd = m["pos"]
                    tx, td = m["target_pos"]
                    cur_to = [fx + (tx - fx) * prog, fd + (td - fd) * prog]
                    self.tongues.append({"from": list(m["pos"]), "to": cur_to, "prog": prog, "aiming": False})
                    if self.invuln_ticks == 0 and math.dist(cur_to, self.pos) <= 1.1:
                        if self._apply_monster_damage(m, events):
                            return True
                    if m["state_ticks_left"] <= 0:
                        m["state"] = "idle"
                        m["state_ticks_left"] = 180
        for m in to_remove:
            if m in self.monsters:
                self.monsters.remove(m)
        return False

    def _apply_monster_damage(self, m, events) -> bool:
        mon = self.t["monsters"]
        self.hp -= 1
        n = int(math.floor(len(self.hold) * mon["loss_ratio"]))
        lost = [public(it) for it in reversed(self.hold[len(self.hold) - n:])] if n else []
        if n:
            self.hold = self.hold[:len(self.hold) - n]
        self.invuln_ticks = int(mon["invuln_ticks"])
        events.append(("monster_hit", {"monster_id": m["id"], "hp": self.hp, "lost": lost, "pos": list(self.pos)}))
        return self._faint_if_dead("monster", events)
