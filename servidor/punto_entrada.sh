#!/bin/sh
set -e

echo "=========================================="
echo " El Mundo del Carguero — Backend Startup"
echo "=========================================="

# 1. Ejecutar migraciones Alembic (crea todas las tablas)
echo "[1/3] Aplicando migraciones de base de datos..."
alembic upgrade head
echo "      Migraciones OK"

# 2. Crear/actualizar usuario admin inicial
echo "[2/3] Inicializando usuario admin..."
python scripts/semilla_admin.py \
  --username "${ADMIN_USERNAME:-admin}" \
  --email    "${ADMIN_EMAIL:-admin@carguero.com}" \
  --full-name "${ADMIN_FULL_NAME:-Administrador}" \
  --password "${ADMIN_PASSWORD:-Admin12345}"
echo "      Admin OK"

# 3. Iniciar servidor FastAPI
echo "[3/3] Iniciando servidor API..."
exec uvicorn aplicacion.principal:app --host 0.0.0.0 --port 8000
