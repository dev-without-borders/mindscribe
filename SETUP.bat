@echo off
title Setup Check for mindscribe
cls

echo --- Start System-Check ---

REM 1. Check Python Installation
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH-Variable!
    echo Please make sure Python is installed and 'Add to PATH' was checked during installation.
    pause
    exit /b
)

REM 2. Display Python Version
echo Found Python installation:
python --version
echo Pfad:
where python
echo.

REM 3. (Optional) Info if a VENV should be used
if exist .venv (
    echo [INFO] A '.venv' folder was found.
    echo If you want to run this script within the virtual environment,
    echo please launch it from the activated console or modify the .bat file.
    echo Currently, the GLOBAL Python or the active environment is being used.
    echo.
)

REM 4. Start Python Setup Check Script
python check_setup.py

pause
