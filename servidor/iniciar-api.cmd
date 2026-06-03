@echo off
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel% neq 0 (
  echo.
  echo [ERROR] Python no esta instalado o no esta en el PATH.
  echo Instala Python 3.11+ desde https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

if not exist ".env" (
  echo Copiando .env desde .env.example ...
  copy /Y ".env.example" ".env" >nul
)

echo Instalando dependencias...
py -m pip install -r requirements.txt -q
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo PostgreSQL debe estar activo. Desde la raiz del proyecto:
echo   docker compose up -d db
echo.

echo Aplicando migraciones...
py -m alembic upgrade head
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo API en http://127.0.0.1:8000  (Swagger: /docs)
echo Admin: admin / Admin12345
echo.
py -m uvicorn aplicacion.principal:app --reload --host 127.0.0.1 --port 8000
