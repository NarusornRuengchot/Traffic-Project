@echo off
set "PROJECT_DIR=C:\Users\takt\Desktop\IP-BOB\Traffic-Project"
set "BACKEND_DIR=%PROJECT_DIR%\backend"

start "KU SRC Backend" cmd /k "cd /d %BACKEND_DIR% && python server.py"

echo Local Backend is starting.
echo Open the local frontend at http://localhost:5173
pause
