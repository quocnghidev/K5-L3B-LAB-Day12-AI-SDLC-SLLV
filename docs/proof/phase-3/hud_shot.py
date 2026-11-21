import json, subprocess, sys, time
sys.path.insert(0, ".")
from chonoi.contract import load_contract
from chonoi.items import new_item
from chonoi.live import LiveGame, LiveServer
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
out = sys.argv[1]
hold = [new_item("I1", "ca_loc", 95), new_item("I2", "bong_sung", 45), new_item("I3", "ca_linh", 29), new_item("I4", "keo_neo", 100)]
g = LiveGame("gather", load_contract()["tuning"], {"hold": hold, "random_fish": False, "player": {"pos": [30, 5]}}, 1)
s = LiveServer(g, port=0); s.start(); time.sleep(0.3)
subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1280,720", "--virtual-time-budget=1500",
                f"--screenshot={out}/p3-hud-gather.png", f"http://127.0.0.1:{s.port}/"], capture_output=True, timeout=60)
s.stop()
