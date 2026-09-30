@echo off
title NeXAS Script Tool
cd /d "%~dp0"
python gui.py
if errorlevel 1 (
    echo.
    echo Terjadi kesalahan saat menjalankan gui.py.
    pause
)
