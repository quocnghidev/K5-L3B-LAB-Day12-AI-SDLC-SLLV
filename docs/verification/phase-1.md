# Ma trận truy vết Phase 1

Kiểm chứng trên working tree dựa trên commit `f0a1906` (chưa commit lúc ghi; cập nhật hash khi gắn tag `phase-1`).
Lệnh: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → 70 test, OK (`docs/proof/phase-1/unittest.txt`).

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P1-01 Bơi, ramp, chặn biên (gather) | `tests/test_smoke_p1.py` (Movement) | `proof/phase-1/unittest.txt` | đạt |
| AC-P1-02 Oxy: dưới nước trừ 1, mặt nước hồi 6, kẹp [0,max] | `tests/test_gather_rules.py::Oxygen` | unittest.txt | đạt |
| AC-P1-03 Ngạt: lần đầu ở t+59, mỗi 60 tick −1 Máu; nổi lên đúng bước thì không ngạt | `Oxygen.test_oxygen_empty_event_once_and_first_choke_after_60_steps`, `test_surfacing_on_choke_step_saves_player` | unittest.txt | đạt |
| AC-P1-04 Ngất: bỏ giỏ LIFO, `faint`, `gather_end fainted`, kho rỗng | `Oxygen.test_faint_loses_hold_lifo_and_writes_empty_inventory` | unittest.txt | đạt |
| AC-P1-05 `dive` / `surface` chỉ khi đổi phía biên mặt nước | `Oxygen.test_dive_and_surface_events` | unittest.txt | đạt |
| AC-P1-06 Hái nút: ở mặt nước, đúng mép bán kính, gần nhất rồi id nhỏ, `hold_full`, mọc lại sau 20 s | `tests/test_gather_rules.py::Gathering` | unittest.txt | đạt |
| AC-P1-07 Bắt cá: dưới nước, hồi chiêu 30 tick, `fish_caught`, `hold_full` giữ đàn và không hồi chiêu | `tests/test_gather_rules.py::Catching` | unittest.txt | đạt |
| AC-P1-08 Cập bến xét trước hái; hết giờ giữ giỏ; kho ghi đúng một lần | `Docking`, `test_inv_01_*` | unittest.txt | đạt |
| AC-P1-09 Khách đến theo lịch, chọn món đủ nguyên liệu khả dụng theo seed, giữ chỗ, `no_dish` | `tests/test_quan_rules.py::Arrivals` | unittest.txt | đạt |
| AC-P1-10 Bếp: nấu (tiêu nguyên liệu), `dish_ready`, `dish_picked`, một interact mỗi bước | `Kitchen` | unittest.txt | đạt |
| AC-P1-11 Phục vụ, boa đúng ngưỡng, ăn xong trả tiền, uy tín | `Serving` | unittest.txt | đạt |
| AC-P1-12 Khách bỏ đi: trừ uy tín, nhả giữ chỗ, bỏ món đang nấu/trên tay; hết ca đóng quán | `Leaving` | unittest.txt | đạt |
| AC-P1-13 Fixture mâu thuẫn → mã 2, không ghi đầu ra | `BadFixtures` | unittest.txt | đạt |
| AC-P1-14 Smoke hai tiến trình theo PRD-0 mục G | chạy lệnh mục G | `proof/phase-1/smoke-two-process.txt` (quán đọc `{"bong_sung":2,"ca_loc":1}`) | đạt |
| AC-P1-15 Cùng seed → output giống từng byte (gather và quan) | `cmp` hai lượt 10800 tick | `smoke-two-process.txt` | đạt |
| AC-P1-16 Chơi được cả hai buổi trên trình duyệt, HUD đọc được | `python3 -m chonoi.live` | `proof/phase-1/hud_gather.png`, `proof/phase-1/hud_quan.png` | đạt |
| AC-P1-17 Tag `phase-1` trên `main` | `git tag` | chưa gắn | **chưa đạt** |

## Đánh giá ngắn
- Đạt: toàn bộ luật lõi gather và quan theo mục F; hợp đồng kho mục G; tính tất định; chơi thử cả hai buổi trên trình duyệt (`chonoi.live`) nối kho, HUD đọc được.
- Chưa đạt / chưa kiểm chứng: chưa gắn tag `phase-1` (HUD hiện dùng hình khối tạm của khung).
- Giả định đã đặt: xem `docs/clarify.md` (Q1–Q4).
- Chưa có test cho: chọn một interact giữa bếp và bàn khi cùng khoảng cách; tương tác khi nhiều khách (preset chỉ có 1 bàn nên chỉ kiểm được bằng fixture sửa bàn).
- Điều cần chỉnh cho phase sau: đọc kỹ Ticket-02 trước khi động tới contract; giữ luật đọc số từ `game.contract.json`.
