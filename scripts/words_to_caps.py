#!/usr/bin/env python3
"""Gợi ý dòng phụ đề từ transcript (words.json của scripts/transcribe.py), in sẵn dạng tuple dán vào SEGS[...]["caps"].
Cắt cụm ở: khoảng ngừng > 0,3 s, dấu câu, hoặc khi dài quá N ký tự (mặc định 42 cho 9:16; 16:9 dùng ~48).
Áp bảng sửa từ (hiệu đính) từ file fix.tsv nếu có: mỗi dòng "sai<TAB>đúng" (vd. "code\tcos", "slide\tX-Light").
Dùng: .venv/bin/python scripts/words_to_caps.py <words.json> [từ_giây] [đến_giây] [--max 42] [--fix work/fix.tsv]
Kết quả CHỈ là gợi ý: phải đọc lại, sửa chính tả/thuật ngữ, chọn ≤ 1 keyword mỗi dòng (cột thứ 3)."""
import json, sys, argparse
ap = argparse.ArgumentParser(); ap.add_argument("words"); ap.add_argument("a", nargs="?", type=float, default=0)
ap.add_argument("b", nargs="?", type=float, default=1e9); ap.add_argument("--max", type=int, default=42); ap.add_argument("--fix")
o = ap.parse_args()
FIX = [l.rstrip("\n").split("\t") for l in open(o.fix, encoding="utf-8") if "\t" in l] if o.fix else []
ws = [w for s in json.load(open(o.words, encoding="utf-8"))["segments"] for w in s.get("words", []) if o.a - 0.02 < w["s"] < o.b]
chunks, cur = [], []
for w in ws:
    txt = " ".join(x["w"] for x in cur + [w])
    if cur and (w["s"] - cur[-1]["e"] > 0.3 or len(txt) > o.max): chunks.append(cur); cur = []
    cur.append(w)
    if w["w"][-1:] in ",.?!": chunks.append(cur); cur = []
if cur: chunks.append(cur)
for c in chunks:
    t = " ".join(x["w"] for x in c)
    for bad, good in FIX: t = t.replace(bad, good)
    print(f'    ({c[0]["s"]:.2f}, "{t.rstrip(",.")}", None),   # → {c[-1]["e"]:.2f}')
