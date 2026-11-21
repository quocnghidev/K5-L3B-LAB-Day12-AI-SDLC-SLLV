# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | Phase 1 | PRD-0 chỉ nói `dive`/`surface` phát "khi đổi phía của biên mặt nước". Biên là d ≤ 0.5 (mặt nước) hay d > 0.5 (dưới nước)? | Giả định: mặt nước = `d <= surface_depth` (khớp mục F oxy); `dive` khi từ mặt nước xuống dưới 0.5, `surface` ngược lại. Chưa hỏi Anh Năm. | PO (tự quyết) |
| 2 | Phase 1 | Khách ở `waiting` thì `base_price` trong snapshot là gì trước khi bếp "chốt giá"? | Giả định: gán giá menu lúc khách đến (menu cố định nên bằng giá chốt khi nấu); `tip` = 0 tới lúc phục vụ. | PO (tự quyết) |
| 3 | Phase 1 | `catch` khi giỏ thiếu chỗ: "giữ đàn và cooldown" nghĩa là gì? | Giả định: giữ đàn, hồi chiêu giữ nguyên giá trị hiện tại (không đặt lại), chỉ phát `hold_full`. | PO (tự quyết) |
| 4 | Phase 1 | Snapshot `quan.player` có `vel` không? | Có `pos` và `vel` (mục E nói "player theo D"). | PO (tự quyết) |
| 5 | Phase 2 | `recoil_dist` trong contract là gì? Ticket chỉ nói "mỗi bước 2/60 m". | Giả định: tổng quãng lùi = 2 m, mỗi bước `recoil_dist / recoil_ticks` = 2/60 m. | PO (tự quyết) |
| 6 | Phase 2 | 8 đàn đầu ca chọn loài/điểm thế nào? | Giả định: lặp 8 lần luật sinh cá (trọng số loài chuẩn hóa theo loài còn điểm, điểm đều, cách đàn đang sống > 1 m) → 8 điểm hình học khác nhau. | PO (tự quyết) |
| 7 | Phase 2 | Cá Sấu "đến" waypoint khi nào nếu số thực lệch vài ulp? | Coi như tới khi quãng còn lại ≤ bước + 1e-9 (240 bước × 1/60 m = đúng 4 m). | PO (tự quyết) |
| 8 | Phase 2 | Ngưỡng "người chơi ở d ≥ 10" để Cá Sấu đuổi/chạm lấy từ đâu? | Lấy cận dưới `depths` của loài (Cá Sấu 10), để mở rộng Rắn (d ≥ 8) dùng cùng luật. | PO (tự quyết) |
| 9 | Phase 2 | DayIntro/EveningIntro/DayResult có làm dừng mô phỏng không? | Chỉ ở cửa sổ chơi: máy chủ giữ (không bước) khi đổi pha cho tới khi người chơi bấm tiếp; headless không có màn này nên tick không đổi. | PO (tự quyết) |
| 10 | Phase 3 | Khi nhiều đơn cùng có hàng giữ vừa ươn: nhả hết rồi mới giữ lại, hay xử lý từng đơn? | Giả định: xử lý từng đơn theo `order_tick` rồi id bàn — nhả toàn bộ phần giữ của đơn đó rồi giữ lại đúng một lần trước khi sang đơn kế. | PO (tự quyết) |
| 11 | Phase 3 | "Đủ độ chính xác khi đọc lại" cho file kho là bao nhiêu chữ số? | Ghi `fresh = units / 240` bằng float đầy đủ (repr Python, đọc lại `round(fresh × 240)` ra đúng đơn vị); JSONL vẫn làm tròn 3 chữ số (dung sai ±0.01). | PO (tự quyết) |
| 12 | Phase 3 | Ngày 1 trong `day` giữ id mẫu `gather.hold`, id hàng mới bắt đầu từ đâu? | Bộ cấp id `I` nạp trước id của mẫu, nên hàng mới nối sau hậu tố lớn nhất (mẫu `I1` → hàng mới `I2`); Ngày kế cấp id mới cho mẫu theo thứ tự mảng. | PO (tự quyết) |
| 13 | Phase 3 | Có làm mở rộng `current`, `reservations` không? | Không: nhóm 2 người, ưu tiên lõi đúng trong 35 phút (ADR 0001 mục 6). | Nghị + An |
| 14 | Phase 4 | Bench "có render" đo thế nào khi game vẽ trên trình duyệt? | Chrome/Chromium headless 1280×720 tải trang thật ở chế độ `?bench=1`, đếm khung bằng `requestAnimationFrame`; `load_ms` tính từ lúc lệnh khởi chạy tới khung đầu tiên có snapshot. Headless bị giới hạn vsync 60 Hz nên avg tối đa ≈ 60. | Nghị |
| 15 | Phase 4 | Repo chưa có `LICENSE`; có thêm giấy phép không? | Chưa thêm: code starter thuộc giảng viên, nhóm không tự chọn giấy phép thay; không dùng asset ngoài (CREDITS.md). Chờ giảng viên / nhóm quyết. | Nghị |
| 16 | Phase 4 | Soak "bằng script input hoặc bot tất định" — bot cần chơi giỏi tới đâu? | Bot tối thiểu (hái rau mặt nước, nấu/bưng/phục vụ, mua nâng cấp khi đủ tiền) đủ để đi qua `gather → quan → shop` mỗi Ngày; mục tiêu là độ bền và tính lặp, không tối ưu điểm. | Nghị |
