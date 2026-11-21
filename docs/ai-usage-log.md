# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| 1 | quocnghidev (Nghị) | Claude Code (Sonnet 5.5) | Đọc repo + PRD-0, điền TEAM.md, viết luật `sim/gather.py` và `sim/quan.py`, viết `tests/test_gather_rules.py`, `tests/test_quan_rules.py`, tài liệu Phase 1 | chưa đo | (1) Lần đầu tóm tắt lab board, AI nói PRD-0 bị khóa; thực ra nội dung nằm trong DB của artifact và người dùng phải dán. (2) AI viết test quán với kho rỗng nhưng khách giữ chỗ `ca_loc`; luật kiểm tra mới (đúng) trả mã 2 nên 3 test đỏ. Người đọc phải xác nhận lỗi ở fixture của test, không phải ở luật. (3) Chạy smoke bằng biến `$H` trong zsh bị "command not found"; chuyển sang script bash. |
