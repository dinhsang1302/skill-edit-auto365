# Cai Skill Edit Auto365 tren Windows 10/11 (khuyen dung GPU NVIDIA) va tao thu muc lam viec.
# Chay (PowerShell, trong thu muc skill):
#   powershell -ExecutionPolicy Bypass -File setup.ps1 [-WS "D:\Auto365Edit"]
# Mac dinh thu muc lam viec: %USERPROFILE%\Videos\Auto365Edit
param([string]$WS = "$env:USERPROFILE\Videos\Auto365Edit")
$ErrorActionPreference = "Continue"
$SK = $PSScriptRoot
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User") }
function WG($id) { winget install --id $id -e --accept-source-agreements --accept-package-agreements; Refresh-Path }

Refresh-Path   # nap PATH moi nhat (chay lan 2 sau khi winget vua cai)
Write-Host "== 1/6 winget"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Write-Host "Chua co winget -> cai 'App Installer' tu Microsoft Store roi chay lai."; exit 1 }

Write-Host "== 2/6 ffmpeg (ban Gyan full: NVDEC/NVENC, scale_cuda)"
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { WG "Gyan.FFmpeg" }
ffmpeg -version | Select-Object -First 1

Write-Host "== 3/6 Python 3.12 + Git (Claude Code can Git for Windows)"
$has312 = $false
try { if ((& py -3.12 -c "print(1)" 2>$null) -eq "1") { $has312 = $true } } catch {}
if (-not $has312) { WG "Python.Python.3.12" }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { WG "Git.Git" }

Write-Host "== 4/6 Thu muc lam viec: $WS"
foreach ($d in "projects","assets\music","assets\sfx","assets\fonts","scripts") { New-Item -ItemType Directory -Force -Path (Join-Path $WS $d) | Out-Null }
Copy-Item "$SK\scripts\*" "$WS\scripts\" -Recurse -Force
Copy-Item "$SK\assets\fonts\*" "$WS\assets\fonts\" -Force
Copy-Item "$SK\VERSION" "$WS\.skill_version" -Force
if (-not (Test-Path "$WS\CLAUDE.md")) {
  $t = Get-Content "$SK\templates\CLAUDE.md.tpl" -Raw -Encoding UTF8
  $t = $t.Replace("{{SK}}", $SK).Replace("{{PY}}", ".venv\Scripts\python").Replace("{{OS}}", "Windows (GPU NVIDIA: NVDEC/NVENC)").Replace("{{REVEAL}}", "explorer /select,<file>")
  [IO.File]::WriteAllText("$WS\CLAUDE.md", $t, (New-Object Text.UTF8Encoding $false))
}

Write-Host "== 5/6 Python (.venv): numpy scipy pillow psutil faster-whisper + CUDA (cuBLAS, cuDNN)"
Set-Location $WS
if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
.\.venv\Scripts\python -m pip install -q --upgrade pip
.\.venv\Scripts\python -m pip install -q numpy scipy pillow psutil opencv-python-headless faster-whisper nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
if ($LASTEXITCODE -ne 0) { Write-Host "pip loi - xem thong bao o tren"; exit 1 }
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User"); $env:PYTHONUTF8 = "1"

Write-Host "== Loc tap am giong: DeepFilterNet 0.5.6 -> bin\deep-filter.exe"
.\.venv\Scripts\python scripts\denoise.py --install
Write-Host "== Nhac nen co giay phep (Mixkit) -> assets\music\_downloaded"
.\.venv\Scripts\python scripts\music.py --install
Write-Host "== 6/6 Kiem tra"
.\.venv\Scripts\python scripts\check_env.py
Write-Host ""
Write-Host "Xong. Chay thu ra clip: cd `"$WS`"; .\.venv\Scripts\python scripts\demo_project.py"
Write-Host "Mo Claude Code:  cd `"$WS`"; claude"
Write-Host "Lan dau nhan giong se tai model whisper (~1,6 GB)."
