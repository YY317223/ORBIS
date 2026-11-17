@echo off
chcp 65001 >nul
title ORBIS - data service
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found in PATH. Install Python 3.9+ and try again.
  pause
  exit /b 1
)
python app.py --open %*
if errorlevel 1 pause
