"""Cửa sổ chơi trực tiếp bằng TRÌNH DUYỆT, chỉ dùng thư viện chuẩn Python.

    python3 -m chonoi.live --mode gather|quan|day [--days N] [--seed N] [--port 8000]

Máy chủ HTTP nhỏ (ThreadingHTTPServer) phục vụ `chonoi/web/index.html` và các API:
    GET  /state   -> snapshot JSON hiện tại (cùng trường như dòng snapshot của headless) + `meta` + `events`
                     + `ui_hold`/`intro` (màn hình chờ của UI) + `stats`/`totals` (số liệu cho DayResult/Summary)
    POST /input   -> {"move": [a, b], "interact", "catch", "pause", "shop_done": bool, "buy": "oxygen"|"hp"}
    POST /control -> {"hold": bool} giữ/thả mô phỏng khi UI đang ở màn hình giới thiệu; {"menu": true} về menu
    POST /restart -> chơi lại từ đầu (cùng seed, cùng scenario)
    POST /quit    -> tắt máy chủ (nút Thoát của menu chính)

Chế độ `day`: máy chủ tự GIỮ mô phỏng ở menu chính và mỗi khi đổi pha (DayIntro / EveningIntro / DayResult),
client thả bằng /control. Giữ là chuyện của cửa sổ chơi (không bước, không đổi tick); headless không có màn này.

Mô phỏng chạy 60 tick/s trong một luồng nền, dùng CÙNG lớp sim như headless (qua `runner.Session`).
Client chỉ ĐỌC snapshot và tự bỏ qua trường chưa có, nên luật do nhóm viết thêm trường nào cũng không vỡ.
Ngẫu nhiên vẫn đi qua `Streams` (seed); chỉ nhịp chạy theo đồng hồ thật, không đi vào luật.
"""

import argparse
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contract import load_contract
from .errors import BadInput
from .inputs import LiveInputs
from .inventory import read_inventory
from .runner import Session
from .scenario import load_scenario

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
TICK_S = 1.0 / 60.0
MAX_BODY = 4096
RECENT_EVENTS = 40


class LiveGame:
    """Một lượt chơi + luồng nền bước 60 tick/s. Mọi truy cập trạng thái đi qua khóa."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, inventory_out=None, days=1):
        self._args = (mode, tuning, scenario, seed, inventory, days)
        self.mode = mode
        self.tuning = tuning
        self.inventory_out = inventory_out
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.quit_requested = threading.Event()
        self._thread = None
        self._reset()

    def _reset(self):
        self.session = Session(*self._args)
        self.inputs = LiveInputs()
        self.events = []
        self._saved = False
        self.error = None
        # màn hình chờ của UI (chỉ chế độ day): menu chính trước khi chơi
        self.hold = self.mode == "day"
        self.intro = "menu" if self.hold else None
        self.stats = None
        self.totals = {"served": 0, "left": 0, "tips": 0, "sold": {}}
        if self.mode == "day":
            self._new_day_stats()

    def _new_day_stats(self):
        sim = self.session.sim
        self.stats = {"day": getattr(sim, "day", None), "served": 0, "left": 0, "tips": 0,
                      "earned_start": sim.earned, "reputation_start": sim.reputation}

    def _track(self, row):
        """Gom số liệu Ngày cho DayResult/Summary từ event; tự giữ mô phỏng khi đổi pha (day)."""
        name, data = row["name"], row["data"]
        if self.mode != "day":
            return
        if name == "day_start":
            self._new_day_stats()
        elif name == "served":
            self.stats["served"] += 1
            self.totals["served"] += 1
            sold = self.totals["sold"]
            sold[data["dish_id"]] = sold.get(data["dish_id"], 0) + 1
        elif name == "customer_left" and data.get("reason") == "patience":
            self.stats["left"] += 1
            self.totals["left"] += 1
        elif name == "paid":
            self.stats["tips"] += data.get("tip", 0)
            self.totals["tips"] += data.get("tip", 0)
        elif name == "phase_start":
            self.intro = {"gather": "day", "quan": "evening", "shop": "result"}.get(row["phase"])
            self.hold = True

    # --- luồng nền ----------------------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._loop, name="chonoi-sim", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        nxt = time.perf_counter()
        while not self._stop.is_set():
            nxt += TICK_S
            with self._lock:
                try:
                    self._tick_once()
                except Exception:  # luật của nhóm lỗi: báo ra terminal + client, dừng bước (restart để chơi lại)
                    self.error = traceback.format_exc()
                    sys.stderr.write(self.error)
                    self.session.sim.done = True
                    self.session.sim.reason = "error"
            delay = nxt - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            elif delay < -0.25:  # chạy chậm quá thì bỏ bù, tránh chạy dồn
                nxt = time.perf_counter()

    def _tick_once(self):
        s = self.session
        if s.done or self.hold:
            return
        for row in s.step(self.inputs.advance()):
            self.events.append(row)
            self._track(row)
        del self.events[:-RECENT_EVENTS]
        if s.done and not self._saved:
            self._saved = True
            if self.inventory_out:
                try:
                    s.write_inventory_if_done(self.inventory_out)
                except OSError as e:
                    sys.stderr.write(f"lỗi ghi kho: {e}\n")

    # --- API cho handler -----------------------------------------------------------
    def state_json(self) -> bytes:
        with self._lock:
            snap = self.session.snapshot()
            meta = dict(self.tuning.get(self.session.phase, {}))
            meta.update(menu=self.tuning["menu"], shop=self.tuning["shop"])
            if self.mode == "day":
                meta.update(gather=self.tuning["gather"], quan=self.tuning["quan"], days=self.session.sim.days)
            snap["meta"] = meta
            snap["events"] = list(self.events)
            snap["ui_hold"] = self.hold  # khác `hold` (giỏ) của snapshot gather
            snap["intro"] = self.intro if self.hold else None
            snap["stats"] = self.stats
            snap["totals"] = self.totals
            snap["finished"] = self.session.done
            snap["reason"] = self.session.sim.reason if self.session.done else None
            snap["error"] = self.error
            return json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def set_input(self, body: dict):
        move = body.get("move")
        if move is not None:
            ok = (isinstance(move, list) and len(move) == 2 and
                  all(isinstance(c, (int, float)) and not isinstance(c, bool) and abs(c) <= 1 for c in move))
            if not ok:
                raise ValueError("move phải là [a, b] trong [-1, 1]")
        buttons = {}
        for b in ("interact", "catch", "pause", "shop_done"):
            if b in body:
                if not isinstance(body[b], bool):
                    raise ValueError(f"{b} phải là boolean")
                buttons[b] = body[b]
        buy = body.get("buy")
        if buy is not None and (not isinstance(buy, str) or not buy or len(buy) > 40):
            raise ValueError("buy phải là chuỗi khác rỗng")
        with self._lock:
            self.inputs.set(move, buy=buy, **buttons)

    def control(self, body: dict):
        with self._lock:
            if body.get("menu"):
                self._reset()
                return
            if "intro" in body:  # menu chính -> DayIntro (vẫn giữ)
                if body["intro"] not in ("day",):
                    raise ValueError("intro không hợp lệ")
                self.intro = body["intro"]
                return
            if "hold" in body:
                if not isinstance(body["hold"], bool):
                    raise ValueError("hold phải là boolean")
                self.hold = body["hold"]
                if not self.hold:
                    self.intro = None
                    self.inputs = LiveInputs()  # phím giữ qua màn hình chờ không tạo cạnh mới

    def restart(self):
        with self._lock:
            self._reset()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    game: LiveGame = None  # gán trên lớp con trong make_server

    def log_message(self, fmt, *args):  # yên lặng
        pass

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/state":
            self._send(200, self.game.state_json())
        elif path in ("/", "/index.html"):
            try:
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, b'{"error":"thieu index.html"}')
        else:
            self._send(404, b'{"error":"khong co"}')

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self._send(400, b'{"error":"body sai"}')
            return
        raw = self.rfile.read(n) if n else b""
        try:
            if path == "/input":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.set_input(body)
            elif path == "/control":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.control(body)
            elif path == "/restart":
                self.game.restart()
            elif path == "/quit":
                self.game.quit_requested.set()
            else:
                self._send(404, b'{"error":"khong co"}')
                return
        except (ValueError, UnicodeDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode("utf-8"))
            return
        self._send(200, b'{"ok":true}')


class LiveServer:
    """Máy chủ + mô phỏng. port=0 -> cổng ngẫu nhiên (đọc `.port`)."""

    def __init__(self, game: LiveGame, host="127.0.0.1", port=8000):
        handler = type("Handler", (_Handler,), {"game": game})
        self.game = game
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self.httpd.daemon_threads = True
        self.host = host
        self.port = self.httpd.server_address[1]
        self._thread = None

    @property
    def url(self):
        return f"http://{self.host}:{self.port}/"

    def start(self):
        self.game.start()
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="chonoi-http", daemon=True)
        self._thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self.game.stop()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.live", description="Chơi trực tiếp trên trình duyệt (starter).")
    p.add_argument("--mode", required=True, choices=["gather", "quan", "day"])
    p.add_argument("--days", type=int, default=1, help="chỉ với day: số Ngày (1..5)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--port", type=int, default=8000, help="0 = cổng ngẫu nhiên")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--scenario")
    p.add_argument("--inventory", help="chỉ với quan: nạp kho từ file")
    p.add_argument("--inventory-out", dest="inventory_out", help="chỉ với gather: ghi kho khi kết thúc buổi")
    a = p.parse_args(argv)
    try:
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        if not (1 <= a.days <= 5):
            raise BadInput("--days phải từ 1 đến 5")
        tuning = load_contract()["tuning"]
        scenario = load_scenario(a.scenario, a.mode, tuning)
        inventory = read_inventory(a.inventory) if a.inventory else None
        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
        game = LiveGame(a.mode, tuning, scenario, a.seed, inventory, a.inventory_out, days=a.days)
        server = LiveServer(game, a.host, a.port)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"không mở được cổng {a.port}: {e}\n")
        return 1
    server.start()
    print(f"Mở trình duyệt tại {server.url}  (chế độ {a.mode}, seed {a.seed}). Ctrl+C để dừng.", flush=True)
    try:
        while not game.quit_requested.is_set():
            time.sleep(0.2)
        print("Đã thoát (nút Thoát).", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
