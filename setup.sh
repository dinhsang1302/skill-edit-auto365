#!/bin/bash
# Cài Skill Edit Auto365 trên Mac (Apple Silicon) và tạo thư mục làm việc.  Windows: dùng setup.ps1
# Dùng:  bash setup.sh [thư_mục_làm_việc=~/Movies/Auto365Edit]
set -e
SK="$(cd "$(dirname "$0")" && pwd)"
WS="${1:-$HOME/Movies/Auto365Edit}"
echo "== 1/5 Homebrew"
command -v brew >/dev/null || { echo "Chưa có Homebrew → cài theo https://brew.sh rồi chạy lại."; exit 1; }
echo "== 2/5 ffmpeg + Python 3.12"
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list python@3.12 >/dev/null 2>&1 || brew install python@3.12
echo "== 3/5 Thư mục làm việc: $WS"
mkdir -p "$WS"/{projects,assets/music,assets/sfx}
rsync -a "$SK/scripts/" "$WS/scripts/"
rsync -a "$SK/assets/fonts/" "$WS/assets/fonts/"
cp "$SK/VERSION" "$WS/.skill_version"
[ -f "$WS/CLAUDE.md" ] || sed -e "s#{{SK}}#$SK#g" -e "s#{{PY}}#.venv/bin/python#g" -e "s#{{OS}}#macOS Apple Silicon (videotoolbox)#g" \
  -e "s#{{REVEAL}}#open -R <file>#g" "$SK/templates/CLAUDE.md.tpl" > "$WS/CLAUDE.md"
echo "== 4/5 Python (.venv): numpy scipy pillow psutil mlx-whisper opencv"
[ -x "$WS/.venv/bin/python" ] || "$(brew --prefix python@3.12)/bin/python3.12" -m venv "$WS/.venv"
"$WS/.venv/bin/pip" install -q --upgrade pip
"$WS/.venv/bin/pip" install -q numpy scipy pillow psutil mlx-whisper opencv-python-headless
echo "== Lọc tạp âm giọng: DeepFilterNet 0.5.6 → bin/deep-filter"
(cd "$WS" && .venv/bin/python scripts/denoise.py --install) || echo "  (chưa tải được deep-filter — chạy lại setup khi có mạng)"
echo "== Nhạc nền có giấy phép (Mixkit) → assets/music/_downloaded"
(cd "$WS" && .venv/bin/python scripts/music.py --install) || echo "  (chưa tải được nhạc — chạy lại setup khi có mạng)"
echo "== 5/5 Kiểm tra"
cd "$WS" && .venv/bin/python scripts/check_env.py
echo; echo "Xong. Chạy thử ra clip: cd \"$WS\" && .venv/bin/python scripts/demo_project.py"; echo "Mở Claude Code:  cd \"$WS\" && claude"
