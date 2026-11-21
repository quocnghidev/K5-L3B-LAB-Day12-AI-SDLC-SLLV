"""Cuối ngày — Shop nâng cấp (TICKET-02 mục 2, 4.1–4.5).

Một bước trong Shop:
  1. Giảm time_left_ticks đi 1, tăng phase_tick thêm 1.
  2. Xử lý tối đa MỘT lệnh `buy` tại frame hiện tại (trước cạnh lên `shop_done`, kể cả bước cuối):
     - Nếu action không thuộc các nâng cấp đang bật -> `buy_failed` (reason: "unknown").
     - Nếu đã đạt cấp tối đa -> `buy_failed` (reason: "max_level").
     - Nếu money < price -> `buy_failed` (reason: "funds").
     - Nếu đủ tiền (money >= price): trừ money (giữ nguyên earned), tăng cấp trong `upgrades`,
       phát `bought` {upgrade, level, price, money}.
  3. Kiểm tra đóng Shop:
     - Nếu có cạnh lên `shop_done` -> kết thúc với `shop_end` {reason: "done"}.
     - Ngược lại, nếu time_left_ticks <= 0 -> kết thúc với `shop_end` {reason: "time"}.

Giao diện cho `day` (Lát 4b):
  - `ShopSim(tuning, stock=..., money=..., earned=..., reputation=..., upgrades=..., active_upgrades=...)`
  - `apply_active_upgrades(tuning, active_upgrades) -> dict` (trả về bản sao tuning đã áp cấp oxygen/hp cho Ngày kế)
  - `upgraded_gather_stats(tuning, active_upgrades) -> dict` (trả về {"oxygen_max_s": ..., "oxygen_max_ticks": ..., "hp_max": ...})
  - `validate_upgrades(tuning, upgrades) -> dict` (kiểm tra scenario.day.upgrades, sai -> BadInput mã 2)
"""

import copy

from ..errors import BadInput
from ..items import public_list

TICK = 60.0
CORE_UPGRADES = ("oxygen", "hp")
DEFAULT_SHOP_TUNING = {
    "max_ticks": 600,
    "upgrades": {
        "oxygen": [
            {"level": 1, "price": 200, "oxygen_max_s": 45},
            {"level": 2, "price": 400, "oxygen_max_s": 60},
        ],
        "hp": [
            {"level": 1, "price": 250, "hp_max": 4},
            {"level": 2, "price": 500, "hp_max": 5},
        ],
    },
}


def _shop_cfg(tuning: dict) -> dict:
    return tuning.get("shop", DEFAULT_SHOP_TUNING)


def validate_upgrades(tuning: dict, upgrades: dict, allowed_keys=CORE_UPGRADES) -> dict:
    """Kiểm tra map upgrades từ scenario.day.upgrades (BadInput -> mã 2)."""
    if not isinstance(upgrades, dict):
        raise BadInput("day.upgrades phải là object")
    shop_up = _shop_cfg(tuning).get("upgrades", {})
    out = {}
    for k, lvl in upgrades.items():
        if k not in allowed_keys or k not in shop_up:
            raise BadInput(f"nâng cấp không hợp lệ hoặc chưa bật: {k}")
        tiers = shop_up[k]
        max_lvl = max((int(t["level"]) for t in tiers), default=0)
        if isinstance(lvl, bool) or not isinstance(lvl, int) or not (0 <= lvl <= max_lvl):
            raise BadInput(f"cấp nâng cấp {k} phải là số nguyên trong [0, {max_lvl}]")
        if lvl > 0:
            out[k] = lvl
    return out


def upgraded_gather_stats(tuning: dict, active_upgrades: dict) -> dict:
    """Tính chỉ số gather (oxygen_max_s, oxygen_max_ticks, hp_max) theo active_upgrades."""
    g = tuning["gather"]
    shop_up = _shop_cfg(tuning).get("upgrades", {})
    oxy_s = g["oxygen_max_s"]
    hp_max = g["hp_max"]
    if active_upgrades:
        oxy_lvl = active_upgrades.get("oxygen", 0)
        if oxy_lvl > 0:
            tier = next((x for x in shop_up.get("oxygen", []) if x["level"] == oxy_lvl), None)
            if tier is not None:
                oxy_s = tier["oxygen_max_s"]
        hp_lvl = active_upgrades.get("hp", 0)
        if hp_lvl > 0:
            tier = next((x for x in shop_up.get("hp", []) if x["level"] == hp_lvl), None)
            if tier is not None:
                hp_max = tier["hp_max"]
    return {
        "oxygen_max_s": oxy_s,
        "oxygen_max_ticks": int(round(oxy_s * TICK)),
        "hp_max": int(hp_max),
    }


def apply_active_upgrades(tuning: dict, active_upgrades: dict) -> dict:
    """Trả về bản sao tuning với gather.oxygen_max_s và gather.hp_max đã áp theo active_upgrades.
    Gọi hàm này khi dựng GatherSim ở đầu mỗi Ngày mới.
    """
    t = copy.deepcopy(tuning)
    stats = upgraded_gather_stats(t, active_upgrades or {})
    t["gather"]["oxygen_max_s"] = stats["oxygen_max_s"]
    t["gather"]["hp_max"] = stats["hp_max"]
    return t


class ShopSim:
    mode = "shop"
    phase = "shop"

    def __init__(self, tuning, money=0, earned=0, reputation=None,
                 upgrades=None, stock=None, active_upgrades=None, allowed_upgrades=CORE_UPGRADES):
        shop_cfg = _shop_cfg(tuning)
        self.t = shop_cfg
        self.upgrades_cfg = shop_cfg["upgrades"]
        self.allowed_upgrades = set(allowed_upgrades)
        self.time_left_ticks = int(shop_cfg.get("max_ticks", 600))
        self.phase_tick = 0
        self.stock = [dict(it) for it in (stock or [])]  # list cá thể nội bộ, không hao tươi
        self.money = int(money)
        self.earned = int(earned)
        self.reputation = tuning["quan"]["reputation_initial"] if reputation is None else reputation
        self.upgrades = {k: int(v) for k, v in (upgrades or {}).items() if v > 0}
        self.active_upgrades = {k: int(v) for k, v in (active_upgrades or {}).items() if v > 0}
        self.done = False
        self.reason = None

    def snapshot(self) -> dict:
        return {
            "stock": public_list(self.stock),
            "upgrades": {k: self.upgrades[k] for k in sorted(self.upgrades) if self.upgrades[k] > 0},
        }

    def step(self, inp) -> list:
        events = []
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.phase_tick += 1

        buy_action = getattr(inp, "buy", None)
        if buy_action is None and isinstance(inp, dict):
            buy_action = inp.get("buy")
        if buy_action is not None:
            self._handle_buy(buy_action, events)

        shop_done = inp.pressed("shop_done") if hasattr(inp, "pressed") else bool(isinstance(inp, dict) and inp.get("shop_done"))
        if shop_done:
            self.done = True
            self.reason = "done"
            events.append(("shop_end", {"reason": "done"}))
        elif self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("shop_end", {"reason": "time"}))
        return events

    def _handle_buy(self, action: str, events: list):
        if not isinstance(action, str) or action not in self.allowed_upgrades or action not in self.upgrades_cfg:
            events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            return
        cur_lvl = self.upgrades.get(action, 0)
        tiers = self.upgrades_cfg[action]
        next_tier = next((t for t in tiers if t["level"] == cur_lvl + 1), None)
        if next_tier is None:
            events.append(("buy_failed", {"action": action, "reason": "max_level"}))
            return
        price = int(next_tier["price"])
        if self.money < price:
            events.append(("buy_failed", {"action": action, "reason": "funds"}))
            return
        self.money -= price
        self.upgrades[action] = int(next_tier["level"])
        events.append(("bought", {
            "upgrade": action,
            "level": int(next_tier["level"]),
            "price": price,
            "money": self.money,
        }))
