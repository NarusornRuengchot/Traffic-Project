@echo off
title KU SRC Smart Traffic Dashboard
echo ========================================================
echo   Starting KU SRC Smart Traffic React Dashboard...
echo ========================================================
echo.

cd /d "%~dp0.."

if exist .venv\Scripts\python.exe (
    set PYTHON_EXEC=%CD%\.venv\Scripts\python.exe
) else (
    set PYTHON_EXEC=python
)

echo Using Python: %PYTHON_EXEC%
echo.
echo Opening browser at http://localhost:8000 ...
start "" http://localhost:8000

cd backend
"%PYTHON_EXEC%" server.py
pause
