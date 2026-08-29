@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0runtime\python\python.exe"

if not exist "%PYTHON%" (
    echo Portable Python not found.
    echo Run setup_portable.ps1 first.
    pause
    exit /b 1
)

"%PYTHON%" "%~dp0downloader.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
