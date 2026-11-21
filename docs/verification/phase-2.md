# Ma trận truy vết Phase 2 (TICKET-02 · Contract v1.1)

Kiểm chứng trên working tree dựa trên commit `26b7c5d` (cập nhật hash commit bàn giao khi gắn tag `phase-2`).
Lệnh test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **117 test, OK** (`docs/proof/phase-2/unittest.txt`).

| AC | Mô tả | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| AC-P2-01 | Contract v1.1: số chuẩn, `B2`, `T2–T4`, 6 món, `day_plan`, `shop`, nguyên liệu mới | `tests/test_contract_v11.py` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-02 | Gather: số chuẩn, N5/N6 `keo_neo`, `ca_keo` | `tests/test_contract_v11.py`, `tests/test_gather_v11.py` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-03 | Đàn cá: đầu ca 8 đàn, bơi 1.5 m/s, đổi hướng theo seed mỗi 120 tick, phản xạ mép | `tests/test_gather_v11.py::FishSwimming` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-04 | Sinh cá mỗi 360 tick, trần 12, `fish_spawned`, trọng số & khoảng cách > 1 m | `tests/test_gather_v11.py::FishSpawning` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-05 | Cá Sấu M1/M2: `patrol`, `chase` (d ≥ 10 & ≤ 10 m), thoát `> 16 m` hoặc `d < 10` | `tests/test_gather_v11.py::Crocodile` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-06 | Va chạm Cá Sấu: mất 1 Máu, bỏ `floor(n/2)` LIFO, bất tử 90 tick, `recoil` 60 tick | `tests/test_gather_v11.py::Crocodile` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-07 | Ngất do quái: `faint` (`cause: "monster"`), `gather_end` (`fainted`), kho rỗng | `tests/test_gather_v11.py::Crocodile.test_faint_by_monster` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-08 | Quán: 2 bếp (`B1`, `B2`), 4 bàn (`T1`–`T4`), 6 món từ dữ liệu | `tests/test_quan_rules.py::Phase2QuanExpansion` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-09 | Quán: trong `day` lọc món theo `plan_dishes` trước khi lọc nguyên liệu; quán riêng dùng cả 6 món | `tests/test_quan_rules.py::Phase2QuanExpansion` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-10 | Shop: nâng cấp `oxygen`/`hp` theo `shop.upgrades`, `buy` trước `shop_done`, `bought`/`buy_failed`/`shop_end`, tự đóng 600 tick | `tests/test_shop_rules.py::ShopUpgrades` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-11 | Shop: cấp vừa mua hiển thị ngay (`upgrades`), hiệu lực từ Ngày kế (`active_upgrades`) | `tests/test_shop_rules.py`, `tests/test_day_v11.py`, `day --days 2` | `proof/phase-2/unittest.txt`, `proof/phase-2/day-smoke.txt` | đạt |
| AC-P2-12 | Day: `--mode day --days N`, `day_start → day_plan → phase_start`, bàn giao kho trong bộ nhớ | `tests/test_day_v11.py::DayFlow` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-13 | Day: `days_completed`, `reason: "days_complete"`, hiệu năng ≤ 20 s/Ngày & tất định | `day --days 1` (1.978 s, `same_bytes=True`) | `proof/phase-2/day-smoke.txt` | đạt |
| AC-P2-14 | Pause/Resume ở cả 3 mode: đóng băng gameplay/timer/lịch, bỏ qua hành động & `buy` | `tests/test_day_v11.py::Pause` | `proof/phase-2/unittest.txt` | đạt |
| AC-P2-15 | Smoke tích hợp (`gather --inventory-out → quan --inventory`), regression P1 với số chuẩn | chạy CLI 2 tiến trình & `test_smoke_p1.py` | `proof/phase-2/integration.txt`, `proof/phase-2/unittest.txt` | đạt |

## Đánh giá ngắn
- **Đạt:** Toàn bộ 117 unit/integration/smoke test đều xanh; smoke tích hợp 2 tiến trình (`gather` → `quan`) khớp kho ở tick 0 (`match=True`); `--mode day --days 1` chạy trong `1.978s` (< 20s) và tất định (`same_bytes=True`); `--mode day --days 2` xác nhận nâng cấp `oxygen` cấp 1 ở cuối Ngày 1 tăng `oxygen_max_ticks` lên `2700` từ đầu Ngày 2.
- **Thay đổi test P1 vì số chuẩn v1.1 (đã ghi rõ lý do):**
  - `tests/test_quan_rules.py`: tách `test_no_spawn_when_table_full_and_reservation_blocks_stock` thành `test_reserved_stock_is_not_available_to_next_customer` (vì v1.1 có 4 bàn `T1–T4` nên `T2` trống phát `no_dish`) và `test_no_spawn_when_all_tables_full` (lấp đủ 4 bàn).
  - `tests/test_smoke_p1.py`: `test_con_03_old_and_future_modes_rejected` bỏ `"day"` khỏi danh sách mode bị từ chối vì `--mode day` đã được hỗ trợ ở Contract v1.1.
- **Việc tiếp theo trước khi gắn tag `phase-2`:** cập nhật `docs/retro.md`, `docs/ai-usage-log.md`, kiểm tra `tools/check_team.py`, commit và gắn tag `phase-2` trên `main`.
