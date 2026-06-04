# Movimientos / Kardex
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user
from aplicacion.nucleo.base_datos import get_db
from aplicacion.excepciones import (
    CantidadInvalidaError,
    ProductoNoEncontradoError,
    StockInsuficienteError,
    TipoMovimientoInvalidoError,
)
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.movimiento import MovimientoCreate, MovimientoListaOut, MovimientoOut, MovimientoPaginaOut
from aplicacion.servicios.servicio_movimiento import (
    list_movimientos_como_dto,
    list_movimientos_paginados_como_dto,
    registrar_movimiento,
)

router = APIRouter(prefix="/movimientos", tags=["movimientos"])


@router.get("", response_model=list[MovimientoListaOut])
def list_movimientos(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    producto_id: int | None = Query(None, description="Filtrar por producto"),
    tipo: str | None = Query(None, description="entrada | salida | ajuste"),
    q: str | None = Query(None, description="Buscar por codigo o nombre"),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    limit: int = Query(500, ge=1, le=2000),
):
    return list_movimientos_como_dto(
        db,
        producto_id=producto_id,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        busqueda=q,
        limit=limit,
    )


@router.get("/paginado", response_model=MovimientoPaginaOut)
def list_movimientos_paginados(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    producto_id: int | None = Query(None, description="Filtrar por producto"),
    tipo: str | None = Query(None, description="entrada | salida | ajuste"),
    q: str | None = Query(None, description="Buscar por codigo o nombre"),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
):
    return list_movimientos_paginados_como_dto(
        db,
        producto_id=producto_id,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        busqueda=q,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
def post_movimiento(
    payload: MovimientoCreate,
    db: Session = Depends(get_db),
    usuario_actual: User = Depends(get_current_user),
):
    try:
        return registrar_movimiento(db, usuario_actual.id, payload)
    except ProductoNoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    except StockInsuficienteError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock insuficiente",
        )
    except TipoMovimientoInvalidoError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de movimiento invalido",
        )
    except CantidadInvalidaError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cantidad debe ser mayor que cero",
        )
