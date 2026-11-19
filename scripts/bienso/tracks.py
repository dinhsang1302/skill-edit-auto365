# Danh sách vùng cần che — điền cho từng dự án (toạ độ khung 1920x1080, góc TL,TR,BR,BL ở khung mồi seed_t).
# style: "plate" = đè biển trắng trơn bo góc · "patch" = xoá số sơn trên thân xe bằng màu thân xe lấy theo hàng.
# soft (tuỳ chọn): sigma làm mềm tấm che cho xe nền bị mất nét (vd 2–5).
# range: giây NGUỒN cần che (phủ hết khúc được dùng ± 0,3 s; lấy từ shots_of() của build).
TR = [
 # ("8501a", "8501", 2.5, [[290,730],[459,777],[469,829],[295,782]], (1.2, 4.9), "plate"),
 # ("8520a", "8520", 2.8, [[1803,636],[1851,636],[1851,677],[1803,677]], (0.6, 5.0), "plate", 5),
]
