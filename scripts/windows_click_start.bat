@echo off
setlocal
cd /d %~dp0\..

where powershell >nul 2>nul
if errorlevel 1 (
  echo PowerShell not found. Please install PowerShell.
  exit /b 1
)

echo [TPM] Starting Windows click-start mode...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows_bootstrap.ps1 -Mode auto -Port 8787
