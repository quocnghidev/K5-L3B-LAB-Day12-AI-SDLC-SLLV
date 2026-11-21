# Kế hoạch Phase 3 — Ticket-03 "Mùa Nước Nổi" (≤ 1 trang)

- **Mục tiêu:** Contract v1.2 kho cá thể có độ tươi, giữ chỗ theo id, giá theo tươi, HUD độ tươi; regression P1–P2 xanh; tag `phase-3`.
- **Quyết định schema và thứ tự tích hợp:** `docs/adr/0001-kho-ca-the.md`. Không làm mở rộng `current`, `reservations`.

## Tác động
| Module | File cần đổi | Test giữ / đổi / thêm | Người |
|---|---|---|---|
| Adapter / schema | `chonoi/items.py` (mới), `chonoi/inventory.py`, `chonoi/scenario.py`, `chonoi/contract.py`, `game.contract.json` | đổi `test_smoke_p1` (kho), `test_contract_v11`; thêm `test_items_v12.py` | Nghị |
| Lặn | `chonoi/sim/gather.py` | đổi fixture `hold` trong `test_gather_rules`, `test_gather_v11`; thêm test ngưỡng 30 | Nghị |
| Day | `chonoi/sim/day.py`, `chonoi/runner.py` (ghi kho) | đổi `test_day_v11`; thêm test id xuyên Ngày | Nghị |
| Quán | `chonoi/sim/quan.py` | đổi `test_quan_rules`; thêm test giữ theo id, giữ lại khi ươn, giá theo tươi | An |
| Shop | `chonoi/sim/shop.py` | đổi `test_shop_rules` | An |
| HUD | `chonoi/web/index.html` | `test_live` giữ | Nghị (sáng), An (quán) |
| QA | `docs/verification/phase-3.md`, `docs/proof/phase-3/` | regression P1–P2 | An |

## DoD → người nhận
| DoD | Người |
|---|---|
| v1.2 bàn giao kho cá thể qua file và `day`, kho đếm mã 2 | Nghị |
| Id, tươi, ươn, giữ chỗ, giá, JSONL đúng luật | Nghị (gather/day), An (quán/Shop) |
| HUD độ tươi; test ngưỡng, giữ lại khi ươn, chốt giá, bàn giao | Nghị (sáng + bàn giao), An (quán + giữ + giá) |
| Ghi tác động, quyết định schema, thứ tự tích hợp | Nghị (ADR, bảng này) |
| `CHANGELOG.md` breaking change | Nghị |
| `verification/phase-3.md`, bằng chứng, regression | An |
| `clarify.md`, nhật ký AI | cả hai |
| Gộp `main` + tag `phase-3` | Nghị |

## Mốc
0–7 ADR + kế hoạch · 7–15 nhánh `p3/schema` (An branch từ đây) · 15–25 gather/day ∥ quán/Shop/HUD · ~20 smoke bàn giao · 25–32 gộp `main`, regression, CHANGELOG, tag.
