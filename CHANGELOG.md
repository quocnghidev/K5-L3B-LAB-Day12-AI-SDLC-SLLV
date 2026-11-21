# Changelog

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
