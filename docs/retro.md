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
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
