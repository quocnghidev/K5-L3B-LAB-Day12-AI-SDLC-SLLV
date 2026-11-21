# Hợp đồng tích hợp — nhóm SLLV (Test Contract v1.1)

Đổi hợp đồng: báo người kia trước, ghi lý do trong commit. Số liệu chỉ nằm trong `game.contract.json`.

## 1. File kho (gather → quan)
- Schema: `{"items": {"<kind>": <số nguyên >= 0>}}`, chỉ có khóa `items`, bỏ khóa có lượng 0. Ví dụ: `inventory.sample.json`.
- Kind hợp lệ (v1.1): `ca_loc`, `ca_linh`, `ca_keo`, `bong_dien_dien`, `bong_sung`, `keo_neo` (`chonoi/inventory.py: KINDS_P1`).
- Gather ghi đúng một lần khi `gather_end` (ngất ghi rỗng); quan đọc bằng `--inventory`. Trong `day`, bàn giao trong bộ nhớ cùng schema.

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
        # upgrades: {"oxygen": cấp đã mua, "hp": cấp đã mua} (cấp vắng = 0); stock: kho dư từ ca tối
    def step(self, inp) -> list[tuple[str, dict]]: ...
        # một buy (inp.buy) trước cạnh shop_done; event bought / buy_failed / shop_end
    def snapshot(self) -> dict: ...   # stock, upgrades
    # thuộc tính runner đọc: money, earned, reputation, time_left_ticks, done, reason, upgrades
```
`day` (`chonoi/sim/day.py`) gọi `ShopSim(tuning, money, earned, reputation, upgrades, stock)` khi `quan_end`,
đọc lại `money, earned, reputation, upgrades` khi `done`, rồi sao `upgrades` sang `active_upgrades` lúc dựng Ngày mới.
Event Shop trả dạng `(name, data)` như gather/quan; `day` tự gắn `phase`/`day`.

## 4b. Quán trong `day` (An, lát 3)
`day` dựng `QuanSim(...)` rồi gán `sim.plan_dishes = set(id món trong kế hoạch Ngày)` và `money/earned/reputation`
xuyên Ngày. Quán chạy riêng không có thuộc tính này (= cả 6 món). Lát 3 cần lọc món theo `plan_dishes`
trước khi lọc nguyên liệu khả dụng.

## 5. Sự kiện
| Sự kiện | `data` | Phát ở |
|---|---|---|
| `gather`, `node_regrown`, `hold_full`, `fish_caught`, `dive`, `surface`, `oxygen_empty`, `choke`, `faint`, `gather_end` | theo PRD-0 mục E | gather |
| `customer_arrived`, `no_dish`, `cook_started`, `dish_ready`, `dish_picked`, `served`, `paid`, `customer_left`, `quan_end` | theo PRD-0 mục E | quan |
| `bought` `{upgrade,level,price,money}`, `buy_failed` `{action,reason}`, `shop_end` `{reason}` | Ticket-02 mục 4.4 | shop |
| `fish_spawned`, `monster_hit`, `day_start`, `day_plan`, `phase_start`, `paused`, `resumed` | Ticket-02 mục 4.4 | gather / day |

## 6. Sim ↔ UI (`chonoi/live.py`)
UI chỉ đọc snapshot (`Session.snapshot()`) và gửi `move`, `interact`, `catch` (sau này `shop_done`, `buy`, `pause`). UI không đổi trạng thái sim.
