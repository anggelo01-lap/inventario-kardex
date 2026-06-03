from fastapi import APIRouter, HTTPException, status

from aplicacion.nucleo.configuracion import get_settings
from aplicacion.nucleo.base_datos import ping_db
from aplicacion.esquemas.salud import HealthOut

router = APIRouter(prefix="/health", tags=["salud"])

settings = get_settings()


@router.get("", response_model=HealthOut)
def health_check() -> HealthOut:
    try:
        ping_db()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "estado": "degradado",
                "database": "error",
                "app_env": settings.app_env,
            },
        ) from exc
    return HealthOut(
        estado="activo",
        database="ok",
        app_env=settings.app_env,
    )
