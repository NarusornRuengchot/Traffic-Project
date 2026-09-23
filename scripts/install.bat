@echo off
title KU SRC Smart Traffic Setup
echo ===================================================
echo   KU SRC Smart Traffic Dashboard - Setup Utility
echo ===================================================
echo.

cd /d "%~dp0.."

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH.
    echo Please download and install Python ^(3.9 - 3.12 is recommended^).
    echo Make sure to check the box "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Get python version
for /f "tokens=2" %%i in ('python --version') do set pyver=%%i
echo Detected Python version: %pyver%

:: Check for Python 3.13 or higher (which can have issues compiling lapx without build tools)
echo %pyver% | findstr /r "^3\.13\." >nul
if %errorlevel% EQU 0 (
    echo.
    echo [WARNING] You are using Python 3.13.
    echo The dependency 'lapx' ^(needed for tracking^) may fail to install on Python 3.13
    echo unless you have "Microsoft C++ Build Tools" installed.
    echo If setup fails, we highly recommend using Python 3.12 instead.
    echo.
)

:: Create virtual environment if it doesn't exist
if exist v (
    echo Virtual environment ^(v^) already exists.
    goto venv_done
)

echo Creating virtual environment ^(v^)...
python -m venv v
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo Virtual environment created successfully.

:venv_done

echo.
echo Upgrading pip inside virtual environment...
v\Scripts\python.exe -m pip install --upgrade pip

echo.
echo Installing dependencies from backend\requirements.txt...
echo This might take a few minutes (downloading torch, ultralytics, streamlit)...
v\Scripts\python.exe -m pip install -r backend\requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ===================================================
    echo [ERROR] Dependency installation failed!
    echo ===================================================
    echo Common reasons:
    echo 1. Missing C++ Build Tools for 'lapx'.
    echo    To fix: Install Python 3.12 ^(highly recommended for compatibility^)
    echo    OR install Microsoft C++ Build Tools from:
    echo    https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo [SUCCESS] Setup completed successfully!
echo ===================================================
echo.
echo To run the React dashboard (FastAPI):
echo   cd backend ^&^& ..\v\Scripts\python.exe server.py
echo.
echo To run the legacy Streamlit dashboard:
echo   cd backend ^&^& ..\v\Scripts\python.exe -m streamlit run legacy\app.py
echo.
echo To run the legacy OpenCV Desktop app:
echo   cd backend ^&^& ..\v\Scripts\python.exe -m legacy.main
echo.
pause
