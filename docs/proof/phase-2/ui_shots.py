import json, subprocess, sys, time, urllib.request
sys.path.insert(0, ".")
from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
out = sys.argv[1]
tuning = load_contract()["tuning"]
sc = {"gather": {"hold": ["ca_loc", "bong_sung", "ca_linh"], "player": {"pos": [58, 18]}}}
game = LiveGame("day", tuning, sc, 3, days=2)
srv = LiveServer(game, port=0); srv.start()
base = f"http://127.0.0.1:{srv.port}"
def post(path, obj):
    urllib.request.urlopen(urllib.request.Request(base + path, data=json.dumps(obj).encode(), method="POST"), timeout=5).read()
def shot(name):
    subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1280,720",
                    "--virtual-time-budget=1500", f"--screenshot={out}/{name}.png", base + "/"], capture_output=True, timeout=60)
shot("1-menu")
post("/control", {"intro": "day"}); shot("2-dayintro")
post("/control", {"hold": False}); time.sleep(1.0); shot("3-gather")
# nhảy tới quán: ép cập bến bằng cách đặt vị trí? dùng phím: không có -> đợi qua sim trực tiếp
with game._lock:
    sim = game.session.sim.cur; sim.pos = [2.0, 0.0]
post("/input", {"interact": True}); time.sleep(0.2); post("/input", {"interact": False}); time.sleep(0.2)
shot("4-evening")
post("/control", {"hold": False}); time.sleep(3.0); shot("5-quan")
with game._lock:
    game.session.sim.cur.time_left_ticks = 2
time.sleep(0.3); shot("6-result")
post("/control", {"hold": False}); time.sleep(0.2); shot("7-shop")
post("/input", {"pause": True}); time.sleep(0.2); shot("8-pause")
srv.stop()
