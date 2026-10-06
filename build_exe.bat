@echo off
REM Release build: single-file NINAHSaveEditor.exe, no Python needed.
REM The console window stays visible on purpose: closing it stops the server.
REM Requires: pip install -r requirements.txt pyinstaller
"D:\Программы\python\python.exe" -m PyInstaller --noconfirm --onefile --console ^
  --name NINAHSaveEditor --add-data "web;web" ninah_gui.py
echo.
echo Result: dist\NINAHSaveEditor.exe
