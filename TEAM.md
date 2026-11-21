# TEAM

**Tên nhóm:** SLLV  **Số người:** 2  (khớp `team_size` trong `game.contract.json`)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Lã Quốc Nghị | quocnghidev | `sim/gather`, `client/ui` | PO · Integrator (giữ `docs/contracts/`, gắn tag) | `sim/quan` |
| Hoàng Đức An | katogithub2701 | `sim/quan`, `qa` | QA lead · Scrum/Release | `sim/gather` |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm

- Kênh liên lạc: nhắn trực tiếp; ghi lại trong `docs/standup.md` và `docs/clarify.md`.
- Khi bất đồng về thiết kế: nói 2 phút, không xong thì Integrator (Nghị) quyết và ghi ADR ngắn trong `docs/adr/`.
- Khi vướng quá 10 phút: báo người kia ngay; người dự phòng nhận việc. Câu hỏi về PRD ghi vào `docs/clarify.md`.
- Giờ standup giữa phase: ghi một dòng vào `docs/standup.md` ở mỗi mốc phase.
- Cách đọc code: review chéo — Nghị đọc `sim/quan`, An đọc `sim/gather` — trước khi gắn tag; ghi chỗ AI sai vào `docs/ai-usage-log.md`.
- Cách làm việc với Git: nhánh ngắn cho mỗi lát rồi gộp vào `main`; chạy test trước khi gộp; chỉ gắn tag `phase-n` khi `main` xanh.
