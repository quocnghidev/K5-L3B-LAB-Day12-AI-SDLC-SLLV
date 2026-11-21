# ADR 0001 — Kho cá thể có độ tươi (Ticket-03, Contract v1.2)

- **Trạng thái:** chấp nhận (Phase 3)
- **Người quyết:** Nghị (Integrator), An đồng ý

## Bối cảnh
Ticket-03 thay kho đếm theo loại (`{"items":{"ca_loc":1}}`) bằng kho cá thể có độ tươi
(`{"items":[{"id":"I1","kind":"ca_loc","fresh":100}]}`), giữ chỗ theo id và giá theo độ tươi. Đây là breaking change
cho file kho, scenario (`gather.hold`, `quan.stock`, `customers[].reserved`) và JSONL (`hold`, `stock`, `reserved`,
`cook_started.items`, `lost`).

## Quyết định
1. **Biểu diễn độ tươi bằng số nguyên:** 240 đơn vị = 1 điểm tươi (`chonoi/items.py`). Gather trừ 2 đơn vị/tick
   (0.5/s), quán trừ 1 đơn vị/tick (0.25/s); so ngưỡng `fresh < 30` trên số nguyên (7200 đơn vị), không lệch số thực.
   Đọc vào: `round(fresh × 240)`; xuất JSONL `units / 240` (3 chữ số); xuất file kho đủ chính xác để đọc lại đúng
   đơn vị (không làm tròn 3 chữ số).
2. **Một cá thể trong mọi nơi chứa:** `{"id","kind","fresh"}` (bên trong giữ thêm `units`). Giỏ giữ thứ tự vào giỏ
   (LIFO khi mất). Kho quán, Shop sắp theo id khi xuất.
3. **Cấp id `I<n>`:** một bộ cấp `IdAllocator` họ `I` sống suốt lượt; `day` truyền cùng bộ cấp qua mọi pha và Ngày,
   nạp trước các id có sẵn trong fixture (id mới nối sau hậu tố lớn nhất).
4. **Chỉ một schema khi chạy:** `game.contract.json` có `contract_version:"1.2"` thì chỉ nhận kho cá thể; kho đếm → mã 2.
   Không giữ đường v1.1 song song trong code (ít nhánh, ít test hơn); test cũ đổi fixture sang mảng cá thể.
5. **Giữ chỗ theo id** (quán, An): tươi nhất rồi id nhỏ; cá thể giữ vừa ươn → nhả toàn bộ phần giữ của đơn, giữ lại
   đúng một lần, thiếu → `unfulfillable`. Giá chốt lúc nấu `floor(niêm yết × trung bình fresh / 100)`.
6. **Không làm mở rộng** `current`, `reservations` ở Phase 3 (nhóm 2 người, ưu tiên lõi đúng).

## Thứ tự tích hợp (giữ `main` xanh)
1. ADR + kế hoạch lên `main` (chỉ tài liệu).
2. Nghị: nhánh `p3/schema` — `items.py`, `inventory.py`, `scenario.py`, contract v1.2. An branch `p3/quan` từ đây.
3. Song song: Nghị gather + day trên `p3/schema`; An quán + Shop + HUD quán trên `p3/quan`.
4. Gộp cả hai vào `main` **một lần** khi cả hai đầu bàn giao đã xanh (không gộp nửa vời: gather v1.2 + quán v1.1 làm đỏ).
5. Smoke ngưỡng 30, smoke bàn giao file, `day`; regression P1–P2; CHANGELOG; tag `phase-3`.

## Hệ quả
- Mọi fixture `hold`/`stock`/`reserved` trong test phải viết lại dạng cá thể (ghi lý do trong commit).
- File kho v1.1 cũ không đọc được nữa (đúng yêu cầu: mã 2).
