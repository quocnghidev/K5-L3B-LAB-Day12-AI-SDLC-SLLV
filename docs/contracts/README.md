# Hợp đồng tích hợp — nhóm SLLV (Test Contract v1.2)

Đổi hợp đồng: báo người kia trước, ghi lý do trong commit. Số liệu chỉ nằm trong `game.contract.json`.

## 1. Kho cá thể (v1.2, Ticket-03 — ADR 0001)
- File / event / snapshot: `{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]}`, kho rỗng `{"items": []}`,
  sắp theo id. Kind: `ca_loc`, `ca_linh`, `ca_keo`, `bong_dien_dien`, `bong_sung`, `keo_neo`. Kho đếm v1.1 → mã 2.
- **Bên trong sim** (`chonoi/items.py`): cá thể `{"id", "kind", "units"}`, `units = fresh × 240` (số nguyên).
  Hao: `decay(items, units_per_tick(fr["quan_decay_per_s"]), fr, "stock", events)` trả id vừa ươn; `spoiled(it, fr)`
  = `units < 30 × 240`; xuất bằng `public()` / `public_list()`. `fr = tuning["freshness"]`.
- `read_inventory()` trả list cá thể nội bộ; scenario đã đổi `gather.hold`, `quan.stock` sang list cá thể nội bộ;
  `customers[].reserved` là list id (chuỗi) — quán kiểm id có trong kho, chưa ươn, đủ công thức, không dùng chung.
- Gather ghi đúng một lần khi `gather_end` (ngất ghi rỗng). Trong `day` bàn giao trong bộ nhớ, cùng tick, không hao thêm.

## 2. Dữ liệu v1.1 đã có trong `game.contract.json`
| Khóa | Dùng ở | Người đọc |
|---|---|---|
| `quan.stoves` (B1, B2), `quan.tables` (T1–T4), `menu` (6 món) | quán | An (lát 3) |
| `day_plan[]` `{day, dishes, ingredients}` (D1–D5, `ingredients` = tổng công thức × suất) | quán trong `day`, HUD | An (lát 3), Nghị (lát 4b) |
| `shop.max_ticks`, `shop.upgrades.oxygen[] {level,price,oxygen_max_s}`, `shop.upgrades.hp[] {level,price,hp_max}` | Shop | An (lát 4a) |
| `gather.nodes` N5/N6 `keo_neo`, `fish_yield.ca_keo`, `fish_*`, `gather.monsters` | gather | Nghị (lát 1, 2) |

`gather.fish_initial` = 8 (số đàn đầu ca, sinh ở điểm chuẩn theo seed). Snapshot gather có `fish[].age_ticks`, `monsters[]`.

## 3. Inputs
- Nút boolean (cạnh lên): `interact`, `catch`, `pause` (mọi mode), `shop_done` (v1.1). Pause xử lý ở `runner.Session`, sim không cần biết.
- `buy`: chuỗi khác rỗng, chỉ có ở đúng frame khai báo → `InputState.buy` (None ở frame khác).

## 4. Giao diện Shop (An viết, Nghị gọi từ `day`)
File `chonoi/sim/shop.py`:
```python
class ShopSim:
    mode = phase = "shop"
    def __init__(self, tuning, money, earned, reputation, upgrades, stock): ...
        # upgrades: {"oxygen": cấp đã mua, "hp": cấp đã mua} (cấp vắng = 0)
        # stock (v1.2): list cá thể nội bộ {id, kind, units} dư từ ca tối; snapshot xuất public_list(); không hao
    def step(self, inp) -> list[tuple[str, dict]]: ...
        # một buy (inp.buy) trước cạnh shop_done; event bought / buy_failed / shop_end
    def snapshot(self) -> dict: ...   # stock, upgrades
    # thuộc tính runner đọc: money, earned, reputation, time_left_ticks, done, reason, upgrades
```
`day` (`chonoi/sim/day.py`) gọi `ShopSim(tuning, money, earned, reputation, upgrades, stock)` khi `quan_end`,
đọc lại `money, earned, reputation, upgrades` khi `done`, rồi sao `upgrades` sang `active_upgrades` lúc dựng Ngày mới.
Event Shop trả dạng `(name, data)` như gather/quan; `day` tự gắn `phase`/`day`.

## 4b. Quán trong `day` (An, lát 3)
`day` dựng `QuanSim(tuning, tpl_quan, streams, ids, inventory=list cá thể nội bộ (v1.2), plan_dishes=set(món kế hoạch),
money=..., earned=..., reputation=...)`. Quán chạy riêng không truyền `plan_dishes` (= cả 6 món). Quán lọc món theo
`plan_dishes` trước khi lọc nguyên liệu khả dụng, và kiểm khách fixture gọi món ngoài kế hoạch → mã 2.
v1.2: `self.stock` là list cá thể nội bộ; `day` đọc lại `self.stock` khi `quan_end` để đưa sang Shop.

## 4c. Cửa sổ chơi (`chonoi/live.py`)
`GET /state` = snapshot + `meta`, `events`, `ui_hold`/`intro` (màn hình chờ: `menu`, `day`, `evening`, `result`),
`stats`/`totals` (DayResult, Summary). `POST /input` nhận thêm `pause`, `shop_done`, `buy`; `POST /control`
`{"hold": false}` / `{"intro": "day"}` / `{"menu": true}`; `POST /quit`. `ui_hold` chỉ là màn hình chờ của UI,
headless không có.

## 5. Sự kiện
| Sự kiện | `data` | Phát ở |
|---|---|---|
| `gather`, `node_regrown`, `hold_full`, `fish_caught`, `dive`, `surface`, `oxygen_empty`, `choke`, `faint`, `gather_end` | theo PRD-0 mục E | gather |
| `customer_arrived`, `no_dish`, `cook_started`, `dish_ready`, `dish_picked`, `served`, `paid`, `customer_left`, `quan_end` | theo PRD-0 mục E | quan |
| `bought` `{upgrade,level,price,money}`, `buy_failed` `{action,reason}`, `shop_end` `{reason}` | Ticket-02 mục 4.4 | shop |
| `fish_spawned`, `monster_hit`, `day_start`, `day_plan`, `phase_start`, `paused`, `resumed` | Ticket-02 mục 4.4 | gather / day |

## 6. Sim ↔ UI (`chonoi/live.py`)
UI chỉ đọc snapshot (`Session.snapshot()`) và gửi `move`, `interact`, `catch` (sau này `shop_done`, `buy`, `pause`). UI không đổi trạng thái sim.
