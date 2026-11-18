# Skill Edit Auto365 — lỗi đã gặp và cách sửa

Soát mỗi job. Lọc từ bảng lỗi của xưởng (các job Auto365/VF3/Mazda/F10).

| Lỗi | Gặp ở | Cách sửa (đã đóng gói) |
|---|---|---|
| Chữ động tràn mép khung ("LOẠI NÀO CŨNG ĐƯỢC", "ĐANG CÓ VOUCHER") | job 9:16 cũ | `e365.layout_line` báo lỗi khi dòng > W − 2×60 px và kẹp vào vùng an toàn → giảm cỡ hoặc tách 2 dòng |
| Phụ đề đè chữ động ("NỮ HOÀNG") | job 9:16 cũ | Phụ đề tự ẩn khi chữ động đang hiện (`kin_on` trong build); `check_layout` báo khi cùng hiện mà cách < 24 px |
| Chữ đè mặt người dẫn/người mẫu | Mazda v2 ("CHIẾU SÁNG" góc phải khi người đứng phải), job 9:16 cũ cảnh đầu | Đặt chữ phía đối diện người / vùng ngực giữa cằm và sản phẩm; soát contact sheet |
| Chữ đè hộp sản phẩm trên capo | Mazda | Bỏ chữ động ở cảnh đó, chỉ giữ phụ đề |
| Chữ "NÂNG CẤP" chạm logo áo | F10 10 s | Dời chữ, kiểm khung bằng ảnh có lưới y (như `projects/2026-10-11_job 9:16 cũ/work/stills.py`) |
| Zoom clip AI 720p làm lộ vỡ hình | Mazda | Clip người mẫu AI 720p: **giữ nguyên khung, không zoom in/out** |
| Ảnh "zin" bị làm sáng thành giống ảnh nâng cấp | Mazda v1 | Ảnh so sánh dùng nguyên gốc; chỉ cân phơi sáng khi ghép đôi, theo vùng không bị đèn chiếu |
| Chữ động hiện quá nhanh | F10/Mazda | Thời lượng chốt: mask 0,55 s, trượt 0,8 s, ra 0,35 s (`e365.Word`) |
| Lặp từ do ghép 2 take | job 9:16 cũ | Mỗi câu một take |
| Render đè mất bản cũ | Mazda v1 | Luôn tăng `VER` |
| CPU vọt 618% khi xuất bản giao | job 9:16 cũ | x264 `-threads 2 lookahead-threads=1`, ffmpeg đọc 2 luồng |
| Render chậm 8 lần | Mazda (taskpolicy -b) | Không dùng `taskpolicy -b`; giải mã videotoolbox + scale_vt |
| Hình khựng (rơi ~3,5% frame) | VF3 v2 (Sony XAVC 8-bit) | `VReader` tự giải mã CPU cho clip XAVC; soát khựng bằng đếm frame lặp trong cảnh quay |
| Insert quá ít, trình bày "không giống mẫu" | VF3 v2, v6 | Phân tích mẫu **từng khung** (toạ độ, thời lượng từng chuyển động) trước khi dựng; insert 2–4 s/lần; đo cỡ chữ mẫu, đừng ước lượng |
| Chữ/thẻ đè biển hiệu "3M Pro Shop", logo áo, mặt | VF3 v3–v6 | Soát mắt từng cảnh có vẽ khung an toàn; crop b-roll đẩy biển ra khỏi vùng chữ; cảnh người dẫn có biển sau đầu → chữ vùng ngực canh trái |
| Màu sai luật (vàng, xanh mint của mẫu) | VF3 v2–v3 | Chỉ đỏ/trắng/đen dù mẫu dùng màu khác |
| Chữ không bám kịch bản ("cắt nhiệt", câu tự chế) | VF3 v3 | Tiêu đề/pill/phụ đề lấy nguyên văn kịch bản; phụ đề khớp mốc transcript |
| Light leak nhạt, chuyển cảnh không thấy / sau đó lại thừa | VF3 v6–v11 | Chốt: khác khung cắt thẳng, cùng khung hoà tan 6 frame (mục 6.8) |
| Tia minh hoạ nhiều, bay nhanh | VF3 demo MG | Mũi tên mảnh, ít (≤ 8/pha), ~650 px/s |
| Hiệu ứng minh hoạ quá nhẹ/ngắn nên anh tưởng chưa có | VF3 v9 | Mỗi minh hoạ ≥ 1,5 s, tương phản rõ; báo mốc giây khi giao |
| Phụ đề giật, quá nhanh, trùng chữ pop up | VF3 v9–v11 | Chỉ hiện khi cả câu hiện trọn, ≥ 0,9 s, ≤ 20 ký tự/s, không trùng pop up; tối đa 2 dòng |
| Pop up nhiều quá | VF3 v11 | Chỉ số liệu, tiêu đề chương, tên sản phẩm, 1–2 chú thích, CTA |
| Insert xe thô/xấu ở đoạn kết | VF3 v10 | Hero sản phẩm: Codex vẽ lại theo frame thật (`--image`) trong studio + vệt sáng |
| File đoạn dở trong cache sau khi lỗi | VF3 MG | Render ra `.part.mp4` rồi mới đổi tên |
| Voice TTS nghỉ giữa các câu quá lâu (~0,7–1,2 s) | VF3 V20 Square hook (05/11/2026) | Cắt lặng đầu/cuối từng câu TTS, xếp câu nối nhau **cách ~0,25 s** (chỗ chuyển ý mới nghỉ dài hơn); hình/chữ lùi theo mốc voice, không kéo voice theo hình |
| Khoanh tròn cả chiếc xe (vòng to) → anh không thích; muốn chữ sau chủ thể, minh hoạ vui | VF3 V20 Square hook (05/11/2026) | Khoanh/gạch chỉ cho chi tiết nhỏ hoặc chữ, không khoanh cả xe. Nhấn thỉnh thoảng bằng **chữ lớn nằm sau chủ thể** (`car_mask.py`); ý cảm xúc/xã hội ("hot", "rần rần") → **nhân vật hoạt hình code tay** tông 365 (`projects/2026-11-05_VF3_V20_Square/work/toon.py`), bố cục gọn |
| Thu video vào khung dọc (điện thoại/thẻ 4:5) → cắt mất xe, đèn, ánh sáng; cảnh mở dính người đứng cạnh xe; rác ở mép khung | VF3 V20 Square hook (05/11/2026) | Thu hình vào khung/thẻ: **giữ đúng tỉ lệ nguồn** (16:9 → khung ngang 16:9), không crop mất chủ thể/đèn/vệt sáng. Mỗi cảnh **crop nhẹ** (zoom ~1,05–1,2, chỉnh tâm) để bỏ người/rác ở mép **nếu không mất chủ thể**; không crop được thì đổi cảnh khác. Anh bỏ tách nền (chữ sau chủ thể) từ 05/11 — chữ đặt vùng trống, không đè xe |
| Chuyển cảnh nhanh quá (2–3 cảnh trong 4 s, nhịp thở 1,2 s bằng cảnh mới); cảnh cận góc rộng làm đèn méo / quay nghiêng | VF3 V20 Square nháp v1 (05/11/2026) | **Mỗi cảnh đứng ≥ 2,4 s** (đoạn ngắn thì bớt cảnh — `ShotSeq` trong `projects/2026-11-05_VF3_V20_Square/work/build_full.py`); nhịp thở = kéo dài cảnh trước, không chèn cảnh mới ngắn. Soát cảnh cận bằng lưới ngang: bỏ cảnh góc rộng méo/nghiêng, chọn cảnh thẳng. Lấy cảnh từ bản dựng cũ: dò khung sạch chữ + **dò khung chuyển cảnh màu** (đếm khung bão hoà cao) |
| Zoom giật (25 fps nguồn ép lên 30 fps → lặp 1/5 frame) | job 9:16 cũ | fps ra **đúng fps nguồn** (DJI ở đây 25); đưa FPS vào hash cache đoạn |
| Tiếng người quay ("1, 2, 3") lọt qua tiếng hiện trường | job 9:16 cũ | Chọn đoạn `nat` ngoài các mốc có lời trong transcript nguồn; nhận giọng lại đoạn đã mix để soát |
| Chữ pop up lên/xuống đột ngột, xuống ngay khi vừa hiện | góp ý 18/11/2026 | `Word.HOLD_MIN` 1,2 s: chữ hiện mượt → đứng yên ≥ 1,2 s → ra mượt (ease + mờ); build báo lỗi nếu không đủ chỗ trong đoạn |
| Người dẫn nói lặp từ / vấp "ờ, à" lọt vào bản dựng | góp ý 18/11/2026 | `scripts/stutter.py` dò → nghe lại → `cuts` giữ 1 lần nói; mối cắt trám bằng `covers` (build chặn nếu chưa trám) |
| Giọng có tạp âm (quạt, người nói phía sau) | góp ý 01/11 + 18/11/2026 | `DENOISE="strong"` tự lọc bằng DeepFilterNet (setup tự cài); giọng nhỏ `soft`; không chạy 2 lượt (cụt đuôi chữ) |
| Clip ra không nhạc vì `assets/music` trống | góp ý 18/11/2026 | `MUSIC="auto"`: setup tự tải bộ Mixkit có giấy phép, build tự chọn theo mood |
| Bản giao vẫn còn nói lặp/nói lại (0:41 "được phát, được phát triển", 2:07 "theo em thì mức độ ưu, theo em thì", 2:19 "và muốn đầu tư", 2:35 "còn các anh thì sao") dù đã chạy dò lặp | Corolla Cross v2 (18/11/2026) | Whisper nhận cả clip gộp lần nói lại thành 1 và kéo dài 1 từ ~2 s → `stutter.py --audio` nghe sâu (nhận giọng riêng đoạn từ bị kéo dài/khoảng hở có tiếng) + luật NÓI LẠI (cụm lặp sau vài từ hỏng); bắt buộc `stutter.py --check <bản giao>` ĐẠT trước khi giao |
| Chữ động đè mặt MC ("3M CR BLK"), sát đầu–vai ("20 TRIỆU", "XỨNG ĐÁNG?") | Corolla Cross v2 (18/11/2026) | Build soát YuNet 3 khung mỗi dòng chữ, cấm vùng đầu (mặt nới rộng) + vai–ngực trên, chặn render và gợi ý dời sang phía đối diện người |
