# Kế hoạch Phase 2 — Ticket-02 (≤ 1 trang)

- **Mục tiêu:** Test Contract v1.1 (số chuẩn), cá bơi/sinh, Cá Sấu, 2 bếp/4 bàn, 6 món, `--mode day` + Shop + pause; regression P1 còn xanh; tag `phase-2`.
- **Nguyên tắc chia:** An giữ phần quan + Shop (ít đụng gather), Nghị giữ gather + chuyển pha `day`. Lát 0 làm trước vì cả hai phụ thuộc.

| # | Lát | Việc | AC | Người | Phụ thuộc |
|---|---|---|---|---|---|
| 0 | Contract | `game.contract.json` lên `1.1`: khóa gather mới, `monsters`, B2/T2–T4, 6 món, `day_plan`, `shop`; cập nhật `docs/contracts/` | AC-P2-01 | Nghị | — |
| 1 | Gather | Số chuẩn, N5/N6, `ca_keo`, cá bơi (phản xạ mép, đổi hướng theo seed), sinh cá mỗi 360 tick, `fish_spawned` | AC-P2-02..04 | Nghị | 0 |
| 2 | Cá Sấu | patrol/chase/recoil, `monster_hit` (LIFO nửa giỏ), bất tử 90 tick, `faint` cause `monster` | AC-P2-05..07 | Nghị | 0 |
| 3 | Quán | 2 bếp/4 bàn, 6 món, chọn món lọc theo kế hoạch ngày trong `day`, quán riêng dùng cả 6 món | AC-P2-08..09 | **An** | 0 |
| 4a | Shop | Nâng cấp `oxygen`/`hp` theo dữ liệu, `buy`, `bought`/`buy_failed`/`shop_end`, tự đóng sau 600 tick, hiệu lực từ Ngày kế | AC-P2-10..11 | **An** | 0 |
| 4b | Day | `--mode day --days N`: `day_start → day_plan → phase_start`, bàn giao kho trong bộ nhớ, `days_completed`, pause/resume | AC-P2-12..14 | Nghị | 1, 3, 4a |
| QA | Kiểm chứng | Smoke tích hợp phút 20 (`docs/proof/phase-2/integration.*`), regression P1 với số chuẩn, `docs/verification/phase-2.md` | AC-P2-15 | **An** | 1, 3 |
| R | Retro | `docs/retro.md` mục Phase 2 (một hành động có người nhận) | — | cả hai | — |

- **Ngoài phạm vi trước:** menu/HUD đầy đủ ở `chonoi/web/` làm sau khi headless đúng; mở rộng (Lao, Vợt…) không bắt buộc với nhóm 2 người.
- **Rủi ro:** lát 4b phụ thuộc cả ba lát kia → An đưa fixture Shop/quán sớm; test P1 đổi vì số chuẩn phải ghi lý do trong commit.
