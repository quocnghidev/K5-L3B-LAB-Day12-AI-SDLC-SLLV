# Changelog

## v1.0.0 — Phase 4, Contract v1.3 (Ticket-04)

### Thêm
- `bench_cmd` (`python3 -m chonoi.bench --seed --duration --out`): đo FPS có render bằng Chrome/Chromium headless 1280×720,
  cảnh lặn seed 42, làm nóng 3 s; `bench.json {avg_fps, p1_low_fps, frames, measured_s, load_ms}`.
- `soak_cmd` (`python3 -m chonoi.soak --seed --days --out`): N Ngày trong một tiến trình bằng bot tất định, D1–D5 lặp ở Ngày 6–10;
  `soak.json {days, days_completed, crashes, results[{day, earned, reputation, score}], duration_s}`.
- Cảnh báo chữ + biểu tượng: thủy quái gần, oxy sắp hết, khách sắp giận; chế độ tương phản cao (`H`, `?contrast=1`).
- README: yêu cầu môi trường, chạy 3 lệnh từ clone sạch, lệnh test/headless/bench/soak. CREDITS rà lại.

### Đổi
- `contract_version: "1.3"`; gameplay, tuning, kho và JSONL giữ như v1.2.
- `plan_for`: Ngày > 5 dùng lại kế hoạch D1–D5.

## Unreleased

## Phase 3 — Contract v1.2 "Mùa Nước Nổi" (Ticket-03)

### BREAKING CHANGE — kho cá thể có độ tươi (ADR `docs/adr/0001-kho-ca-the.md`)
- **File kho** `--inventory` / `--inventory-out` và `gather_end.data.inventory`:
  `{"items": {"ca_loc": 1}}` → `{"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}` (kho rỗng `{"items": []}`, sắp theo id).
  File kho đếm v1.1 giờ trả **mã 2**; id trùng, kind lạ, `fresh` ngoài [0, 100] cũng mã 2.
- **Scenario:** `gather.hold` và `quan.stock` là mảng cá thể `{id, kind, fresh}`; `customers[].reserved` là mảng id cá thể.
- **JSONL:** snapshot `hold` (thứ tự vào giỏ), `stock` (quán, Shop) và `customers[].reserved` theo schema mới;
  `cook_started.data.items`, `monster_hit.lost`, `faint.lost` là mảng cá thể; event mới `spoiled {item_id, kind, location}`.
- `game.contract.json`: `contract_version: "1.2"`, thêm `freshness {initial: 100, gather_decay_per_s: 0.5, quan_decay_per_s: 0.25, spoiled_below: 30}`.

### Cách cập nhật fixture
| Cũ (v1.1) | Mới (v1.2) |
|---|---|
| `"hold": ["ca_loc", "bong_sung"]` | `"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I2", "kind": "bong_sung", "fresh": 100}]` |
| `"stock": {"ca_loc": 2}` | `"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I2", "kind": "ca_loc", "fresh": 100}]` |
| `"reserved": {"ca_loc": 1}` | `"reserved": ["I1"]` |
| kiểm `lost == ["ca_linh"]` | kiểm `[x["id"] for x in lost]` |
Trong test dùng `tests/helpers.py: items("ca_loc", "bong_sung", fresh=100)` để sinh id `I1, I2, …`.

### Thêm
- `chonoi/items.py`: cá thể nội bộ `{id, kind, units}` với 240 đơn vị/điểm tươi (hao 2 đơn vị/tick ở giỏ, 1 ở kho quán).
- Gather: hao tươi đầu bước, `spoiled` theo id, id `I<n>` tăng xuyên pha và Ngày (`day` dùng chung bộ cấp id).
- HUD sáng: thanh độ tươi từng ô giỏ, nhãn "ươn".

## Phase 2 — Contract v1.1 (Ticket-02)
- Số chuẩn, cá bơi/sinh, Cá Sấu, 2 bếp/4 bàn, 6 món, `--mode day`, Shop, pause, menu/HUD vòng ngày.

## Phase 1 — Contract v1.0 (PRD-0)
- Lõi gather + quán, kho đếm theo loại, smoke hai tiến trình.
