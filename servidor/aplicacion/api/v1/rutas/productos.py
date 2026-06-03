# Productos / Inventario
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user, require_admin
from aplicacion.nucleo.base_datos import get_db
from aplicacion.excepciones import (
    CategoriaNoEncontradaError,
    ProductoEnUsoError,
    ProductoNoEncontradoError,
    TipoProductoInvalidoError,
)
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.producto import ProductoCreate, ProductoImageUploadOut, ProductoOut, ProductoUpdate
from aplicacion.servicios.servicio_producto import (
    ImagenProductoInvalidaError,
    create_producto,
    delete_producto,
    get_producto,
    list_productos,
    save_producto_image,
    update_producto,
)

router = APIRouter(prefix="/productos", tags=["productos"])


@router.post("/upload-imagen", response_model=ProductoImageUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_producto_imagen(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    try:
        image_url = await save_producto_image(file)
    except ImagenProductoInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ProductoImageUploadOut(image_url=image_url)


@router.get("", response_model=list[ProductoOut])
def get_productos(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    q: str | None = Query(None, description="Buscar por codigo o nombre"),
):
    return list_productos(db, busqueda=q)


@router.get("/{producto_id}", response_model=ProductoOut)
def get_producto_por_id(
    producto_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    p = get_producto(db, producto_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return p


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def post_producto(
    payload: ProductoCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return create_producto(db, payload)
    except CategoriaNoEncontradaError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria no encontrada")
    except TipoProductoInvalidoError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de producto invalido")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un producto con ese codigo",
        )


@router.put("/{producto_id}", response_model=ProductoOut)
def put_producto(
    producto_id: int,
    payload: ProductoUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return update_producto(db, producto_id, payload)
    except ProductoNoEncontradoError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    except CategoriaNoEncontradaError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria no encontrada")
    except TipoProductoInvalidoError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de producto invalido")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe otro producto con ese codigo",
        )


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_producto_route(
    producto_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        delete_producto(db, producto_id)
    except ProductoNoEncontradoError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    except ProductoEnUsoError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: el producto tiene movimientos en el Kardex",
        )
