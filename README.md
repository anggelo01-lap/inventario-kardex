# Sistema de Inventario con Kardex

Arquitectura base profesional para un sistema de inventario con trazabilidad de movimientos (Kardex), preparada para desarrollo, despliegue en la nube y crecimiento por modulos.

## Stack Tecnologico

- Backend: Python + FastAPI
- Frontend: Angular + Angular Material
- Base de datos: **PostgreSQL** (unico motor soportado)
- ORM: SQLAlchemy
- Migraciones: Alembic
- Autenticacion: JWT
- Contenedores: Docker Compose

## Estado actual

El proyecto ya cuenta con:

- inventario con categorias, productos, movimientos y tablero,
- autenticacion JWT y administracion de usuarios,
- exportaciones restringidas por rol,
- healthcheck con verificacion real de base de datos,
- logging basico por request con `X-Request-ID`,
- validaciones y restricciones de integridad en base de datos,
- suite backend automatizada con cobertura funcional e integridad.

## Estructura del Proyecto

```text
inventario-kardex/
|-- servidor/                 (API FastAPI)
|   |-- alembic/
|   |-- aplicacion/
|   |-- pruebas/
|   |-- scripts/
|   |-- subidas/
|   |-- .env.example
|   `-- requirements.txt
|-- interfaz/                 (Angular)
|-- base-datos/init/
|-- docker-compose.yml
`-- README.md
```

## Inicio Rapido

### 1) PostgreSQL

Levantar la base de datos con Docker (recomendado):

```bash
docker compose up -d db
```

Configurar variables del backend:

```bash
cd servidor
copy .env.example .env
py -m pip install -r requirements.txt
py -m alembic upgrade head
```

La URL por defecto en `.env.example` es:

`postgresql+psycopg2://postgres:7721@localhost:5432/inventario_kardex`

Debe coincidir con la contraseña de `POSTGRES_PASSWORD` en `docker-compose.yml`.

### 2) Backend

```bash
cd servidor
iniciar-api.cmd
```

O manualmente:

```bash
py -m uvicorn aplicacion.principal:app --reload --host 127.0.0.1 --port 8000
```

### 3) Frontend

```bash
cd interfaz
npm install
npm start
```

Desde la raiz del proyecto tambien puedes usar `iniciar-proyecto.cmd` (API + Angular).

### 4) Admin inicial

En cada arranque del servidor se crea o actualiza el admin definido en `.env` (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, etc.).

## Variables de entorno

Archivo: `servidor/.env` (plantilla: `servidor/.env.example`)

| Variable | Descripcion |
|----------|-------------|
| `DATABASE_URL` | URL PostgreSQL (`postgresql+psycopg2://...`) |
| `SECRET_KEY` | Clave JWT |
| `BACKEND_CORS_ORIGINS` | Origenes del frontend |
| `ADMIN_*` | Usuario administrador inicial |

**No se usa SQLite.** Si existe `servidor/.env.local` con una URL `sqlite://`, eliminalo o actualizalo a PostgreSQL.

## Migrar a Neon (PostgreSQL en la nube)

1. Crea un proyecto en [Neon](https://neon.tech) y copia la **connection string**.
2. En el dashboard elige **Pooled connection** (recomendado para la API).
3. Edita `servidor/.env` y pega la URL. Formato:

```env
DATABASE_URL=postgresql+psycopg2://usuario:clave@ep-xxxx-pooler.region.aws.neon.tech/neondb?sslmode=require
```

Tambien puedes partir de `servidor/.env.neon.example`.

4. Crear tablas en Neon:

```bash
cd servidor
py scripts/preparar_neon.py
```

5. **Opcional** — copiar datos desde tu PostgreSQL local:

```bash
py scripts/copiar_bd_local_a_neon.py
```

6. Reinicia la API (`iniciar-api.cmd`) y verifica `GET /api/v1/health`.

En pgAdmin ya no veras la base local como principal: los datos viven en Neon. Puedes conectar pgAdmin usando el mismo host/usuario/clave de Neon (SSL requerido).

## Pruebas automatizadas

Requiere PostgreSQL. Base de pruebas por defecto: `inventario_kardex_test`.

```bash
docker compose up -d db
# Crear la base de pruebas (una vez)
docker exec -it inventario_db psql -U postgres -c "CREATE DATABASE inventario_kardex_test;"
cd servidor
set TEST_DATABASE_URL=postgresql+psycopg2://postgres:7721@localhost:5432/inventario_kardex_test
py -m pytest -q
```

En CI (GitHub Actions) PostgreSQL se levanta automaticamente como servicio.

## Verificaciones rapidas

- Swagger: `http://127.0.0.1:8000/docs`
- Health: `GET /api/v1/health`
- Login JWT: `POST /api/v1/auth/login`

## Reglas funcionales implementadas

- `entrada` suma stock.
- `salida` resta stock solo si hay disponibilidad.
- `ajuste` reemplaza stock.
- La base rechaza stock, precio o cantidades invalidas.
- Exportaciones y administracion de usuarios requieren rol `admin`.

## Checklist de puesta en marcha

1. `docker compose up -d db`
2. Configurar `servidor/.env` desde `.env.example`
3. `py -m alembic upgrade head`
4. Levantar backend y frontend
5. Probar login, producto, movimiento y `GET /api/v1/health`
