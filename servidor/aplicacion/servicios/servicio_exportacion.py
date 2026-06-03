from datetime import date
from io import BytesIO

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from openpyxl import Workbook
from sqlalchemy.orm import Session

from aplicacion.servicios.servicio_movimiento import list_movimientos_filtrados, movimiento_a_lista_out
from aplicacion.servicios.servicio_producto import list_productos


def export_productos_xlsx(db: Session) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"
    ws.append(["Codigo", "Nombre", "Descripcion", "Stock actual", "Stock minimo", "Precio"])
    for p in list_productos(db):
        ws.append(
            [
                p.codigo,
                p.nombre,
                p.descripcion or "",
                p.stock_actual,
                p.stock_minimo,
                float(p.precio) if p.precio is not None else "",
            ]
        )
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def export_movimientos_xlsx(
    db: Session,
    *,
    producto_id: int | None = None,
    tipo: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = 5000,
) -> BytesIO:
    rows = list_movimientos_filtrados(
        db,
        producto_id=producto_id,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"
    ws.append(
        [
            "ID",
            "Fecha",
            "Producto codigo",
            "Producto nombre",
            "Tipo",
            "Cantidad",
            "Usuario",
        ]
    )
    for m in rows:
        dto = movimiento_a_lista_out(m)
        ws.append(
            [
                dto.id,
                dto.fecha_movimiento.isoformat(),
                dto.producto_codigo or "",
                dto.producto_nombre or "",
                dto.tipo,
                dto.cantidad,
                dto.usuario_username,
            ]
        )
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def _pdf_safe(text: str) -> str:
    return text.encode("latin-1", errors="replace").decode("latin-1")


def export_movimientos_pdf(
    db: Session,
    *,
    producto_id: int | None = None,
    tipo: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = 500,
) -> BytesIO:
    rows = list_movimientos_filtrados(
        db,
        producto_id=producto_id,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0,
        10,
        _pdf_safe("Movimientos de inventario (Kardex)"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", size=7)
    col_w = [12, 32, 28, 45, 18, 14, 28]
    headers = ["ID", "Fecha", "Cod.", "Producto", "Tipo", "Cant.", "Usuario"]
    pdf.set_font("Helvetica", "B", 7)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, _pdf_safe(h), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", size=7)
    for m in rows:
        dto = movimiento_a_lista_out(m)
        line = [
            str(dto.id),
            dto.fecha_movimiento.strftime("%Y-%m-%d %H:%M"),
            dto.producto_codigo or "",
            (dto.producto_nombre or "")[:40],
            dto.tipo,
            str(dto.cantidad),
            dto.usuario_username[:18],
        ]
        for i, cell in enumerate(line):
            pdf.cell(col_w[i], 6, _pdf_safe(cell), border=1)
        pdf.ln()
    bio = BytesIO()
    pdf.output(bio)
    bio.seek(0)
    return bio
