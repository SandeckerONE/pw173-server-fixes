@echo off
rem Runs the editor straight from the Python files (no build needed).
cd /d "%~dp0"
py main.py
if errorlevel 1 pause
