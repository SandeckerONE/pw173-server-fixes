@echo off
rem Builds PW173Editor.exe in the dist folder. Needs internet once to install PyInstaller.
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller
py -m PyInstaller --noconfirm --onefile --windowed --name PW173Editor --add-data "layouts;layouts" main.py
echo.
echo Done. The program is dist\PW173Editor.exe
pause
