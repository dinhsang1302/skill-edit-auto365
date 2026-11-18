# Xưởng dựng clip — Skill Edit Auto365

Dựng mọi clip trong thư mục này theo skill **Skill Edit Auto365** (`edit-auto365`): đọc `{{SK}}/SKILL.md`
và `{{SK}}/references/` (style.md, quy-trinh.md, loi-da-gap.md) trước khi dựng.

- Trả lời tiếng Việt, ngắn, kết luận trước.
- Python: `{{PY}}` (môi trường riêng của thư mục này). Máy: {{OS}}.
- Mỗi clip một thư mục `projects/<YYYY-MM-DD>_<Ten>/` — tạo bằng `{{PY}} scripts/new_project.py <Ten>`.
- Script là nguồn của bản dựng (`projects/X/work/build.py`); mỗi lần sửa tăng `VER`, không ghi đè bản cũ.
- Render từng đoạn tuần tự, canh CPU bằng `e365.start_cpu_watch` (trần 50% CPU máy). Không chạy song song nhiều đoạn.
- Không bịa thông số; ảnh AI chỉ minh hoạ, không làm bằng chứng (hộp, beam, trước/sau phải là ảnh thật).
- Nhạc/SFX chỉ dùng file có giấy phép trong `assets/music`, `assets/sfx` (`MUSIC="auto"` tự chọn bộ Mixkit đã tải).
- Giọng tự lọc tạp âm (DeepFilterNet), tự bỏ chỗ lặp/vấp (`scripts/stutter.py`) và trám mối cắt bằng insert; chữ pop up đứng ≥ 1,2 s.
- Xong bản nào thì mở thư mục chọn sẵn file đó ({{REVEAL}}) để người dùng xem ngay.
