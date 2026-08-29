@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0runtime\python\python.exe"
if not exist "%PYTHON%" (
  echo Portable Python not found. Run setup_portable.ps1 first.
  pause
  exit /b 1
)
"%PYTHON%" -m pip install -U --no-warn-script-location -r "%~dp0requirements.txt"
echo.
echo Python packages updated.
pause
