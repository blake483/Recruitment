@echo off
rem Import a folder of CVs. Either drag the folder onto this file,
rem or double-click it and paste the folder path when asked.
title CV Search - import CVs
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Please double-click start.bat once first, so the app gets set up.
    pause
    exit /b
)

set "FOLDER=%~1"
if "%FOLDER%"=="" set /p "FOLDER=Paste the path of your CV folder, then press Enter: "
set "FOLDER=%FOLDER:"=%"

".venv\Scripts\python.exe" import_cvs.py "%FOLDER%"
pause
