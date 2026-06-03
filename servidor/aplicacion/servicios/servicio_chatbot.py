from __future__ import annotations

import json
import logging
import os
import re
import threading
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib import error, request

from sqlalchemy import func
from sqlalchemy.orm import Session

from aplicacion.modelos.movimiento import Movimiento
from aplicacion.modelos.producto import Producto
from aplicacion.esquemas.chatbot import ChatbotHistorialItem
from aplicacion.servicios.servicio_producto import listar_alertas_stock

logger = logging.getLogger(__name__)

STOPWORDS = {
    "cuanto",
    "cuanta",
    "cuantos",
    "cuantas",
    "hay",
    "del",
    "de",
    "la",
    "el",
    "los",
    "las",
    "producto",
    "stock",
    "stok",
    "estok",
    "stokc",
    "estokc",
    "existencias",
    "precio",
    "proveedor",
    "categoria",
    "info",
    "informacion",
    "detalle",
    "tiene",
    "queda",
    "su",
    "ese",
    "esa",
    "mismo",
    "misma",
    "hoy",
    "ayer",
}

SALUDOS = ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey")
AGRADECIMIENTOS = ("gracias", "muchas gracias", "te pasaste", "genial")
INTENT_UNKNOWN = "unknown"

_SESSION_TTL_SECONDS = 30 * 60
_SESSION_LOCK = threading.Lock()
_SESSION_CONTEXT: dict[str, dict[str, Any]] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _purge_expired_sessions() -> None:
    now = _utcnow()
    expired_keys = [
        key for key, value in _SESSION_CONTEXT.items() if (now - value.get("updated_at", now)).total_seconds() > _SESSION_TTL_SECONDS
    ]
    for key in expired_keys:
        _SESSION_CONTEXT.pop(key, None)


def load_session_context(session_id: str, user_id: int) -> dict[str, Any]:
    with _SESSION_LOCK:
        _purge_expired_sessions()
        state = _SESSION_CONTEXT.get(session_id)
        if not state:
            return {}
        if state.get("user_id") != user_id:
            return {}
        return dict(state)


def save_session_context(session_id: str, user_id: int, **payload: Any) -> None:
    with _SESSION_LOCK:
        _purge_expired_sessions()
        current = _SESSION_CONTEXT.get(session_id, {})
        if current and current.get("user_id") != user_id:
            return
        merged = {**current, **payload}
        merged["user_id"] = user_id
        merged["updated_at"] = _utcnow()
        _SESSION_CONTEXT[session_id] = merged


def _build_trace_id() -> str:
    return f"cbt_{_utcnow().strftime('%Y%m%d%H%M%S%f')}"


def _allowed_intent(intent: str) -> str:
    allowed = {"stock", "movimientos", "producto", "proveedor", "alertas", "unknown"}
    return intent if intent in allowed else "unknown"


def _normalize(texto: str) -> str:
    normalized = unicodedata.normalize("NFKD", texto.lower().strip())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return value.replace(year=year, month=month, day=1)


def _resolve_date_range(texto: str) -> tuple[datetime, datetime, str]:
    today = datetime.now(timezone.utc).date()

    if "ayer" in texto:
        target = today - timedelta(days=1)
        return _start_of_day(target), _start_of_day(target + timedelta(days=1)), "ayer"
    if "hoy" in texto:
        return _start_of_day(today), _start_of_day(today + timedelta(days=1)), "hoy"
    if "esta semana" in texto:
        monday = today - timedelta(days=today.weekday())
        return _start_of_day(monday), _start_of_day(monday + timedelta(days=7)), "esta semana"
    if "este mes" in texto:
        start = _month_start(today)
        end = _add_months(start, 1)
        return _start_of_day(start), _start_of_day(end), "este mes"
    if "ultimos 7 dias" in texto or "ultimos siete dias" in texto:
        start = today - timedelta(days=6)
        return _start_of_day(start), _start_of_day(today + timedelta(days=1)), "los ultimos 7 dias"
    if "ultimos 30 dias" in texto or "ultimos treinta dias" in texto:
        start = today - timedelta(days=29)
        return _start_of_day(start), _start_of_day(today + timedelta(days=1)), "los ultimos 30 dias"

    for pattern in (r"(\d{4}-\d{2}-\d{2})", r"(\d{2}/\d{2}/\d{4})"):
        match = re.search(pattern, texto)
        if match:
            raw = match.group(1)
            try:
                target = (
                    datetime.strptime(raw, "%Y-%m-%d").date()
                    if "-" in raw
                    else datetime.strptime(raw, "%d/%m/%Y").date()
                )
                return _start_of_day(target), _start_of_day(target + timedelta(days=1)), target.strftime("%d/%m/%Y")
            except ValueError:
                break

    return _start_of_day(today), _start_of_day(today + timedelta(days=1)), "hoy"


def _extract_candidate(texto: str) -> str | None:
    patterns = [
        r"(?:stock|stok|estok|stokc|estokc|precio|proveedor|categoria|detalle|informacion|info)\s+(?:actual\s+)?(?:de|del|sobre|para)?\s+(.+)",
        r"(?:cuanto\s+(?:stock|stok|estok|stokc|estokc|queda|tiene)|cual\s+es\s+el\s+(?:precio|proveedor)|dame\s+el\s+(?:precio|proveedor))\s+(?:de|del)?\s*(.+)",
        r"(?:hablame|cuentame)\s+de\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, texto)
        if match:
            candidate = match.group(1).strip(" ?.!,")
            if candidate:
                return candidate
    return None


def _extract_intent_by_rules(texto: str) -> str:
    if any(token in texto for token in ("bajo stock", "alerta", "alertas", "stock bajo", "critico")):
        return "alertas"
    if any(token in texto for token in ("movimientos", "entradas", "salidas", "ingresaron", "salieron")):
        return "movimientos"
    if "proveedor" in texto:
        return "proveedor"
    if any(token in texto for token in ("stock", "stok", "estok", "stokc", "estokc", "disponible", "existencia", "existencias", "inventario")):
        return "stock"
    if any(token in texto for token in ("producto", "detalle", "precio", "categoria", "informacion")):
        return "producto"
    return INTENT_UNKNOWN


def _ai_enabled() -> bool:
    return os.getenv("AI_ENABLED", "false").lower() in {"1", "true", "yes"}


def _classify_with_ai(message: str) -> tuple[str, float]:
    if not _ai_enabled():
        return INTENT_UNKNOWN, 0.0
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return INTENT_UNKNOWN, 0.0
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    timeout = int(os.getenv("AI_TIMEOUT_SECONDS", "8"))
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Clasifica la intencion del usuario en inventario interno y responde JSON con intent y confidence. "
                    "Intent posibles: stock, movimientos, producto, proveedor, alertas, unknown."
                ),
            },
            {"role": "user", "content": message},
        ],
    }
    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return _allowed_intent(parsed.get("intent", INTENT_UNKNOWN)), float(parsed.get("confidence", 0.5))
    except (error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
        logger.exception("Error clasificando intencion con IA")
        return INTENT_UNKNOWN, 0.0


def _search_product(db: Session, texto: str, contexto_producto_id: int | None) -> Producto | None:
    lowered = _normalize(texto)
    candidate = _extract_candidate(lowered)

    if candidate:
        producto = (
            db.query(Producto)
            .filter(
                func.lower(Producto.nombre).like(f"%{candidate}%")
                | func.lower(Producto.codigo).like(f"%{candidate}%")
            )
            .order_by(Producto.nombre.asc())
            .first()
        )
        if producto is not None:
            return producto

    tokens = [token for token in re.findall(r"[a-z0-9\-]+", lowered) if token not in STOPWORDS and len(token) >= 3]
    for token in tokens:
        producto = (
            db.query(Producto)
            .filter(
                func.lower(Producto.nombre).like(f"%{token}%")
                | func.lower(Producto.codigo).like(f"%{token}%")
            )
            .order_by(Producto.nombre.asc())
            .first()
        )
        if producto is not None:
            return producto

    if contexto_producto_id and any(
        phrase in lowered
        for phrase in ("ese producto", "esa pieza", "ese", "esa", "su stock", "su precio", "su proveedor", "y de ese")
    ):
        return db.query(Producto).filter(Producto.id == contexto_producto_id).first()

    return None


def _friendly_product_detail(producto: Producto) -> str:
    proveedor = producto.proveedor.nombre if getattr(producto, "proveedor", None) else "sin proveedor asignado"
    categoria = producto.categoria.nombre if getattr(producto, "categoria", None) else "sin categoria"
    return (
        f"{producto.nombre} ({producto.codigo}) tiene {producto.stock_actual} unidades disponibles, "
        f"stock minimo de {producto.stock_minimo}, precio actual de S/ {float(producto.precio):.2f}, "
        f"categoria {categoria} y proveedor {proveedor}."
    )


def _sumar_ventas(db: Session, inicio: datetime, fin: datetime) -> tuple[float, int]:
    row = (
        db.query(
            func.coalesce(func.sum(Movimiento.cantidad * Producto.precio), 0),
            func.coalesce(func.sum(Movimiento.cantidad), 0),
        )
        .join(Producto, Producto.id == Movimiento.producto_id)
        .filter(Movimiento.tipo == "salida", Movimiento.fecha_movimiento >= inicio, Movimiento.fecha_movimiento < fin)
        .first()
    )
    total_monto, total_unidades = row or (0, 0)
    return float(total_monto or 0), int(total_unidades or 0)


def responder_consulta_inventario(
    db: Session,
    pregunta: str,
    *,
    historial: list[ChatbotHistorialItem] | None = None,
    contexto_producto_id: int | None = None,
    contexto_producto_nombre: str | None = None,
) -> tuple[str, str, float, int | None, str | None]:
    del historial
    texto = pregunta.strip()
    lowered = _normalize(texto)

    if any(token in lowered for token in SALUDOS):
        return (
            "Hola. Estoy listo para ayudarte con inventario, ventas, productos y movimientos. Dime que necesitas revisar.",
            "saludo",
            0.98,
            contexto_producto_id,
            contexto_producto_nombre,
        )

    if any(token in lowered for token in AGRADECIMIENTOS):
        return (
            "De nada. Si quieres seguimos revisando stock, ventas o movimientos.",
            "agradecimiento",
            0.99,
            contexto_producto_id,
            contexto_producto_nombre,
        )

    if any(token in lowered for token in ("bajo stock", "faltante", "alerta", "alertas")):
        alertas = listar_alertas_stock(db, limit=6)
        if not alertas:
            return "Todo esta en rango por ahora. No hay productos bajo stock.", "alertas_stock", 0.95, None, None
        detalle = "; ".join(f"{p.nombre}: {p.stock_actual}/{p.stock_minimo}" for p in alertas)
        return f"Estos son los productos mas comprometidos: {detalle}.", "alertas_stock", 0.94, None, None

    if any(token in lowered for token in ("mas vendidos", "top vendidos", "top 5", "top cinco")):
        rows = (
            db.query(
                Producto.id,
                Producto.nombre,
                Producto.codigo,
                func.coalesce(func.sum(Movimiento.cantidad), 0).label("total"),
            )
            .join(Movimiento, Movimiento.producto_id == Producto.id)
            .filter(Movimiento.tipo == "salida")
            .group_by(Producto.id, Producto.nombre, Producto.codigo)
            .order_by(func.coalesce(func.sum(Movimiento.cantidad), 0).desc(), Producto.nombre.asc())
            .limit(5)
            .all()
        )
        if not rows:
            return "Todavia no hay salidas registradas para armar un top de vendidos.", "top_productos", 0.9, None, None
        detalle = "; ".join(f"{nombre} ({codigo}) con {int(total)} uds." for _, nombre, codigo, total in rows)
        return f"Los productos mas vendidos hasta ahora son: {detalle}.", "top_productos", 0.92, None, None

    if any(token in lowered for token in ("vendio", "ventas", "monto vendido", "facturo", "facturacion")):
        inicio, fin, etiqueta = _resolve_date_range(lowered)
        total_monto, total_unidades = _sumar_ventas(db, inicio, fin)
        return (
            f"En {etiqueta} se registraron ventas estimadas por S/ {total_monto:.2f} sobre {total_unidades} unidades despachadas.",
            "ventas_periodo",
            0.91,
            None,
            None,
        )

    if any(token in lowered for token in ("ingresaron", "entraron", "entradas", "salieron", "salidas", "movimientos")):
        inicio, fin, etiqueta = _resolve_date_range(lowered)
        tipo = None
        if any(token in lowered for token in ("ingresaron", "entraron", "entradas")):
            tipo = "entrada"
        elif any(token in lowered for token in ("salieron", "salidas")):
            tipo = "salida"

        query = db.query(func.count(Movimiento.id), func.coalesce(func.sum(Movimiento.cantidad), 0)).filter(
            Movimiento.fecha_movimiento >= inicio,
            Movimiento.fecha_movimiento < fin,
        )
        if tipo:
            query = query.filter(Movimiento.tipo == tipo)
        total_movimientos, total_unidades = query.first() or (0, 0)
        if tipo == "entrada":
            verbo = "ingresaron"
        elif tipo == "salida":
            verbo = "salieron"
        else:
            verbo = "se movieron"
        return (
            f"En {etiqueta} {verbo} {int(total_unidades or 0)} unidades en {int(total_movimientos or 0)} movimientos.",
            "movimientos_periodo",
            0.9,
            None,
            None,
        )

    if any(token in lowered for token in ("cuantos productos", "total de productos", "resumen", "panorama")):
        total_productos = db.query(func.count(Producto.id)).scalar() or 0
        total_stock = db.query(func.coalesce(func.sum(Producto.stock_actual), 0)).scalar() or 0
        bajo_stock = len(listar_alertas_stock(db, limit=5))
        return (
            f"Ahora mismo tienes {int(total_productos)} productos registrados, {int(total_stock)} unidades en stock total y {int(bajo_stock)} alertas de stock bajo.",
            "resumen_inventario",
            0.9,
            None,
            None,
        )

    if any(token in lowered for token in ("stock", "stok", "estok", "stokc", "estokc", "existencias", "precio", "proveedor", "categoria", "detalle", "informacion", "info")):
        producto = _search_product(db, texto, contexto_producto_id)
        if producto is None:
            return (
                "No logre identificar el producto que quieres revisar. Mencioname su nombre o su codigo y lo busco.",
                "producto_no_encontrado",
                0.55,
                contexto_producto_id,
                contexto_producto_nombre,
            )

        if "proveedor" in lowered:
            proveedor = producto.proveedor.nombre if getattr(producto, "proveedor", None) else "sin proveedor asignado"
            return (
                f"El proveedor de {producto.nombre} es {proveedor}.",
                "detalle_producto",
                0.93,
                producto.id,
                producto.nombre,
            )

        if "precio" in lowered:
            return (
                f"El precio actual de {producto.nombre} es S/ {float(producto.precio):.2f}.",
                "detalle_producto",
                0.94,
                producto.id,
                producto.nombre,
            )

        if "categoria" in lowered:
            categoria = producto.categoria.nombre if getattr(producto, "categoria", None) else "sin categoria"
            return (
                f"{producto.nombre} esta en la categoria {categoria}.",
                "detalle_producto",
                0.93,
                producto.id,
                producto.nombre,
            )

        if any(token in lowered for token in ("stock", "stok", "estok", "stokc", "estokc", "existencia", "existencias")) or contexto_producto_id == producto.id:
            return (
                f"Claro. {producto.nombre} tiene stock actual de {producto.stock_actual} unidades y su minimo configurado es {producto.stock_minimo}.",
                "stock_producto",
                0.96,
                producto.id,
                producto.nombre,
            )

        return _friendly_product_detail(producto), "detalle_producto", 0.92, producto.id, producto.nombre

    if contexto_producto_id is not None and any(token in lowered for token in ("y de ese", "y de esa", "y cuanto", "y su")):
        producto = db.query(Producto).filter(Producto.id == contexto_producto_id).first()
        if producto is not None:
            return (
                _friendly_product_detail(producto),
                "detalle_producto",
                0.88,
                producto.id,
                producto.nombre,
            )

    total_productos = db.query(func.count(Producto.id)).scalar() or 0
    return (
        f"Puedo ayudarte con productos, stock, ventas y movimientos. En este momento hay {int(total_productos)} productos cargados.",
        "ayuda_general",
        0.7,
        contexto_producto_id,
        contexto_producto_nombre,
    )


def _search_product_options(db: Session, texto: str, limit: int = 5) -> list[Producto]:
    lowered = _normalize(texto)
    candidate = _extract_candidate(lowered) or lowered
    if not candidate:
        return []
    return (
        db.query(Producto)
        .filter(func.lower(Producto.nombre).like(f"%{candidate}%") | func.lower(Producto.codigo).like(f"%{candidate}%"))
        .order_by(Producto.nombre.asc())
        .limit(limit)
        .all()
    )


def procesar_mensaje_chatbot(
    db: Session,
    *,
    message: str,
    session_id: str,
    user_id: int,
    historial: list[ChatbotHistorialItem] | None = None,
    contexto_producto_id: int | None = None,
    contexto_producto_nombre: str | None = None,
) -> dict[str, Any]:
    trace_id = _build_trace_id()
    session_state = load_session_context(session_id=session_id, user_id=user_id)
    contexto_producto_id = contexto_producto_id or session_state.get("last_producto_id")
    contexto_producto_nombre = contexto_producto_nombre or session_state.get("last_producto_nombre")
    normalized = _normalize(message)
    intent = _extract_intent_by_rules(normalized)
    confidence = 0.85 if intent != INTENT_UNKNOWN else 0.4

    if intent == INTENT_UNKNOWN:
        ai_intent, ai_conf = _classify_with_ai(message)
        if ai_intent != INTENT_UNKNOWN:
            intent = ai_intent
            confidence = ai_conf

    options: list[dict[str, Any]] = []
    if intent in {"stock", "producto", "proveedor"}:
        options_rows = _search_product_options(db, message)
        if len(options_rows) > 1 and not contexto_producto_id:
            options = [{"id": row.id, "label": f"{row.nombre} ({row.codigo})"} for row in options_rows]
            save_session_context(
                session_id,
                user_id,
                last_options_presented=options,
                last_intent=intent,
                last_user_message=message,
            )
            return {
                "status": "need_clarification",
                "intent": intent,
                "answer": "Se encontraron multiples productos. Selecciona una opcion para continuar.",
                "data": None,
                "options": options,
                "confidence": confidence,
                "trace_id": trace_id,
                "session_id": session_id,
                "contexto_producto_id": contexto_producto_id,
                "contexto_producto_nombre": contexto_producto_nombre,
            }

    respuesta, resolved_intent, resolved_conf, product_id, product_name = responder_consulta_inventario(
        db,
        message,
        historial=historial,
        contexto_producto_id=contexto_producto_id,
        contexto_producto_nombre=contexto_producto_nombre,
    )

    status = "ok"
    if "No logre identificar" in respuesta:
        status = "need_clarification"
    if "No pude" in respuesta:
        status = "error"

    data: dict[str, Any] | None = None
    if product_id:
        producto = db.query(Producto).filter(Producto.id == product_id).first()
        if producto:
            estado = "OK"
            if producto.stock_actual <= 0:
                estado = "Sin stock"
            elif producto.stock_actual < producto.stock_minimo:
                estado = "Bajo"
            data = {
                "producto_id": producto.id,
                "producto_nombre": producto.nombre,
                "stock_actual": int(producto.stock_actual),
                "stock_minimo": int(producto.stock_minimo),
                "estado": estado,
            }

    save_session_context(
        session_id,
        user_id,
        last_intent=resolved_intent,
        last_producto_id=product_id,
        last_producto_nombre=product_name,
        last_trace_id=trace_id,
        last_user_message=message,
    )

    return {
        "status": status,
        "intent": _allowed_intent(intent if intent != INTENT_UNKNOWN else resolved_intent),
        "answer": respuesta,
        "data": data,
        "options": options,
        "confidence": float(resolved_conf if resolved_conf else confidence),
        "trace_id": trace_id,
        "session_id": session_id,
        "contexto_producto_id": product_id,
        "contexto_producto_nombre": product_name,
    }


def resolver_opcion_chatbot(db: Session, *, session_id: str, user_id: int, selected_option_id: int) -> dict[str, Any]:
    state = load_session_context(session_id=session_id, user_id=user_id)
    presented = state.get("last_options_presented", [])
    if not any(int(option["id"]) == selected_option_id for option in presented):
        return {
            "status": "error",
            "intent": "unknown",
            "answer": "La opcion seleccionada no es valida para la sesion actual.",
            "data": None,
            "options": [],
            "confidence": 1.0,
            "trace_id": _build_trace_id(),
            "session_id": session_id,
            "contexto_producto_id": state.get("last_producto_id"),
            "contexto_producto_nombre": state.get("last_producto_nombre"),
        }
    producto = db.query(Producto).filter(Producto.id == selected_option_id).first()
    if not producto:
        return {
            "status": "error",
            "intent": "unknown",
            "answer": "No se encontro el producto seleccionado.",
            "data": None,
            "options": [],
            "confidence": 1.0,
            "trace_id": _build_trace_id(),
            "session_id": session_id,
            "contexto_producto_id": state.get("last_producto_id"),
            "contexto_producto_nombre": state.get("last_producto_nombre"),
        }

    consulta = f"stock de {producto.nombre}"
    return procesar_mensaje_chatbot(
        db,
        message=consulta,
        session_id=session_id,
        user_id=user_id,
        contexto_producto_id=producto.id,
        contexto_producto_nombre=producto.nombre,
    )


def listar_sugerencias_chatbot() -> list[dict[str, str]]:
    return [
        {"id": "stock", "label": "Consultar stock"},
        {"id": "movimientos_30d", "label": "Movimientos ultimos 30 dias"},
        {"id": "alertas", "label": "Productos con stock bajo"},
        {"id": "proveedor", "label": "Buscar proveedor"},
    ]
