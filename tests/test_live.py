"""Test cửa sổ chơi trực tiếp (chonoi.live). Chỉ dành cho starter Python: nhóm đổi ngôn ngữ thì xóa file này."""

import json
import time
import unittest
import urllib.error
import urllib.request

from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read()


def _post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        e.close()
        return e.code


class LiveServerTest(unittest.TestCase):
    def test_state_input_and_clean_stop(self):
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("gather", tuning, {}, 1), port=0)  # cổng ngẫu nhiên
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            code, body = _get(base + "/state")
            self.assertEqual(code, 200)
            st = json.loads(body)
            self.assertIn("tick", st)
            self.assertEqual(st["mode"], "gather")
            self.assertEqual(st["player"]["pos"], [2, 0])
            self.assertEqual(_post(base + "/input", {"move": [1, 0], "interact": False, "catch": False}), 200)
            self.assertEqual(_post(base + "/input", {"move": [5, 0]}), 400)
            code, html = _get(base + "/")
            self.assertEqual(code, 200)
            self.assertIn(b"<canvas", html)
            deadline = time.time() + 3
            while time.time() < deadline:
                st2 = json.loads(_get(base + "/state")[1])
                if st2["tick"] > st["tick"] + 3 and st2["player"]["pos"][0] > st["player"]["pos"][0]:
                    break
                time.sleep(0.05)
            self.assertGreater(st2["tick"], st["tick"], "mô phỏng phải chạy nền")
            self.assertGreater(st2["player"]["pos"][0], st["player"]["pos"][0], "input phải tác động tới sim")
        finally:
            server.stop()
        self.assertFalse(server.game._thread.is_alive())
        self.assertFalse(server._thread.is_alive())


class LiveDayTest(unittest.TestCase):
    """Chế độ day: giữ ở menu, DayIntro, thả, pause, buy, Thoát (Ticket-02 mục 2 "Menu, pause và HUD")."""

    def wait(self, base, cond, timeout=3):
        deadline = time.time() + timeout
        while time.time() < deadline:
            st = json.loads(_get(base + "/state")[1])
            if cond(st):
                return st
            time.sleep(0.03)
        self.fail("hết giờ chờ trạng thái")

    def test_menu_intro_pause_and_quit(self):
        tuning = load_contract()["tuning"]
        game = LiveGame("day", tuning, {}, 1, days=2)
        server = LiveServer(game, port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            st = json.loads(_get(base + "/state")[1])
            self.assertEqual((st["mode"], st["ui_hold"], st["intro"], st["day"]), ("day", True, "menu", 1))
            time.sleep(0.1)
            self.assertEqual(json.loads(_get(base + "/state")[1])["tick"], 0, "menu: mô phỏng đứng yên")
            self.assertIn("ingredients", st["day_plan"])
            self.assertEqual(_post(base + "/control", {"intro": "day"}), 200)
            self.assertEqual(json.loads(_get(base + "/state")[1])["intro"], "day")
            self.assertEqual(_post(base + "/control", {"hold": False}), 200)
            st = self.wait(base, lambda s: s["tick"] > 3)
            self.assertIsNone(st["intro"])
            self.assertEqual(_post(base + "/input", {"pause": True}), 200)
            st = self.wait(base, lambda s: s["state"] == "paused")
            t = st["sim_tick"]
            time.sleep(0.1)
            self.assertEqual(json.loads(_get(base + "/state")[1])["sim_tick"], t, "pause: sim_tick đứng yên")
            self.assertEqual(_post(base + "/input", {"pause": False, "buy": "oxygen"}), 200)
            self.assertEqual(_post(base + "/input", {"buy": ""}), 400)
            self.assertEqual(_post(base + "/control", {"hold": "x"}), 400)
            self.assertEqual(_post(base + "/control", {"menu": True}), 200)
            st = json.loads(_get(base + "/state")[1])
            self.assertEqual((st["tick"], st["intro"]), (0, "menu"))
            self.assertEqual(_post(base + "/quit", {}), 200)
            self.assertTrue(game.quit_requested.is_set())
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
