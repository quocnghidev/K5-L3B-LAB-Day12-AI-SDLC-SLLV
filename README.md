# Day 12 — AI SDLC: Quán Ăn Chợ Nổi

> **Làm theo nhóm 4–6 người** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Út Sen lặn bắt cá, hái rau trên mặt nước rồi tối mở quán phục vụ khách.
> **Yêu cầu từng phase mở đúng mốc giờ tại lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)** (cần đăng nhập claude.ai; có trợ giảng AI cho từng phase).

## Bắt buộc (chỉ có thế)

Cách làm việc kỹ thuật là **tự do** (push thẳng, nhánh + PR, pair, có hay không CI…). Cái bắt buộc:

1. **Một repo chung:** trưởng nhóm **fork** repo này, đặt tên `K5-L3B-LAB-Day12-AI-SDLC-<ten-nhom>`, thêm mọi thành viên làm collaborator (*Settings → Collaborators*, quyền Write) và để repo **public** (giảng viên xem được, không cần mời).
2. **Cả nhóm cùng commit** bằng tài khoản GitHub của mình, mỗi người **≥ 3 commit có nội dung** (làm cặp thì ghi `Co-authored-by:`).
3. **Điền [`TEAM.md`](TEAM.md):** danh sách thành viên + thỏa thuận làm việc nhóm; sửa `team_size` trong [`game.contract.json`](game.contract.json). Commit của người không có trong `TEAM.md` không được tính.
4. **Gắn tag** `phase-1` … `phase-4` đúng hạn; chạy được tại từng tag.
5. **Ghi chép tối thiểu:** `docs/verification/phase-n.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`, `docs/members/<handle>.md`.

## Bắt đầu nhanh

```bash
git clone <fork-của-nhóm> && cd <fork-của-nhóm>
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v        # smoke test
python3 -m chonoi.live --mode gather                                # chơi thử trên trình duyệt (tùy chọn)
```

Game cần chế độ **headless** theo Test Contract (`python3 -m chonoi.headless --mode gather|quan …`) để được chạy và chấm tự động. **Công nghệ không ràng buộc**: khung Python trong `chonoi/` chỉ là gợi ý, chi tiết ở [`docs/STARTER.md`](docs/STARTER.md).

## Tự do sáng tạo

Ngoài phần đề yêu cầu, nhóm được **thêm** nhân vật, loài cá/cây, sinh vật, món, bản đồ, cơ chế, câu chuyện, đồ họa, âm nhạc… với ba điều kiện: **không phá phần cố định** (tắt ở headless), ghi mục **"Sáng tạo của nhóm"** trong README của nhóm, và **làm lõi đúng trước**.

## Lịch 3 giờ

| Mốc | Phase | Hạn tag |
|---|---|---|
| 0:00 | Phase 1 (PRD-0) | `phase-1` trước 1:00 |
| 1:00 | Phase 2 | `phase-2` trước 1:55 |
| 1:55 | Phase 3 | `phase-3` trước 2:30 |
| 2:30 | Phase 4 | `phase-4` + Release `v1.0.0` trước 3:00 |

Hết giờ mỗi phase thì gắn tag rồi đi tiếp; chỗ chưa xong ghi trung thực trong bằng chứng.

## Đánh giá (100 điểm)

| Hạng mục | Điểm |
|---|---|
| Test tự động ẩn (headless, gồm kiểm tra lại phase trước) | 25 |
| Làm việc nhóm (một repo chung, chia việc, tích hợp, đổi yêu cầu) | 25 |
| Kiểm chứng & bằng chứng | 15 |
| Harness AI (AGENTS.md, skill, nhật ký dùng AI) | 10 |
| Đánh giá & retro | 10 |
| Chất lượng sản phẩm (đúng yêu cầu, mở rộng/sáng tạo) | 10 |
| Demo | 5 |

## Quy định

- Dùng AI thoải mái; **không sao chép repo của nhóm khác**; bằng chứng phải thật.
- Nhân vật, bối cảnh là bản gốc của lab; asset ngoài chỉ dùng CC0/CC-BY/MIT hoặc tự tạo, ghi nguồn trong `CREDITS.md`. Không commit API key, token, `.env`.

---

# Nhóm SLLV — Quán Ăn Chợ Nổi v1.0.0 (Test Contract v1.3)

**Yêu cầu môi trường:** macOS hoặc Linux, Python 3 (chỉ thư viện chuẩn, không cần cài gói; đã kiểm trên Python 3.12),
một trình duyệt để chơi. Benchmark cần Google Chrome/Chromium (tự tìm, hoặc đặt `CHROME=<đường dẫn>`).

**Chạy từ clone sạch (3 lệnh):**
```bash
git clone https://github.com/quocnghidev/K5-L3B-LAB-Day12-AI-SDLC-SLLV.git
cd K5-L3B-LAB-Day12-AI-SDLC-SLLV
python3 -m chonoi.live --mode day --days 5          # mở địa chỉ in ra (mặc định http://127.0.0.1:8000/)
```
Bản đóng gói ở GitHub Release `v1.0.0` (`cho-noi-v1.0.0.tar.gz`): giải nén, `cd cho-noi-v1.0.0`, chạy lệnh 3 ở trên.

| Việc | Lệnh |
|---|---|
| Test (1 lệnh) | `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` |
| Headless (Test Contract) | `python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day.jsonl` (`--mode gather|quan|day`) |
| Benchmark có render | `python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json` |
| Soak headless | `python3 -m chonoi.soak --seed 7 --days 10 --out soak.json` |
| Chơi riêng từng buổi | `python3 -m chonoi.live --mode gather --inventory-out kho.json`, rồi `--mode quan --inventory kho.json` |

**Điều khiển:** WASD / mũi tên bơi hoặc đi · `E` tương tác (cập bến, hái, nấu, bưng, phục vụ) · `Space` bắt cá ·
`Esc`/`P` tạm dừng (`M` về menu) · `H` bật/tắt **tương phản cao** (hoặc mở `?contrast=1`) ·
trong Shop `1` mua bình oxy, `2` mua áo phao, `Enter` đóng Shop · màn hình giới thiệu `Enter` để tiếp · `R` chơi lại (chỉ `gather`/`quan`).

**Vòng ngày:** Menu → DayIntro (Má Tư đọc món và nguyên liệu cần lấy) → lặn & hái → EveningIntro → mở quán → DayResult → Shop → Ngày kế; sau Ngày cuối là Summary.
Cấp nâng cấp mua trong Shop có hiệu lực từ Ngày kế.

**Cảnh báo:** banner chữ + biểu tượng ⚠ cho *thủy quái gần*, *oxy sắp hết* (< 25%) và *khách sắp giận* (kiên nhẫn < 25%, thêm "!" trên đầu khách).

**Độ tươi (v1.2):** nguyên liệu hao 0.5/s trong giỏ, 0.25/s trong kho quán; dưới 30 là ươn (ô xám "ươn" trên HUD, không nấu được).
Giá món = `floor(giá niêm yết × trung bình độ tươi / 100)`.

**Cách tính điểm:** `score = earned + 100 × floor(reputation)`. Boa = `floor(giá món đã chốt × 0.2)` nếu phục vụ khi kiên nhẫn còn ≥ 50%. Khách bỏ đi −0.5 uy tín, boa dương +0.2 uy tín, uy tín kẹp [0, 5].

**Hợp đồng tích hợp:** `docs/contracts/README.md` (file kho cá thể `{"items":[{"id":"I1","kind":"ca_loc","fresh":100}]}`, ví dụ `docs/contracts/inventory.sample.json`). Thay đổi theo phase: `CHANGELOG.md`. Kiểm chứng: `docs/verification/phase-1.md` … `phase-4.md`.

**Mở rộng:** không làm (nhóm 2 người, ưu tiên lõi đúng).

**Sáng tạo của nhóm:** chưa có (làm lõi đúng trước).
