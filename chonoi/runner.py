"""Vòng tick (Contract B, mô hình tick).

Thứ tự ghi: event khởi tạo (chỉ `day`) -> snapshot tick 0 -> với mỗi bước: sự kiện (theo thứ tự xử lý) rồi
snapshot (nếu tới lượt hoặc buổi kết thúc) -> dòng 'end'. Mỗi tick tối đa một snapshot.

Pause (v1.1, mọi mode): xét cạnh `pause` trước. Bước vào pause chỉ tăng `tick` ngoài và phát `paused`;
khi còn pause, bỏ qua mọi hành động, `sim_tick`, `phase_tick`, lịch và timer đứng yên. Cạnh lên tiếp theo
phát `resumed` rồi chạy gameplay ngay trong bước đó.

`Session` là API bước tick gọn dùng chung cho headless (`run`) và cửa sổ chơi trực tiếp (`chonoi.live`):
cả hai chạy CÙNG một lớp sim, không nhân đôi logic.
"""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory, days=1, shop_factory=None, creative=False):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids, creative=creative)
    if mode == "day":
        return DaySim(tuning, scenario, streams, days=days, shop_factory=shop_factory, creative=creative)
    return QuanSim(tuning, scenario, streams, ids, inventory=inventory)


class Session:
    """Một lượt chơi: dựng sim, bước từng tick, lấy snapshot / dòng end."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1, shop_factory=None, creative=False):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days, shop_factory, creative=creative)
        self.tick = 0
        self.sim_tick = 0
        self.paused = False

    @property
    def done(self) -> bool:
        return self.sim.done

    @property
    def phase(self):
        return self.sim.phase

    @property
    def phase_tick(self):
        return getattr(self.sim, "phase_tick", self.sim_tick)

    def _score(self):
        return self.sim.earned + self.tuning["score"]["reputation_multiplier"] * math.floor(self.sim.reputation)

    def _row(self, name, data, phase=None, day=None):
        row = {"type": "event", "tick": self.tick, "phase": phase or self.phase}
        if self.mode == "day":
            row["day"] = day if day is not None else self.sim.day
        row["name"] = name
        row["data"] = data
        return row

    def initial_events(self) -> list:
        """Event phát lúc dựng lượt (tick 0), ghi trước snapshot tick 0."""
        return [self._row(*e) for e in getattr(self.sim, "initial_events", [])]

    def snapshot(self) -> dict:
        sim = self.sim
        state = "finished" if sim.done else ("paused" if self.paused else "playing")
        s = {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick, "mode": self.mode,
            "phase": self.phase, "phase_tick": self.phase_tick, "state": state,
            "time_left_ticks": sim.time_left_ticks, "money": sim.money, "earned": sim.earned,
            "reputation": sim.reputation, "score": self._score(),
        }
        s.update(sim.snapshot())
        return s

    def step(self, inp) -> list:
        """Chạy một bước với `inp` (chonoi.inputs.InputState); trả các dòng event (tick = k + 1)."""
        rows = []
        if inp.pressed("pause"):
            self.paused = not self.paused
            if self.paused:
                self.tick += 1
                return [self._row("paused", {})]
            self.tick += 1
            rows.append(self._row("resumed", {}))
        elif self.paused:
            self.tick += 1
            return rows
        else:
            self.tick += 1
        events = self.sim.step(inp)
        self.sim_tick += 1
        rows.extend(self._row(*e) for e in events)
        return rows

    def end_row(self) -> dict:
        sim = self.sim
        row = {"type": "end", "ticks": self.tick, "sim_tick": self.sim_tick, "mode": self.mode,
               "state": "finished" if sim.done else ("paused" if self.paused else "playing"),
               "reason": sim.reason if sim.done else "tick_limit",
               "money": sim.money, "earned": sim.earned, "reputation": sim.reputation, "score": self._score()}
        if self.mode == "day":
            row["days_completed"] = sim.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every, inventory=None, inventory_out=None,
        days=1, shop_factory=None):
    sess = Session(mode, tuning, scenario, seed, inventory, days, shop_factory)
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    try:
        for row in sess.initial_events():
            w.write(row)
        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            if sess.tick % snapshot_every == 0 or sess.done:
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    finally:
        w.close()
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
