# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | Phase 1 | PRD-0 chỉ nói `dive`/`surface` phát "khi đổi phía của biên mặt nước". Biên là d ≤ 0.5 (mặt nước) hay d > 0.5 (dưới nước)? | Giả định: mặt nước = `d <= surface_depth` (khớp mục F oxy); `dive` khi từ mặt nước xuống dưới 0.5, `surface` ngược lại. Chưa hỏi Anh Năm. | PO (tự quyết) |
| 2 | Phase 1 | Khách ở `waiting` thì `base_price` trong snapshot là gì trước khi bếp "chốt giá"? | Giả định: gán giá menu lúc khách đến (menu cố định nên bằng giá chốt khi nấu); `tip` = 0 tới lúc phục vụ. | PO (tự quyết) |
| 3 | Phase 1 | `catch` khi giỏ thiếu chỗ: "giữ đàn và cooldown" nghĩa là gì? | Giả định: giữ đàn, hồi chiêu giữ nguyên giá trị hiện tại (không đặt lại), chỉ phát `hold_full`. | PO (tự quyết) |
| 4 | Phase 1 | Snapshot `quan.player` có `vel` không? | Có `pos` và `vel` (mục E nói "player theo D"). | PO (tự quyết) |
