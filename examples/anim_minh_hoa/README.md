# Hoạt hình minh hoạ trên ảnh render chân thực (Corolla Cross v4, 19/11/2026)

- `prompts/r_*.txt`: prompt Codex vẽ ảnh nền (không chữ/số/logo/biển số, 1/3 phải tối để đặt chữ kin). Chạy trong `work/anim/real/<tên>/`:
  `codex exec --skip-git-repo-check --sandbox workspace-write -C . -c model_reasoning_effort="low" -c service_tier="default" - < prompt.txt`
- `anim.py`: tiện ích (ease, glow, thanh đo, encode). `anim2.py`: từng cảnh = ảnh nền + đẩy máy + hiệu ứng code:
  sóng nhiệt/UV/hồng ngoại dội khỏi kính (`waves`, `sparks`), lớp phim quét qua kính (`film_sweep`), sơ đồ phim nhìn từ trên (`f_filmmap`),
  cửa sổ trời (`f_sunroof`), nhắc quan sát gương ban đêm (`f_night`), thanh đo = đúng số thoại (`A.bar`).
- `SCENES = {tên: (hàm, độ dài ra, tốc độ)}`; `python anim2.py <tên…>` → `work/anim/<tên>.mp4`; `--preview` → ảnh xem nhanh.
- Ảnh AI chỉ minh hoạ, không làm bằng chứng; xe trong ảnh là xe chung chung, không logo.
