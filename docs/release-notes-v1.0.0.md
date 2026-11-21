# Quán Ăn Chợ Nổi v1.0.0 — nhóm SLLV

Game 2D quản lý quán ăn miền Tây: sáng Út Sen lặn bắt cá, hái rau trên sông; tối nấu và phục vụ khách trên nhà bè; cuối ngày mua nâng cấp.

## Điểm mới
- **Vòng ngày 5 Ngày** (`--mode day`): kế hoạch món D1–D5, Shop nâng cấp bình oxy / áo phao (hiệu lực từ Ngày kế), menu, pause, DayIntro / EveningIntro / DayResult / Summary.
- **Buổi sáng:** 8 đàn cá bơi và sinh thêm, Cá Sấu Năm Chèo tuần tra / đuổi / chạm, oxy, ngạt, ngất.
- **Buổi tối:** 2 bếp, 4 bàn, 6 món, giữ chỗ nguyên liệu, boa, uy tín.
- **Mùa Nước Nổi (v1.2):** kho cá thể có độ tươi, hàng ươn, giữ chỗ theo id, giá theo độ tươi.
- **v1.3:** cảnh báo chữ + biểu tượng, chế độ tương phản cao, `bench_cmd`, `soak_cmd`.

## Cách chạy
Cần Python 3 (chỉ thư viện chuẩn) và một trình duyệt.
```bash
tar xzf cho-noi-v1.0.0.tar.gz && cd cho-noi-v1.0.0
python3 -m chonoi.live --mode day --days 5      # mở địa chỉ in ra
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v   # test
```
Điều khiển: WASD bơi/đi · E tương tác · Space bắt cá · Esc/P dừng · H tương phản cao · Shop: 1/2 mua, Enter đóng.

## Số đo (commit bàn giao, máy nhóm)
- Benchmark: `avg_fps 60.0`, `p1_low_fps 59.52`, `load_ms 2053` (Chrome headless 1280×720, 30 s).
- Soak 10 Ngày: `days_completed 10`, `crashes 0`, ~5 s. Headless 1 Ngày (22.200 tick) ~1.5 s.

## Giới hạn đã biết
- Đồ họa là hình khối 2D tạm, chưa có âm thanh.
- FPS bench bị giới hạn bởi vsync 60 Hz của Chrome headless, nên 60 là trần đo được chứ không phải tối đa của máy.
- Bench cần Chrome/Chromium; không có thì `bench_cmd` trả mã 1.
- Không làm các mở rộng (dòng lũ, khách đặt trước, bảng xếp hạng, phụ đề SFX, Lao, Vợt, Rắn, Cháy món, Chợ, Sổ tay).
- Bot của `soak_cmd` chỉ hái rau và phục vụ đơn giản; dùng để kiểm độ bền, không để tối ưu điểm.
