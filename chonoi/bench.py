"""Benchmark có render (Ticket-04 mục 1): python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

Cảnh đo: buổi sáng lõi (độ tươi, cá bơi, Cá Sấu, hiệu ứng mặc định), Út Sen đứng yên ở bến, cửa sổ 1280×720.
Cách đo: mở máy chủ `chonoi.live` (gather, seed) + Chrome/Chromium headless tải trang `?bench=1`; trang vẽ bằng
requestAnimationFrame như khi chơi, làm nóng 3 s rồi đo `--duration` s và gửi số khung, thời gian, 1% low về /bench.
  frames, measured_s : số khung hình / số giây thực trong khoảng đo sau làm nóng
  avg_fps            : frames / measured_s
  p1_low_fps         : nghịch đảo thời gian trung bình của max(1, ceil(0.01 × frames)) khung chậm nhất (giây)
  load_ms            : mili giây từ lúc lệnh khởi chạy tới khung hình đầu tiên của cảnh đo
Trình duyệt: biến môi trường CHROME, hoặc tự tìm Google Chrome / Chromium (macOS, Linux). Không có -> mã 1.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

START = time.time()  # mốc "khởi chạy" cho load_ms

from .contract import load_contract  # noqa: E402
from .live import LiveGame, LiveServer  # noqa: E402

WARMUP_S = 3
CANDIDATES = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


def find_browser():
    env = os.environ.get("CHROME")
    for c in ((env,) if env else ()) + CANDIDATES:
        path = c if os.path.isabs(c) else shutil.which(c)
        if path and os.path.exists(path):
            return path
    return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.bench")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.duration <= 0:
        sys.stderr.write("đầu vào sai: --duration phải > 0\n")
        return 2
    browser = find_browser()
    if browser is None:
        sys.stderr.write("lỗi chạy: không tìm thấy Chrome/Chromium (đặt biến CHROME=<đường dẫn>)\n")
        return 1
    game = LiveGame("gather", load_contract()["tuning"], {}, a.seed)  # Út Sen đứng yên ở bến (không input)
    server = LiveServer(game, port=0)
    server.start()
    profile = tempfile.mkdtemp(prefix="chonoi-bench-")
    url = f"http://127.0.0.1:{server.port}/?bench=1&warmup={WARMUP_S}&duration={a.duration:g}"
    proc = subprocess.Popen([browser, "--headless=new", "--disable-gpu-vsync", "--window-size=1280,720",
                             "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
                             "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                             "--disable-backgrounding-occluded-windows", f"--user-data-dir={profile}", url],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ok = game.bench_done.wait(timeout=WARMUP_S + a.duration + 60)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        server.stop()
        shutil.rmtree(profile, ignore_errors=True)
    if not ok:
        sys.stderr.write("lỗi chạy: trang không gửi kết quả đo (trình duyệt không vẽ?)\n")
        return 1
    b = game.bench
    out = {"avg_fps": round(b["frames"] / b["measured_s"], 2), "p1_low_fps": round(b["p1_low_fps"], 2),
           "frames": b["frames"], "measured_s": round(b["measured_s"], 3),
           "load_ms": int(round(b["first_frame_ms"] - START * 1000))}
    try:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(out, f)
            f.write("\n")
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
