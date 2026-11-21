# quocnghidev — phản tư cá nhân (Lã Quốc Nghị)

- **Tôi đã làm:** luật gather + quán Phase 1 (`4b49923`, `d63e1bc`); contract v1.1, cá bơi/sinh, Cá Sấu, `--mode day`, pause, UI vòng ngày Phase 2 (`150e7ac`, `4ff96c8`, `26b7c5d`, `7970bde`); ADR kho cá thể, adapter v1.2, gather/day theo độ tươi Phase 3 (`611df60`, `fa2db9f`, `3792836`); bench, soak, cảnh báo + tương phản cao, phát hành Phase 4 (`fe87a8e`). Kiêm PO/Integrator: gộp `main`, gắn tag.
- **Tôi đã giúp / review:** chốt giao diện `ShopSim` và `QuanSim` cho An (`docs/contracts/README.md`), push sớm nhánh `p3/schema` để An làm quán; review và gộp `42da03e`, `cb663e6`.
- **AI sai ở đâu, tôi phát hiện thế nào:** đặt tên cờ UI trùng trường `hold` (test vẫn xanh) — phát hiện nhờ chụp màn hình và log console; Cá Sấu tới waypoint trễ 1 tick do cộng dồn số thực — test tuần tra bắt được.
- **Điều tôi học được:** chốt hợp đồng/ADR trước khi chia việc thì làm song song mới nhanh; bằng chứng bằng hình bắt được lỗi mà test hộp đen bỏ sót; nên giao cho người vào sau một lát trọn vẹn sớm hơn.
