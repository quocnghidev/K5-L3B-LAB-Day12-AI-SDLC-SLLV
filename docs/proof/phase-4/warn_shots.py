"""Chụp ba cảnh báo (thủy quái gần, oxy sắp hết, khách sắp giận) ở 1280×720, thường và tương phản cao.
Chạy: python3 docs/proof/phase-4/warn_shots.py docs/proof/phase-4   (cần Chrome; CHROME=<đường dẫn> nếu khác)"""
import subprocess, sys, time
sys.path.insert(0, ".")
from chonoi.bench import find_browser
from chonoi.contract import load_contract
from chonoi.items import new_item
from chonoi.live import LiveGame, LiveServer

out, CH, T = sys.argv[1], find_browser(), load_contract()["tuning"]


def shot(game, name, query):
    s = LiveServer(game, port=0); s.start(); time.sleep(0.4)
    subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1280,720",
                    "--virtual-time-budget=1200", f"--screenshot={out}/{name}.png",
                    f"http://127.0.0.1:{s.port}/{query}"], capture_output=True, timeout=60)
    s.stop()


gather = {"random_fish": False, "player": {"pos": [57, 22], "oxygen_ticks": 300},
          "hold": [new_item("I1", "ca_loc", 90), new_item("I2", "ca_linh", 28)]}
quan = {"stock": [new_item("I1", "bong_sung", 80), new_item("I2", "bong_sung", 70)], "random_customers": False,
        "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "patience_ticks_left": 700}]}
for hc, q in (("thuong", ""), ("tuong-phan-cao", "?contrast=1")):
    shot(LiveGame("gather", T, gather, 42), f"warn-gather-{hc}", q)
    shot(LiveGame("quan", T, quan, 42), f"warn-quan-{hc}", q)
