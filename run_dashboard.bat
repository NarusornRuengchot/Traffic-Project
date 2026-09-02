@echo off
title KU SRC Smart Traffic Dashboard
echo ========================================================
echo   Starting KU SRC Smart Traffic React Dashboard...
echo ========================================================
echo.

if exist .venv\Scripts\python.exe (
    set PYTHON_EXEC=.venv\Scripts\python.exe
) else (
    set PYTHON_EXEC=python
)

echo Using Python: %PYTHON_EXEC%
echo.
echo Opening browser at http://localhost:8000 ...
start "" http://localhost:8000

%PYTHON_EXEC% server.py
pause
