@echo off
title Wireless Phone-to-Laptop File Transfer
color 0b

echo ===================================================
echo     Starting Wireless File Transfer Server
echo ===================================================
echo.

cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.x from https://www.python.org/
    pause
    exit /b 1
)

:: Run the master server
python server.py

pause
