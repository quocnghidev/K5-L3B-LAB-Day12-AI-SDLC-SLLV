# katogithub2701 — phản tư cá nhân (Hoàng Đức An)

- **Tôi đã làm (theo git):** chơi thử hai buổi + ảnh HUD, AC-P1-16 (`cba6508`); lát 3 quán 2 bếp/4 bàn/6 món, lọc `plan_dishes`, lát 4a Shop, smoke tích hợp, `verification/phase-2.md` (`42da03e`); quán/Shop/HUD quán theo kho cá thể v1.2, giữ chỗ theo id, giá theo tươi (`cb663e6`).
- **Tôi đã review:** hợp đồng `docs/contracts/README.md`, `chonoi/sim/gather.py` và `chonoi/sim/day.py` (Phase 2), `docs/adr/0001-kho-ca-the.md` cùng `chonoi/items.py` trên `p3/schema`.
- **AI sai ở đâu và tôi phát hiện thế nào:** ở `42da03e`, AI đặt sai thứ tự tham số `ShopSim.__init__` so với hợp đồng và viết test 4 bàn trong `test_quan_rules.py` vượt tick 3720 làm C1 bỏ đi — phát hiện khi đối chiếu hợp đồng và chạy `unittest`. Ở `cb663e6`, fixture `DOCK` trong `test_day_v11.py` truyền `fresh` thay vì `units` cho `DaySim` — phát hiện khi chạy test và tách `DOCK_RAW`.
- **Điều tôi học được:** chốt hợp đồng và ADR trước giúp làm song song rồi ghép trơn tru; luôn đối chiếu chữ ký hàm, mốc tick và schema nội bộ khi test.
