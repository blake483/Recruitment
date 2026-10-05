@echo off
rem Double-click this file to start CV Search on Windows.
title CV Search
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto run

echo.
echo  First run: setting things up. This takes a minute or two and only happens once.
echo.
set "PY=python"
where py >nul 2>nul && set "PY=py"
%PY% -m venv .venv
if errorlevel 1 goto nopython
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto failed

:run
".venv\Scripts\python.exe" run.py
pause
exit /b

:nopython
echo.
echo  Python was not found. Install it from https://www.python.org/downloads/
echo  and tick "Add python.exe to PATH" on the first screen of the installer.
echo  Then double-click start.bat again.
rmdir /s /q .venv 2>nul
pause
exit /b

:failed
echo.
echo  Installing the required packages failed - check your internet connection,
echo  then double-click start.bat again.
rmdir /s /q .venv 2>nul
pause
exit /b
