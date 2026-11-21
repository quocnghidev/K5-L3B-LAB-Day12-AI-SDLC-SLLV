# Kế hoạch Phase 1 (≤ 1 trang)

- **Mục tiêu:** lõi gather + quan đúng PRD-0 mục F, hợp đồng kho mục G, tính tất định; tag `phase-1` trên `main`.
- **Phân công:** Nghị viết và commit cả bốn lát Phase 1 (An vào nhóm sau khi code đã xong). An kiểm chứng bằng tay trước khi tag, rồi nhận phần lớn Phase 2 (`docs/plan/phase-2.md`).

| # | Việc | AC | Người | Phụ thuộc |
|---|---|---|---|---|
| N1 | Commit setup: `TEAM.md`, `game.contract.json` (team, team_size), `.gitignore` | DoD 4 | Nghị | — |
| N2 | Commit lát 1+2: `sim/gather.py` + `tests/test_gather_rules.py` | AC-P1-01..08 | Nghị | N1 |
| N3 | Commit lát 3+4: `sim/quan.py` + `tests/test_quan_rules.py` | AC-P1-09..13 | Nghị | N1 |
| N4 | Commit ghi chép + bằng chứng smoke (`docs/proof/phase-1/`), push | AC-P1-14,15 | Nghị | N2, N3 |
| A1 | Pull, chạy test, chơi thử `chonoi.live` hai buổi nối kho, chụp HUD vào `docs/proof/phase-1/`, cập nhật AC-P1-16 trong `docs/verification/phase-1.md`, commit | AC-P1-16, DoD 1 | An | N4 |
| N5 | Ghi hash commit bàn giao vào `docs/verification/phase-1.md`, gắn và đẩy tag `phase-1` | AC-P1-17 | Nghị | A1 |

- **Rủi ro:** hạn `phase-1` có thể đã qua → tag ngay sau A1, ghi trung thực chỗ chưa xong; giả định PRD ghi `docs/clarify.md`.
