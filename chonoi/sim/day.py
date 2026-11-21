"""Vòng ngày (`--mode day`, Ticket-02 mục 2 + 4.5 "Đổi pha").

DayIntro → gather → quan → Shop → Ngày kế (hoặc kết thúc sau `days` Ngày).
  - Đầu Ngày (cùng tick): day_start → day_plan → phase_start(gather).
  - Sau gather_end (kể cả ngất): dựng quán với kho bàn giao trong bộ nhớ, phase_start(quan) cùng tick.
  - Sau quan_end: dựng Shop với kho dư, phase_start(shop) cùng tick.
  - Shop đóng (shop_end): days_completed += 1; đủ Ngày thì kết thúc `days_complete`, chưa thì dựng Ngày kế
    ngay tick đó và chỉ khi ấy mới sao cấp đã mua sang active_upgrades.
Pha mới chỉ chạy gameplay từ bước sau. Tiền, earned, uy tín, cấp giữ qua Ngày; oxy/Máu hồi đầy theo cấp
có hiệu lực; giỏ làm mới theo mẫu scenario.gather; kho dư bị bỏ sau Shop.

Shop do lát 4a viết (`chonoi/sim/shop.py`, giao diện ở docs/contracts/README.md mục 4); `shop_factory`
cho phép thay Shop khi test.
"""

import copy

from ..ids import IdAllocator
from .gather import GatherSim
from .quan import QuanSim


def default_shop_factory(*args, **kwargs):
    try:
        from .shop import ShopSim
    except ImportError as e:  # lát 4a chưa tích hợp
        raise RuntimeError("chưa có chonoi/sim/shop.py (lát 4a)") from e
    return ShopSim(*args, **kwargs)


def plan_for(tuning, day, overrides=None):
    """Kế hoạch của Ngày `day`: preset, hoặc mục `day.day_plan` của scenario (ingredients tính lại)."""
    plans = {p["day"]: p for p in tuning["day_plan"]}
    # v1.3 (soak): sau Ngày 5 kế hoạch D1–D5 lặp lại (Ngày 6 dùng D1, ...)
    p = (overrides or {}).get(day, plans[(day - 1) % len(plans) + 1])
    menu = tuning["menu"]
    ing = {}
    for dish, n in p["dishes"].items():
        for k, v in menu[dish]["recipe"].items():
            ing[k] = ing.get(k, 0) + v * n
    return {"dishes": dict(p["dishes"]), "ingredients": {k: ing[k] for k in sorted(ing)}}


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, days=1, shop_factory=None, creative=False):
        self.tuning = tuning
        self.streams = streams
        self.days = days
        self.creative = creative
        self.shop_factory = shop_factory or default_shop_factory
        self.tpl_gather = scenario.get("gather", {})
        self.tpl_quan = scenario.get("quan", {})
        d = scenario.get("day", {})
        self._money = d.get("money", 0)
        self._earned = d.get("earned", 0)
        self._reputation = d.get("reputation", tuning["quan"]["reputation_initial"])
        self.upgrades = dict(d.get("upgrades", {}))
        self.active_upgrades = {}
        self.plan_overrides = {p["day"]: p for p in d.get("day_plan", [])}
        self.day = 0
        self.days_completed = 0
        # v1.2: id cá thể I<n> tăng xuyên pha và Ngày (kể cả khi cá thể cũ đã dùng/bỏ)
        self.item_ids = IdAllocator()
        for it in self.tpl_gather.get("hold", []):
            self.item_ids.reserve(it["id"])
        self.cur = None
        self.phase = None
        self.phase_tick = 0
        self.plan = None
        self.done = False
        self.reason = None
        self.initial_events = []
        self._start_day(self.initial_events)

    # --- trạng thái xuyên pha (runner đọc) -------------------------------------------
    @property
    def money(self):
        return self.cur.money

    @property
    def earned(self):
        return self.cur.earned

    @property
    def reputation(self):
        return self.cur.reputation

    @property
    def time_left_ticks(self):
        return self.cur.time_left_ticks

    def snapshot(self) -> dict:
        s = {"day": self.day, "day_plan": self.plan, "upgrades": dict(self.upgrades),
             "active_upgrades": dict(self.active_upgrades)}
        s.update(self.cur.snapshot())
        return s

    # --- một bước ----------------------------------------------------------------------
    def step(self, inp):
        out = [(name, data, self.phase, self.day) for name, data in self.cur.step(inp)]
        self.phase_tick += 1
        if self.cur.done:
            self._next_phase(out)
        return out

    def _carry(self, sim):
        sim.money, sim.earned, sim.reputation = self._money, self._earned, self._reputation

    def _save(self):
        self._money, self._earned, self._reputation = self.cur.money, self.cur.earned, self.cur.reputation

    def _enter(self, phase, sim, out):
        self.cur, self.phase, self.phase_tick = sim, phase, 0
        out.append(("phase_start", {}, phase, self.day))

    def _start_day(self, out):
        self.day += 1
        self.active_upgrades = dict(self.upgrades)
        self.plan = plan_for(self.tuning, self.day, self.plan_overrides)
        out.append(("day_start", {}, "gather", self.day))
        out.append(("day_plan", copy.deepcopy(self.plan), "gather", self.day))
        tpl = copy.deepcopy(self.tpl_gather)
        if self.day > 1 and "hold" in tpl:  # Ngày kế: cấp id mới theo thứ tự mảng, giữ kind/fresh ban đầu
            tpl["hold"] = [dict(it, id=self.item_ids.new("I")) for it in tpl["hold"]]
        sim = GatherSim(self._tuning_for_day(), tpl, self.streams, IdAllocator(), day=self.day, item_ids=self.item_ids, creative=self.creative)
        self._carry(sim)
        self._enter("gather", sim, out)

    def _tuning_for_day(self):
        """Áp cấp nâng cấp đang có hiệu lực lên oxy tối đa / Máu tối đa."""
        t = copy.deepcopy(self.tuning)
        ups = self.tuning["shop"]["upgrades"]
        for key, field in (("oxygen", "oxygen_max_s"), ("hp", "hp_max")):
            level = self.active_upgrades.get(key, 0)
            for u in ups[key]:
                if u["level"] == level:
                    t["gather"][field] = u[field]
        if self.creative:
            from .shop import CREATIVE_ENERGY_TIERS
            en_lvl = self.active_upgrades.get("energy", 0)
            for u in ups.get("energy", CREATIVE_ENERGY_TIERS):
                if u["level"] == en_lvl:
                    t["gather"]["energy_max_s"] = u["energy_max_s"]
        return t

    def _next_phase(self, out):
        self._save()
        if self.phase == "gather":
            inv = self.cur.inventory_items()
            # lát 3: quán trong `day` lọc món theo kế hoạch; tiền/earned/uy tín xuyên Ngày
            sim = QuanSim(self.tuning, copy.deepcopy(self.tpl_quan), self.streams, IdAllocator(), inventory=inv,
                          plan_dishes=set(self.plan["dishes"]), money=self._money, earned=self._earned,
                          reputation=self._reputation)
            self._enter("quan", sim, out)
        elif self.phase == "quan":
            stock = [dict(it) for it in self.cur.stock]  # v1.2: cá thể dư (hàng thô ở Shop không hao)
            kw = {"creative": True} if self.creative else {}
            sim = self.shop_factory(self.tuning, self._money, self._earned, self._reputation,
                                    dict(self.upgrades), stock, **kw)
            self._enter("shop", sim, out)
        else:  # shop
            self.upgrades = dict(self.cur.upgrades)
            self.days_completed += 1
            if self.days_completed >= self.days:
                self.done = True
                self.reason = "days_complete"
            else:
                self._start_day(out)
