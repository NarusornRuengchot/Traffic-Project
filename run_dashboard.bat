@echo off
set "PROJECT_DIR=C:\Users\takt\Desktop\IP-BOB\Traffic-Project"

start "KU SRC Backend" cmd /k "cd /d %PROJECT_DIR%\backend && python server.py"
timeout /t 3 /nobreak >nul
start "KU SRC Frontend" cmd /k "cd /d %PROJECT_DIR%\frontend && npm run dev"

echo Local dashboard is starting.
echo Open http://localhost:5173
pause
