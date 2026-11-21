import subprocess, sys, time
sys.path.insert(0, ".")
from chonoi.contract import load_contract
from chonoi.items import new_item
from chonoi.live import LiveGame, LiveServer
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
stock = [new_item("I1", "ca_loc", 92), new_item("I2", "ca_loc", 40), new_item("I3", "bong_sung", 29),
         new_item("I4", "bong_sung", 75), new_item("I5", "bong_sung", 60)]
g = LiveGame("quan", load_contract()["tuning"], {"stock": stock, "player": {"pos": [9, 4]},
             "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung"}]}, 1)
s = LiveServer(g, port=0); s.start(); time.sleep(0.3)
subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1280,720", "--virtual-time-budget=1500",
                f"--screenshot={sys.argv[1]}", f"http://127.0.0.1:{s.port}/"], capture_output=True, timeout=60)
s.stop()
