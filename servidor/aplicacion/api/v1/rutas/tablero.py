# Tablero
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user
from aplicacion.nucleo.base_datos import get_db
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.dashboard import DashboardResumenOut
from aplicacion.servicios.servicio_tablero import resumen_dashboard

router = APIRouter(prefix="/tablero", tags=["dashboard"])


@router.get("/resumen", response_model=DashboardResumenOut)
def get_resumen(
    periodo: Literal["all", "7d", "30d", "12m", "today"] = Query("all"),
    agrupar_por: Literal["auto", "dia", "mes"] = Query("auto"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return resumen_dashboard(db, periodo=periodo, agrupar_por=agrupar_por)
