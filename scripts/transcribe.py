#!/usr/bin/env python3
"""Nhận giọng tiếng Việt có mốc thời gian từng từ. Mac: mlx-whisper (Apple Silicon). Windows: faster-whisper (CUDA, RTX).
Model: whisper large-v3-turbo (Mac: mlx-community/whisper-large-v3-turbo; Windows: "large-v3-turbo" của faster-whisper).
Dùng:
  <python> scripts/transcribe.py <video|audio> <out.json> [model]      → 1 file
  <python> scripts/transcribe.py <thư_mục_input> <thư_mục_out> [model]  → cả thư mục (bỏ qua file đã có json)
Ra: {"text", "segments":[{"start","end","text","words":[{"w","s","e"}]}]}. Lần đầu tải model ~1,6 GB.
Windows: GPU lỗi (thiếu cuBLAS/cuDNN) → tự chạy CPU int8 (chậm hơn nhiều lần, có báo).
Sau khi chạy BẮT BUỘC hiệu đính tay (references/quy-trinh.md mục Transcript)."""
import json, sys, os, glob

EXT = (".mp4", ".mov", ".m4a", ".mp3", ".wav", ".aac")
try:
    import mlx_whisper; BACKEND = "mlx"
except ImportError:
    BACKEND = "fw"
MODEL = sys.argv[3] if __name__ == "__main__" and len(sys.argv) > 3 else ("mlx-community/whisper-large-v3-turbo" if BACKEND == "mlx" else "large-v3-turbo")
_FW = None

def _fw_model():
    global _FW
    if _FW: return _FW
    if sys.platform.startswith("win"):                         # DLL cuBLAS/cuDNN cài bằng pip (nvidia-*-cu12)
        for d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
            os.add_dll_directory(d); os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
    from faster_whisper import WhisperModel
    try:
        _FW = WhisperModel(MODEL, device="cuda", compute_type="float16"); print("faster-whisper: GPU CUDA", flush=True)
    except Exception as e:
        print(f"faster-whisper: GPU lỗi ({str(e)[:120]}) → chạy CPU int8, chậm hơn", flush=True)
        _FW = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=max(2, (os.cpu_count() or 4) // 4))
    return _FW

def run(src):
    if BACKEND == "mlx":
        r = mlx_whisper.transcribe(src, path_or_hf_repo=MODEL, language="vi", word_timestamps=True, condition_on_previous_text=False)
        return r["text"], [{"start": s["start"], "end": s["end"], "text": s["text"].strip(),
                            "words": [{"w": w["word"].strip(), "s": round(w["start"], 2), "e": round(w["end"], 2)} for w in s.get("words", [])]}
                           for s in r["segments"]]
    segs, _ = _fw_model().transcribe(src, language="vi", word_timestamps=True, condition_on_previous_text=False, beam_size=5)
    out = [{"start": s.start, "end": s.end, "text": s.text.strip(),
            "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in (s.words or [])]} for s in segs]
    return " ".join(s["text"] for s in out), out

def tx(src, out):
    text, segs = run(src)
    json.dump({"text": text.strip(), "segments": segs}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"== {os.path.basename(src)}", flush=True)
    for s in segs: print(f"  [{s['start']:6.2f} – {s['end']:6.2f}] {s['text']}", flush=True)

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    src, out = sys.argv[1], sys.argv[2]
    if os.path.isdir(src):
        os.makedirs(out, exist_ok=True)
        for f in sorted(os.listdir(src)):
            if f.lower().endswith(EXT) and not os.path.exists(o := os.path.join(out, os.path.splitext(f)[0] + ".json")):
                tx(os.path.join(src, f), o)
    else:
        tx(src, out)
