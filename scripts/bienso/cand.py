"""Tiện ích chung: src(n) → đường dẫn clip C<n>.MP4 trong insert/ hoặc input/ của dự án (chạy trong <dự án>/work/plates/)."""
import pathlib
P = pathlib.Path("../..")
def src(n):
    for d in ("insert", "input"):
        for ext in (".MP4", ".mp4", ".MOV", ".mov"):
            f = P / d / f"C{n}{ext}"
            if f.exists(): return f
    raise FileNotFoundError(f"không thấy C{n} trong insert/ hoặc input/")
