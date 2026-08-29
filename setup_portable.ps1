param(
    [string]$PythonVersion = "3.13.15"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $Root "runtime\python"
$DenoDir = Join-Path $Root "tools\deno"
$FfmpegDir = Join-Path $Root "tools\ffmpeg"
$DownloadsDir = Join-Path $Root "downloads"
$DataDir = Join-Path $Root "data"
$TempDir = Join-Path $Root ".portable-build"

New-Item -ItemType Directory -Force -Path $RuntimeDir, $DenoDir, $FfmpegDir, $DownloadsDir, $DataDir, $TempDir | Out-Null

Write-Host "[1/5] Python $PythonVersion portable"
$PyZip = Join-Path $TempDir "python-embed.zip"
$PyUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
Invoke-WebRequest -Uri $PyUrl -OutFile $PyZip
Get-ChildItem $RuntimeDir -Force | Remove-Item -Recurse -Force
Expand-Archive -Path $PyZip -DestinationPath $RuntimeDir -Force

# Embedded Python disables site by default. Enable it and add site-packages.
$Pth = Get-ChildItem $RuntimeDir -Filter "python*._pth" | Select-Object -First 1
if (-not $Pth) { throw "python*._pth not found" }
$PthText = Get-Content $Pth.FullName -Raw
$PthText = $PthText -replace '#import site', 'import site'
if ($PthText -notmatch '(?m)^Lib\\site-packages\s*$') {
    $PthText = $PthText.TrimEnd() + "`r`nLib\site-packages`r`n"
}
Set-Content -Path $Pth.FullName -Value $PthText -Encoding ASCII

Write-Host "[2/5] pip + Python dependencies"
$GetPip = Join-Path $TempDir "get-pip.py"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip
$PythonExe = Join-Path $RuntimeDir "python.exe"
& $PythonExe $GetPip --no-warn-script-location
& $PythonExe -m pip install --upgrade --no-warn-script-location -r (Join-Path $Root "requirements.txt")

Write-Host "[3/5] Portable FFmpeg"
$FfmpegSource = (& $PythonExe -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())").Trim()
if (-not (Test-Path $FfmpegSource)) { throw "FFmpeg from imageio-ffmpeg not found: $FfmpegSource" }
Copy-Item $FfmpegSource (Join-Path $FfmpegDir "ffmpeg.exe") -Force

Write-Host "[4/5] Portable Deno"
$Release = Invoke-RestMethod -Uri "https://api.github.com/repos/denoland/deno/releases/latest" -Headers @{"User-Agent"="yt-dlp-portable-builder"}
$Asset = $Release.assets | Where-Object { $_.name -eq "deno-x86_64-pc-windows-msvc.zip" } | Select-Object -First 1
if (-not $Asset) { throw "Deno Windows x64 asset not found" }
$DenoZip = Join-Path $TempDir "deno.zip"
Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $DenoZip
Get-ChildItem $DenoDir -Force | Remove-Item -Recurse -Force
Expand-Archive -Path $DenoZip -DestinationPath $DenoDir -Force

Write-Host "[5/5] Validation"
& $PythonExe -c "import imageio_ffmpeg; from yt_dlp.version import __version__; print('Python OK'); print('yt-dlp:', __version__)"
& (Join-Path $DenoDir "deno.exe") --version
& (Join-Path $FfmpegDir "ffmpeg.exe") -version | Select-Object -First 1

Remove-Item $TempDir -Recurse -Force

Write-Host ""
Write-Host "Portable build is ready."
Write-Host "Start with: run.bat"
Write-Host "You can now move the entire folder to another Windows x64 machine."
