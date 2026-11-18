# Skill Edit Auto365 — nhận diện style

Style mặc định của xưởng Edit365 cho clip Auto365 (đèn, phim, phụ kiện ô tô). Chốt 17/10/2026.
Nguồn: phân tích một clip mẫu TikTok 9:16 (chỉ học style, không dùng hình/tiếng của clip mẫu).

## Chữ (điểm nhận diện chính)
- **Chữ động theo từng từ**, đặt quanh/sau người dẫn, không theo khung phụ đề cố định.
- Phối 3 kiểu chữ:
  - `w` chữ thường: **Anton** trắng (đậm hẹp)
  - `k` keyword: **Anton đỏ viết hoa** (`RED` = (226, 32, 40)), mỗi dòng ≤ 1 keyword
  - `it` từ nối: **Playfair Display Italic** trắng
- Chữ hiện nhẹ: **mask trồi lên + trượt ngang**, không pop mạnh. Thời lượng chốt: mask 0,55 s · trượt 0,8 s · ra 0,35 s (`e365.Word`).
  Keyword lớn hiện tối đa ~1,6 s.
- Phụ đề: PNG, Inter Display ExtraBold 66 (16:9) / ~48–56 (9:16), trắng viền tối + bóng mềm, keyword hổ phách `#FFC83D`, pop nhẹ 140 ms;
  16:9 đặt ~86% chiều cao, 9:16 ~0,62–0,70 H. **Lúc có chữ pop up thì ẩn phụ đề.**

## Hình
- Grade tối, phông xám/xanh, đèn practical ấm; nền mờ sâu khi chữ lên.
- **Thẻ ảnh bay** (ảnh hộp, bóng đèn, beam) lơ lửng có độ sâu.
- **Khung kính bo góc** chứa ảnh/thông số; thẻ thông số luôn có **chip nguồn** (vd. "Thông số in trên hộp: POWER 75/45W").
- So sánh trước/sau: ghép đôi cùng khung, ảnh gốc giữ nguyên, chỉ cân phơi sáng theo vùng không bị đèn chiếu.
- Khung 9:16 đứng xa (thấy người + sản phẩm), không crop sát mặt. Clip AI 720p: giữ nguyên khung, không zoom.

## Nhịp & chuyển cảnh
- Mỗi cảnh ~4 s, nhưng cứ 1–2 s có một thay đổi (chữ, thẻ bay, zoom). Lời đọc liền, cắt lặng > 0,4 s.
- Khác khung → **cắt thẳng**, không hiệu ứng, không swish. Cùng khung nối tiếp → **hoà tan ~6 frame**.
- Hạn chế pop up: chỉ số liệu, tiêu đề chương, tên sản phẩm, CTA; còn lại để phụ đề.

## Mạch
hook (mở đầu thấy người dẫn) → nỗi đau → reveal sản phẩm (không reveal hết ở frame đầu) → lý do kỹ thuật/tính năng → bằng chứng (thông số in trên hộp, beam thật) → lợi ích → (end card khung kính + nút CTA đỏ nếu kênh cần; **TikTok thì không end card/CTA** trừ khi được yêu cầu).

## Màu
Ưu tiên **đỏ / đen / trắng / vàng**, xám ít. Màu thương hiệu Auto365: đỏ `#E31B22`, nền `#0D0F13` / `#15171C`, chữ phụ `#9AA3B2`.

## Không làm
Nhân bản người, bóng người cắt AI, glow kiểu game, flare không nguồn, khói, speed line; chữ đè sản phẩm / thông số / mặt người / logo.

## Code
`scripts/e365.py`: `STYLES["dark"]` (Auto365), `Word`, `layout_line`, `cta`, `rounded`/`with_shadow`.
Mẫu: `examples/f10_10s_16x9_nen_toi.py`, `examples/mazda_full_16x9.py`.
