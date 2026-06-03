@echo off
set ROOT=%~dp0
echo Abriendo API y Angular en ventanas separadas...
start "Inventario - API" cmd /k "%ROOT%servidor\iniciar-api.cmd"
timeout /t 3 /nobreak >nul
start "Inventario - Interfaz" cmd /k "cd /d \"%ROOT%interfaz\" && npm start"
echo.
echo Interfaz: http://localhost:4200
echo API:     http://127.0.0.1:8000/docs
echo.
