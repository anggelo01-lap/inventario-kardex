import logging
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from aplicacion.api.v1.rutas import autenticacion, categorias, chatbot, clientes, tablero, exportacion, salud, movimientos, productos, proveedores, usuarios
from aplicacion.modelos import categoria as _categoria_model  # noqa: F401
from aplicacion.modelos import cliente as _cliente_model  # noqa: F401
from aplicacion.modelos import movimiento as _movimiento_model  # noqa: F401
from aplicacion.modelos import producto as _producto_model  # noqa: F401
from aplicacion.modelos import proveedor as _proveedor_model  # noqa: F401
from aplicacion.modelos import usuario as _user_model  # noqa: F401
from aplicacion.nucleo.configuracion import get_settings
from aplicacion.nucleo.base_datos import SessionLocal
from aplicacion.servicios.servicio_inicializacion import seed_admin_user, bootstrap_demo_data

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)
settings.media_root_path.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando datos de prueba...")
    db = SessionLocal()
    try:
        seed_admin_user(
            db,
            username=settings.admin_username,
            email=settings.admin_email,
            full_name=settings.admin_full_name,
            password=settings.admin_password,
        )
        bootstrap_demo_data(db)
        logger.info("Datos de prueba inicializados correctamente!")
    except Exception as e:
        logger.error(f"Error al inicializar datos: {e}")
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "Request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    status_code = 400 if request.url.path.rstrip("/").endswith("/auth/registro") else 422
    return JSONResponse(status_code=status_code, content={"detail": exc.errors()})


if not settings.app_debug:

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, (HTTPException, RequestValidationError)):
            raise exc
        logger.exception(
            "Error no manejado",
            extra={"request_id": getattr(request.state, "request_id", None)},
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor."},
        )


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    schemes = openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    if "HTTPBearer" in schemes:
        schemes["HTTPBearer"]["description"] = "Token JWT obtenido en POST /api/v1/auth/login"
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.mount(
    settings.media_url_prefix,
    StaticFiles(directory=str(settings.media_root_path)),
    name="subidas",
)

app.include_router(salud.router, prefix="/api/v1")
app.include_router(autenticacion.router, prefix="/api/v1")
app.include_router(categorias.router, prefix="/api/v1")
app.include_router(proveedores.router, prefix="/api/v1")
app.include_router(clientes.router, prefix="/api/v1")
app.include_router(productos.router, prefix="/api/v1")
app.include_router(movimientos.router, prefix="/api/v1")
app.include_router(tablero.router, prefix="/api/v1")
app.include_router(exportacion.router, prefix="/api/v1")
app.include_router(usuarios.router, prefix="/api/v1")
app.include_router(chatbot.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
