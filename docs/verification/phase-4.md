# Ma trận truy vết Phase 4 (TICKET-04 · Contract v1.3 · Release v1.0.0)

Kiểm chứng trên commit `fe87a8e` (code Phase 4); tag `phase-4` và Release `v1.0.0` trỏ tới commit tài liệu ngay sau trên `main`.
Lệnh test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **142 test, OK** (`docs/proof/phase-4/unittest.txt`).

| AC | Mô tả | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| AC-P4-01 | `contract_version:"1.3"`, khai `bench_cmd`, `soak_cmd` ở gốc manifest; gameplay/kho/JSONL như v1.2 | `test_release_v13.Manifest` | `proof/phase-4/unittest.txt` | đạt |
| AC-P4-02 | `bench_cmd --seed 42 --duration 30 --out bench.json` chạy cảnh lặn chuẩn (độ tươi, cá bơi, Cá Sấu, Út Sen ở bến) 1280×720, làm nóng 3 s, tạo đúng 5 trường | chạy lệnh; `test_release_v13.Bench` (1 s) | `proof/phase-4/bench.json` | đạt |
| AC-P4-03 | Mốc báo cáo: avg ≥ 60 FPS, 1% low ≥ 30 FPS, load ≤ 10 s | đọc `bench.json` | `avg_fps 60.0`, `p1_low_fps 59.52`, `load_ms 2053` | đạt (60 là trần vsync của Chrome headless) |
| AC-P4-04 | `soak_cmd --seed 7 --days 10 --out soak.json`: 10 Ngày một tiến trình, D1–D5 lặp, tiền/uy tín/cấp/id tiếp tục; `days_completed = days`, `crashes = 0`; gameplay lặp lại được | chạy lệnh; `test_release_v13.Soak` (chạy 2 lần, so `results`) | `proof/phase-4/soak.json` | đạt |
| AC-P4-05 | Cảnh báo chữ hoặc biểu tượng: thủy quái gần, oxy sắp hết, khách sắp giận | chơi thử, chụp 1280×720 | `proof/phase-4/warn-gather-thuong.png`, `warn-quan-thuong.png` | đạt |
| AC-P4-06 | Chế độ tương phản cao hoạt động; chơi thử cả ba cảnh báo ở chế độ đó | `?contrast=1` / phím `H`, chụp | `proof/phase-4/warn-gather-tuong-phan-cao.png`, `warn-quan-tuong-phan-cao.png`, `warn_shots.py` | đạt |
| AC-P4-07 | Clone sạch chạy bản có giao diện bằng ≤ 3 lệnh trên macOS; README ghi môi trường, điều khiển, lệnh test/headless/bench/soak | clone sạch → `cd` → `python3 -m chonoi.live --mode day --days 5`, gọi `/state` | `proof/phase-4/clean-clone.txt`, `README.md` | đạt (đã thử macOS; Linux chưa thử) |
| AC-P4-08 | Regression P1–P3 còn hiệu lực | toàn bộ bộ test | `unittest.txt` (142 OK) | đạt |
| AC-P4-09 | `CHANGELOG.md` theo từng phase, release notes, bản đóng gói, CREDITS/LICENSE đã rà | đọc tài liệu | `CHANGELOG.md`, `docs/release-notes-v1.0.0.md`, `CREDITS.md`, asset `cho-noi-v1.0.0.tar.gz` | đạt (repo chưa có file LICENSE — xem clarify Q15) |
| AC-P4-10 | Tag `phase-4` và Release `v1.0.0` cùng commit trên `main` | `git ls-remote --tags`, trang Release | [Release v1.0.0](https://github.com/quocnghidev/K5-L3B-LAB-Day12-AI-SDLC-SLLV/releases/tag/v1.0.0) | đạt |
| AC-P4-11 | Retro rà hành động P2 và chốt việc tiếp theo; phản tư đủ người | đọc tài liệu | `docs/retro.md`, `docs/members/*.md` | đạt |

## Đánh giá ngắn
- **Đạt:** v1.3, bench, soak, cảnh báo + tương phản cao, clone sạch 3 lệnh, regression P1–P3.
- **Không làm:** mở rộng bảng xếp hạng, phụ đề SFX.
