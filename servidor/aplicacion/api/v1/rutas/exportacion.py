from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import require_admin
from aplicacion.nucleo.base_datos import get_db
from aplicacion.modelos.usuario import User
from aplicacion.servicios.servicio_exportacion import (
    export_movimientos_pdf,
    export_movimientos_xlsx,
    export_productos_xlsx,
)

router = APIRouter(prefix="/export", tags=["exportacion"])


@router.get("/productos.xlsx")
def export_productos_excel(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    bio = export_productos_xlsx(db)
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="productos.xlsx"'},
    )


@router.get("/movimientos.xlsx")
def export_movimientos_excel(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    producto_id: int | None = Query(None),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    limit: int = Query(5000, ge=1, le=10000),
):
    bio = export_movimientos_xlsx(
        db,
        producto_id=producto_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="movimientos.xlsx"'},
    )


@router.get("/movimientos.pdf")
def export_movimientos_pdf_route(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    producto_id: int | None = Query(None),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    limit: int = Query(500, ge=1, le=2000),
):
    bio = export_movimientos_pdf(
        db,
        producto_id=producto_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )
    return StreamingResponse(
        bio,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="movimientos.pdf"'},
    )
