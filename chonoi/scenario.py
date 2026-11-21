"""Nạp và kiểm scenario (Contract D). Trả về dict của đúng khối theo mode.

KHUNG: kiểm cú pháp, id trùng, bộ đếm âm, khoang vượt sức chứa, trường lạ.
TODO(nhóm): bổ sung kiểm mâu thuẫn mức luật mà nhóm cần (khách giữ chỗ quá kho, đơn assigned
phải có đúng một món, khách eating thiếu giá/tip...) — xem PRD-0 mục D và 'Mâu thuẫn -> mã 2'.
"""

import json
import math

from .errors import BadInput
from .inventory import KINDS_P1
from .items import parse_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "time_left_ticks", "monsters"}
MONSTER_KEYS = {"id", "kind", "pos", "waypoints", "target_idx", "state", "state_ticks_left", "recoil_dir"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}


def load_scenario(path, mode: str, tuning: dict) -> dict:
    """gather/quan: trả khối của mode. day: trả {gather?, quan?, day?} (mẫu khởi tạo mỗi Ngày)."""
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan", "day"}:
        raise BadInput("scenario chỉ được có khối 'gather', 'quan' hoặc 'day'")
    allowed_blocks = {"gather", "quan", "day"} if mode == "day" else {mode}
    if set(data) - allowed_blocks:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận {sorted(allowed_blocks)}")
    if mode != "day":
        return _load_block(data.get(mode, {}), mode, tuning)
    out = {}
    for m in ("gather", "quan"):
        if m in data:
            out[m] = _load_block(data[m], m, tuning)
    if "stock" in out.get("quan", {}) or "reputation" in out.get("quan", {}):
        raise BadInput("day: không khai quan.stock / quan.reputation (dùng gather.hold, day.reputation)")
    if "day" in data:
        out["day"] = _validate_day(data["day"], tuning)
    return out


def _load_block(block, mode, tuning):
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * 60))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)
    return block


def _validate_day(d, tuning):
    if not isinstance(d, dict):
        raise BadInput("khối day phải là object")
    extra = set(d) - DAY_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong day: {sorted(extra)}")
    for key in ("money", "earned"):
        if key in d:
            _nonneg_int(f"day.{key}", d[key])
    money, earned = d.get("money", 0), d.get("earned", 0)
    if money > 0 and "earned" not in d:
        raise BadInput("day: có tiền đầu kỳ thì khai cả earned")
    if money > earned:
        raise BadInput("day: cần 0 <= money <= earned")
    q = tuning["quan"]
    if "reputation" in d and not (_num(d["reputation"]) and q["reputation_min"] <= d["reputation"] <= q["reputation_max"]):
        raise BadInput("day.reputation ngoài dải uy tín")
    ups = tuning["shop"]["upgrades"]
    u = d.get("upgrades", {})
    if not isinstance(u, dict):
        raise BadInput("day.upgrades phải là object")
    for k, lv in u.items():
        if k not in ups:
            raise BadInput(f"day.upgrades: nâng cấp lạ {k}")
        _nonneg_int(f"day.upgrades.{k}", lv)
        if lv > max(x["level"] for x in ups[k]):
            raise BadInput(f"day.upgrades.{k} vượt cấp tối đa")
    plans = d.get("day_plan", [])
    if not isinstance(plans, list):
        raise BadInput("day.day_plan phải là mảng")
    seen = set()
    menu = tuning["menu"]
    for p in plans:
        if not isinstance(p, dict) or set(p) - {"day", "dishes", "ingredients"} or "dishes" not in p:
            raise BadInput("day.day_plan: mỗi mục là {day, dishes, ingredients?}")
        n = p.get("day")
        if isinstance(n, bool) or not isinstance(n, int) or not (1 <= n <= 5) or n in seen:
            raise BadInput("day.day_plan: day phải là số Ngày 1..5, không trùng")
        seen.add(n)
        dishes = p["dishes"]
        if not isinstance(dishes, dict) or not dishes:
            raise BadInput("day.day_plan.dishes phải là map món -> số suất")
        ing = {}
        for dish, k in dishes.items():
            if dish not in menu:
                raise BadInput(f"day.day_plan: món lạ {dish}")
            if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
                raise BadInput(f"day.day_plan: số suất {dish} phải là số nguyên dương")
            for kind, v in menu[dish]["recipe"].items():
                ing[kind] = ing.get(kind, 0) + v * k
        if "ingredients" in p and p["ingredients"] != ing:
            raise BadInput(f"day.day_plan Ngày {n}: ingredients không khớp công thức × suất")
    return d


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish", "monsters"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        # v1.2: mảng cá thể {id, kind, fresh} theo thứ tự vào giỏ -> cá thể nội bộ {id, kind, units}
        b["hold"] = parse_items(b["hold"], KINDS_P1, "gather.hold")
        if len(b["hold"]) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax = int(round(g["oxygen_max_s"] * 60))
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= g["hp_max"]):
        raise BadInput("player.hp phải trong [1, hp_max]")
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] > 59:
            raise BadInput("player.zero_oxy_ticks phải trong [0, 59]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    for n in b.get("nodes", []):
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {NODE_KINDS}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        if f.get("kind") not in FISH_KINDS:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {FISH_KINDS}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")
        if "age_ticks" in f:
            _nonneg_int(f"fish.{f['id']}.age_ticks", f["age_ticks"])
    species = g["monsters"]["species"]
    for m in b.get("monsters", []):
        mid = m["id"]
        extra = set(m) - MONSTER_KEYS
        if extra:
            raise BadInput(f"monsters.{mid}: trường lạ/chưa hỗ trợ {sorted(extra)}")
        if m.get("kind") not in species:
            raise BadInput(f"monsters.{mid}: kind phải thuộc {sorted(species)}")
        _pos(f"monsters.{mid}.pos", m.get("pos"), bounds)
        wps = m.get("waypoints")
        if not isinstance(wps, list) or len(wps) != 2:
            raise BadInput(f"monsters.{mid}: cần đúng 2 waypoints")
        for w in wps:
            _pos(f"monsters.{mid}.waypoints", w, bounds)
        if m.get("target_idx", 1) not in (0, 1) or isinstance(m.get("target_idx", 1), bool):
            raise BadInput(f"monsters.{mid}.target_idx phải là 0 hoặc 1")
        state = m.get("state", "patrol")
        if state not in ("patrol", "chase", "recoil"):
            raise BadInput(f"monsters.{mid}.state phải là patrol, chase hoặc recoil")
        left = m.get("state_ticks_left", 0)
        _nonneg_int(f"monsters.{mid}.state_ticks_left", left)
        rd = m.get("recoil_dir")
        if state == "recoil":
            if left <= 0 or not (isinstance(rd, list) and len(rd) == 2 and all(_num(c) for c in rd)
                                 and abs(math.hypot(*rd) - 1) < 1e-6):
                raise BadInput(f"monsters.{mid}: recoil cần timer dương và recoil_dir là vector đơn vị")
        elif rd is not None or left != 0:
            raise BadInput(f"monsters.{mid}: chỉ recoil mới có recoil_dir / timer")


def _validate_quan(b, tuning):
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "stock" in b:
        # v1.2: mảng cá thể {id, kind, fresh}, gồm cả phần giữ chỗ -> cá thể nội bộ
        b["stock"] = parse_items(b["stock"], KINDS_P1, "quan.stock")
    for c in b.get("customers", []):
        r = c.get("reserved")
        if r is not None and not (isinstance(r, list) and all(isinstance(x, str) and x for x in r)):
            raise BadInput(f"customers.{c.get('id')}.reserved phải là mảng id cá thể (Contract v1.2)")
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    qb = tuning["quan"]["bounds"]
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    table_ids = [c.get("table_id") for c in b.get("customers", [])]
    known = {t["id"] for t in tuning["quan"]["tables"]} | {t.get("id") for t in b.get("tables", [])}
    for c in b.get("customers", []):
        if not isinstance(c.get("table_id"), str) or c["table_id"] not in known:
            raise BadInput(f"customers.{c['id']}: table_id phải là bàn có thật")
    if len(table_ids) != len(set(table_ids)):
        raise BadInput("hai khách cùng bàn")
