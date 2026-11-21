# Ma trận truy vết Phase 3 (TICKET-03 "Mùa Nước Nổi" · Contract v1.2)

Kiểm chứng trên commit `125b571` (`main`); tag `phase-3` trỏ tới commit ngay sau, chỉ cập nhật tài liệu.
Lệnh test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **137 test, OK** (`docs/proof/phase-3/unittest.txt`).
Smoke tích hợp: `bash docs/proof/phase-3/smoke_v12.sh <thư mục tạm>` → `docs/proof/phase-3/smoke-v12.txt`.

| AC | Mô tả | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| AC-P3-01 | `contract_version:"1.2"`, khối `freshness {100, 0.5, 0.25, 30}` | `test_contract_v11.StandardData`, `chonoi/contract.py` kiểm khối | `proof/phase-3/unittest.txt` | đạt |
| AC-P3-02 | File kho cá thể `{"items":[{id,kind,fresh}]}`; kho đếm v1.1, thiếu khóa, id trùng, kind lạ, fresh ngoài [0,100] → mã 2 | `test_items_v12.InventoryFile`, smoke | `unittest.txt`, `smoke-v12.txt` (`[kho đếm v1.1] exit=2`) | đạt |
| AC-P3-03 | Ghi file đủ chính xác: đọc lại đúng đơn vị ở sát ngưỡng 30, sắp theo id, ghi đúng một lần, ngất ghi rỗng | `test_items_v12.test_written_file_round_trips_exact_units_near_threshold`, `test_gather_rules` (faint) | `unittest.txt` | đạt |
| AC-P3-04 | Smoke bàn giao file (Ticket-03): cập bến tick 0 → `quan --inventory --ticks 0` đúng id, kind, fresh sau một lần hao | `test_smoke_p1.test_inv_01_gather_writes_inventory_quan_reads_it`, smoke | `smoke-v12.txt` (`fresh 99.99166…`, `khớp … True`) | đạt |
| AC-P3-05 | Bàn giao trong `day` cùng tick, không hao thêm; id `I<n>` tăng xuyên pha và Ngày; Ngày kế cấp id mới cho mẫu `gather.hold` | `test_day_v11.RealShopHeadless.test_items_hand_off_same_tick_and_ids_continue_across_days` | `unittest.txt` | đạt |
| AC-P3-06 | Hao tươi: giỏ 0.5/s, kho quán 0.25/s (cả hàng đang giữ), kẹp 0; hàng mới 100 hao từ bước sau; pause dừng hao; Shop không hao | `test_items_v12.Decay`, `QuanStockDecay`, `test_shop_rules.test_shop_stock_does_not_decay` | `unittest.txt` | đạt |
| AC-P3-07 | Ươn `fresh < 30`: `spoiled {item_id,kind,location}` đúng một lần, theo id; ví dụ Ticket-03 fresh 30 → `spoiled` tick 1 | `test_items_v12.Threshold`, smoke | `smoke-v12.txt` (`[ngưỡng 30]`) | đạt |
| AC-P3-08 | Giữ chỗ theo id: tươi nhất rồi id nhỏ; hàng giữ vừa ươn → nhả toàn bộ, giữ lại đúng một lần, thiếu → `unfulfillable` | `test_quan_rules.Phase3Freshness` (`test_reserve_picks_freshest_then_lowest_id`, `test_spoiled_reservation_re_reserves_once_or_turns_unfulfillable`) | `unittest.txt` | đạt |
| AC-P3-09 | Giá theo tươi `floor(niêm yết × TB fresh / 100)` chốt lúc nấu; boa trên giá đã chốt; điểm không đổi công thức | `test_quan_rules.Phase3Freshness.test_base_price_and_tip_computed_from_average_freshness` | `unittest.txt` | đạt |
| AC-P3-10 | JSONL: `hold`/`stock`/`reserved`, `cook_started.items` (kind rồi id), `lost` của `monster_hit`/`faint` (LIFO) theo schema cá thể | `test_gather_rules`, `test_gather_v11.Crocodile`, `test_quan_rules.Kitchen` | `unittest.txt` | đạt |
| AC-P3-11 | Fixture scenario v1.2 sai/mâu thuẫn → mã 2 (hold sai schema, reserved trỏ id không có, đã ươn, dùng chung, khác công thức) | `test_items_v12.test_bad_scenario_hold_exit_2`, `test_quan_rules.BadFixtures` | `unittest.txt` | đạt |
| AC-P3-12 | HUD cho thấy độ tươi / hàng ươn ở giỏ và kho quán | chụp Chrome headless 1280×720 | `proof/phase-3/hud-gather-freshness.png`, `hud-quan-freshness.png` | đạt |
| AC-P3-13 | `day` chạy trọn, tất định, ≤ 20 s/Ngày | smoke `day --days 1/3`, `cmp` | `smoke-v12.txt` (1.48 s, 3.82 s, giống từng byte) | đạt |
| AC-P3-14 | Regression P1–P2 còn hiệu lực; test đổi vì luật mới có lý do | toàn bộ bộ test | `unittest.txt`; lý do trong commit `3792836`, `cb663e6` và `CHANGELOG.md` | đạt |
| AC-P3-15 | Ghi tác động, quyết định đổi schema, thứ tự tích hợp; `CHANGELOG.md` breaking change | đọc tài liệu | `docs/adr/0001-kho-ca-the.md`, `docs/plan/phase-3.md`, `CHANGELOG.md`, merge `eecebf5` | đạt |

## Đánh giá ngắn
- **Đạt:** toàn bộ lõi Ticket-03; tích hợp theo đúng thứ tự ADR (adapter + gather + day trên `p3/schema`, quán + Shop + HUD quán trên `p3/quan`, gộp `main` một lần ở `eecebf5`, `main` không đỏ giữa chừng).
- **Không làm:** mở rộng `current` (dòng lũ) và `reservations` (khách đặt trước) — không bắt buộc với nhóm 2 người (ADR 0001 mục 6).
- **Giả định:** `docs/clarify.md` Q10–Q13.
