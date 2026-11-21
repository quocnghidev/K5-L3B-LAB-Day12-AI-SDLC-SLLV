# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt: chốt giao diện `ShopSim` trong `docs/contracts/README.md` trước khi code, nên `day` (Nghị) và Shop (An) làm song song rồi ghép không phải sửa; test `day` dùng `FakeShop` theo đúng giao diện. Regression P1 giữ xanh, test đổi vì số chuẩn đều ghi lý do.
- Điều tệ: lát 0 (contract) đi trước nên An phải chờ; một commit lẻ bị đỏ vì tách commit sai thứ tự; phần menu/HUD ban đầu bị ghi "ngoài phạm vi" trong kế hoạch dù DoD yêu cầu, phát hiện muộn khi rà lại Ticket-02.
- 1 hành động cho Phase 3: rà DoD của ticket ngay ở phút 0–5 và gán người cho từng mục DoD (không chỉ cho từng lát) — người nhận: Nghị.

## Phase 3 (nhanh) — rút ra từ lần đổi kho
- Hành động Phase 2 đã làm: `docs/plan/phase-3.md` có bảng "DoD → người nhận" ngay phút đầu, nên không sót mục HUD/CHANGELOG như Phase 2.
- Điều tốt: ADR 0001 chốt biểu diễn số nguyên (240 đơn vị/điểm) trước khi code → không lệch ở ngưỡng 30; tách nhánh `p3/schema` → `p3/quan` và gộp `main` một lần nên `main` không đỏ giữa chừng; helper `items()` trong test làm đổi fixture nhanh.
- Điều tệ: đổi schema kho chạm gần như mọi test (≈ 40 test đỏ lúc bật v1.2), phải đổi fixture hàng loạt; An phải chờ adapter trước khi bắt đầu quán.
- 1 hành động cho Phase 4: trước khi bắt đầu, chạy toàn bộ test + smoke `day` trên `main` và ghi số liệu nền (số test, thời gian/Ngày) để so khi bench — người nhận: Nghị.

## Phase 4 (cuối)
- **Rà lại hành động Phase 2** ("rà DoD ngay phút 0–5 và gán người cho từng mục DoD", người nhận Nghị): **đã làm** ở Phase 3 (`docs/plan/phase-3.md` có bảng "DoD → người nhận") và Phase 4 (`docs/plan/phase-4.md` theo vai). Kết quả: Phase 3–4 không sót mục DoD nào như HUD ở Phase 2. Vướng: việc kiểm chứng P3 giao An nhưng cuối phase phải chuyển sang Nghị để kịp tag — giao việc theo DoD chưa tính thời gian dự phòng của từng người.
- **Rà hành động Phase 3** ("ghi số liệu nền trước Phase 4", Nghị): **đã làm** — 137 test / 17.3 s, `day --days 5` 6.54 s trên `e06cf83` (`docs/plan/phase-4.md`), dùng để so: Phase 4 có 142 test, soak 10 Ngày ~5 s.
- **Điều tốt:** chốt hợp đồng trước khi code (`ShopSim` ở P2, ADR kho cá thể ở P3) giúp hai người làm song song và ghép không phải sửa; `main` luôn xanh nhờ nhánh `p3/schema` → `p3/quan` gộp một lần; mọi test đổi đều có lý do trong commit; bằng chứng bằng ảnh chụp Chrome headless bắt được lỗi giao diện mà test không thấy.
- **Điều tệ:** đóng góp lệch (Nghị 22 commit, An 3 commit không tính merge) vì An vào sau và Nghị kiêm Integrator; thiếu thời gian để An tham gia Phase 4; FPS chỉ đo được trần 60 Hz.
- **Số liệu:** commit (không tính merge, từ `f0a1906`): quocnghidev 22, katogithub2701 3. Đọc code của nhau: Nghị review `42da03e` (Shop), `cb663e6` (quán v1.2) trước khi gộp; An review `gather.py` ở Phase 2 theo kế hoạch. Token theo người: chưa đo (nhật ký AI ghi "chưa đo").
- **Một lần AI sai và cách nhóm xác minh:** ở Phase 2 AI đặt cờ UI tên `hold` trùng trường giỏ `hold` của snapshot → menu và giỏ không vẽ, mà cả 121 test vẫn xanh. Nhóm phát hiện nhờ chụp màn hình bằng Chrome headless và đọc log console (`forEach is not a function`), sửa thành `ui_hold`, thêm ảnh vào bằng chứng.
- **Nếu làm lại / hành động tiếp theo:** (1) chia lát sao cho người vào sau nhận một lát trọn vẹn sớm (không chỉ QA) — người nhận: Nghị; (2) đo FPS bằng trình duyệt có cửa sổ thật (không vsync headless) — người nhận: Nghị.
