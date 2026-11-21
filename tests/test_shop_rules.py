"""Test Lát 4a: Module Shop (TICKET-02 mục 2, 4.1–4.5)."""

import json
import unittest

from chonoi.errors import BadInput
from chonoi.inputs import InputPlayer
from chonoi.items import new_item
from chonoi.sim.shop import ShopSim, apply_active_upgrades, upgraded_gather_stats, validate_upgrades

with open("game.contract.json", encoding="utf-8") as _f:
    CONTRACT = json.load(_f)
TUNING = CONTRACT["tuning"]


def run_shop(shop, frames_list, ticks=None):
    ip = InputPlayer(frames_list)
    events = []
    limit = ticks if ticks is not None else TUNING["shop"]["max_ticks"]
    for t in range(limit):
        if shop.done:
            break
        inp = ip.advance(t)
        for name, data in shop.step(inp):
            events.append((t + 1, name, data))
    return events


class ShopUpgrades(unittest.TestCase):
    def test_buy_oxygen_and_hp_sequentially_and_keep_earned(self):
        shop = ShopSim(TUNING, money=1000, earned=1200, reputation=3.5, upgrades={},
                       stock=[new_item("I1", "ca_loc", 80)])
        evs = run_shop(shop, [
            {"tick": 0, "buy": "oxygen"},   # 200 -> còn 800, level 1
            {"tick": 1, "buy": "hp"},       # 250 -> còn 550, level 1
            {"tick": 2, "buy": "oxygen"},   # 400 -> còn 150, level 2
            {"tick": 3, "shop_done": True},
        ])
        self.assertEqual(evs, [
            (1, "bought", {"upgrade": "oxygen", "level": 1, "price": 200, "money": 800}),
            (2, "bought", {"upgrade": "hp", "level": 1, "price": 250, "money": 550}),
            (3, "bought", {"upgrade": "oxygen", "level": 2, "price": 400, "money": 150}),
            (4, "shop_end", {"reason": "done"}),
        ])
        self.assertEqual(shop.money, 150)
        self.assertEqual(shop.earned, 1200)
        self.assertEqual(shop.upgrades, {"oxygen": 2, "hp": 1})
        self.assertEqual(shop.snapshot(), {
            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 80.0}],
            "upgrades": {"oxygen": 2, "hp": 1},
        })

    def test_shop_stock_does_not_decay(self):
        shop = ShopSim(TUNING, money=0, earned=0, reputation=3.0, upgrades={},
                       stock=[new_item("I1", "ca_loc", 30)])
        run_shop(shop, [], ticks=600)
        self.assertEqual(shop.snapshot()["stock"], [{"id": "I1", "kind": "ca_loc", "fresh": 30.0}])

    def test_exact_money_allows_purchase(self):
        shop = ShopSim(TUNING, money=200, earned=200, reputation=3.0, upgrades={}, stock={})
        evs = run_shop(shop, [{"tick": 0, "buy": "oxygen"}, {"tick": 1, "shop_done": True}])
        self.assertEqual(evs[0], (1, "bought", {"upgrade": "oxygen", "level": 1, "price": 200, "money": 0}))
        self.assertEqual(shop.money, 0)
        self.assertEqual(shop.earned, 200)

    def test_buy_failed_funds_max_level_and_unknown(self):
        shop = ShopSim(TUNING, money=100, earned=500, reputation=3.0, upgrades={"oxygen": 2}, stock={})
        evs = run_shop(shop, [
            {"tick": 0, "buy": "hp"},       # thiếu tiền (cần 250)
            {"tick": 1, "buy": "oxygen"},   # đã max_level (2)
            {"tick": 2, "buy": "weapon"},   # mở rộng chưa bật -> unknown
            {"tick": 3, "buy": "invalid"},  # không tồn tại -> unknown
            {"tick": 4, "shop_done": True},
        ])
        self.assertEqual(evs[:4], [
            (1, "buy_failed", {"action": "hp", "reason": "funds"}),
            (2, "buy_failed", {"action": "oxygen", "reason": "max_level"}),
            (3, "buy_failed", {"action": "weapon", "reason": "unknown"}),
            (4, "buy_failed", {"action": "invalid", "reason": "unknown"}),
        ])
        self.assertEqual(shop.money, 100)
        self.assertEqual(shop.upgrades, {"oxygen": 2})

    def test_auto_close_after_600_ticks(self):
        shop = ShopSim(TUNING, money=0, earned=0, reputation=3.0, upgrades={}, stock={})
        evs = run_shop(shop, [], ticks=700)
        self.assertEqual(evs, [(600, "shop_end", {"reason": "time"})])
        self.assertTrue(shop.done)
        self.assertEqual(shop.reason, "time")
        self.assertEqual(shop.time_left_ticks, 0)

    def test_buy_processed_before_shop_done_even_on_last_tick(self):
        shop = ShopSim(TUNING, money=250, earned=250, reputation=3.0, upgrades={}, stock={})
        evs = run_shop(shop, [{"tick": 599, "buy": "hp", "shop_done": True}], ticks=600)
        self.assertEqual(evs, [
            (600, "bought", {"upgrade": "hp", "level": 1, "price": 250, "money": 0}),
            (600, "shop_end", {"reason": "done"}),
        ])
        self.assertEqual(shop.reason, "done")
        self.assertEqual(shop.upgrades, {"hp": 1})

    def test_upgrades_apply_to_next_day_only_via_helper(self):
        shop = ShopSim(TUNING, money=750, earned=750, reputation=3.0, upgrades={}, stock={})
        run_shop(shop, [
            {"tick": 0, "buy": "oxygen"},
            {"tick": 1, "buy": "hp"},
            {"tick": 2, "shop_done": True},
        ])
        # Trong lúc shop mở, active_upgrades vẫn là {} (chưa có hiệu lực ở ngày hiện tại)
        self.assertEqual(shop.active_upgrades, {})
        self.assertEqual(upgraded_gather_stats(TUNING, shop.active_upgrades),
                         {"oxygen_max_s": 30, "oxygen_max_ticks": 1800, "hp_max": 3})

        # Sang Ngày kế, day sao shop.upgrades -> active_upgrades và gọi apply_active_upgrades
        next_tuning = apply_active_upgrades(TUNING, shop.upgrades)
        self.assertEqual(next_tuning["gather"]["oxygen_max_s"], 45)
        self.assertEqual(next_tuning["gather"]["hp_max"], 4)
        # Không làm biến đổi TUNING gốc
        self.assertEqual(TUNING["gather"]["oxygen_max_s"], 30)
        self.assertEqual(TUNING["gather"]["hp_max"], 3)

    def test_validate_upgrades(self):
        self.assertEqual(validate_upgrades(TUNING, {"oxygen": 2, "hp": 0}), {"oxygen": 2})
        for bad in ({"oxygen": 3}, {"hp": -1}, {"weapon": 1}, {"oxygen": True}):
            with self.assertRaises(BadInput):
                validate_upgrades(TUNING, bad)


if __name__ == "__main__":
    unittest.main()
