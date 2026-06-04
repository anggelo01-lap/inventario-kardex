from __future__ import annotations

import json
import logging
import os
import random
import re
import threading
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib import error, request

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from aplicacion.modelos.categoria import Categoria
from aplicacion.modelos.cliente import Cliente
from aplicacion.modelos.movimiento import Movimiento
from aplicacion.modelos.producto import Producto
from aplicacion.modelos.proveedor import Proveedor
from aplicacion.esquemas.chatbot import ChatbotHistorialItem
from aplicacion.servicios.servicio_producto import listar_alertas_stock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vocabulario extendido
# ---------------------------------------------------------------------------

STOPWORDS = {
    "cuanto", "cuanta", "cuantos", "cuantas", "hay", "del", "de", "la", "el",
    "los", "las", "un", "una", "unos", "unas", "producto", "stock", "stok",
    "estok", "stokc", "estokc", "existencias", "precio", "proveedor",
    "categoria", "info", "informacion", "detalle", "tiene", "queda", "su",
    "ese", "esa", "mismo", "misma", "hoy", "ayer", "por", "para", "con",
    "que", "cual", "como", "fue", "son", "ser", "esta", "estan", "este",
    "estos", "estas", "todo", "todos", "toda", "todas", "mas", "menos",
    "muy", "mucho", "mucha", "muchos", "muchas", "algo", "algun", "alguna",
    "cada", "otro", "otra", "otros", "otras", "donde", "cuando", "dame",
    "dime", "muestrame", "dinos", "nos", "me", "te", "se", "ver", "quiero",
    "necesito", "puedes", "puede", "podrias", "favor", "total", "actual",
}

SALUDOS = (
    "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    "hey", "que tal", "saludos", "buenas buenas",
)

AGRADECIMIENTOS = (
    "gracias", "muchas gracias", "te pasaste", "genial", "excelente",
    "perfecto", "ok gracias", "vale gracias", "chevere", "thanks",
)

DESPEDIDAS = (
    "adios", "chau", "hasta luego", "nos vemos", "bye", "chao",
    "hasta pronto", "me voy",
)

INTENT_UNKNOWN = "unknown"

_SESSION_TTL_SECONDS = 30 * 60
_SESSION_LOCK = threading.Lock()
_SESSION_CONTEXT: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Utilidades de sesión
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _purge_expired_sessions() -> None:
    now = _utcnow()
    expired_keys = [
        key for key, value in _SESSION_CONTEXT.items()
        if (now - value.get("updated_at", now)).total_seconds() > _SESSION_TTL_SECONDS
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


# ---------------------------------------------------------------------------
# Normalización y parsing
# ---------------------------------------------------------------------------

_ALLOWED_INTENTS = {
    "stock", "movimientos", "producto", "proveedor", "alertas", "unknown",
    "kardex", "valor_inventario", "categorias", "clientes", "rotacion",
    "ayuda", "comparacion", "ventas", "top_productos", "resumen",
}


def _allowed_intent(intent: str) -> str:
    return intent if intent in _ALLOWED_INTENTS else "unknown"


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
    if "semana pasada" in texto:
        monday = today - timedelta(days=today.weekday() + 7)
        return _start_of_day(monday), _start_of_day(monday + timedelta(days=7)), "la semana pasada"
    if "este mes" in texto or "mes actual" in texto:
        start = _month_start(today)
        end = _add_months(start, 1)
        return _start_of_day(start), _start_of_day(end), "este mes"
    if "mes pasado" in texto or "mes anterior" in texto:
        start = _add_months(_month_start(today), -1)
        end = _month_start(today)
        return _start_of_day(start), _start_of_day(end), "el mes pasado"
    if "ultimos 7 dias" in texto or "ultimos siete dias" in texto:
        start = today - timedelta(days=6)
        return _start_of_day(start), _start_of_day(today + timedelta(days=1)), "los ultimos 7 dias"
    if "ultimos 30 dias" in texto or "ultimos treinta dias" in texto:
        start = today - timedelta(days=29)
        return _start_of_day(start), _start_of_day(today + timedelta(days=1)), "los ultimos 30 dias"
    if "ultimos 90 dias" in texto:
        start = today - timedelta(days=89)
        return _start_of_day(start), _start_of_day(today + timedelta(days=1)), "los ultimos 90 dias"
    if "este ano" in texto or "este anio" in texto:
        start = today.replace(month=1, day=1)
        return _start_of_day(start), _start_of_day(today + timedelta(days=1)), "este año"

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
        r"(?:kardex|stock|stok|estok|stokc|estokc|precio|proveedor|categoria|detalle|informacion|info|rotacion|movimientos?)\s+(?:actual\s+)?(?:de|del|sobre|para)?\s+(.+)",
        r"(?:cuanto\s+(?:stock|stok|estok|stokc|estokc|queda|tiene)|cual\s+es\s+el\s+(?:precio|proveedor)|dame\s+el\s+(?:precio|proveedor|kardex))\s+(?:de|del)?\s*(.+)",
        r"(?:hablame|cuentame|dime)\s+(?:de|sobre|del)\s+(.+)",
        r"(?:ultimo\s+movimiento|ultima\s+entrada|ultima\s+salida)\s+(?:de|del)?\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, texto)
        if match:
            candidate = match.group(1).strip(" ?.!,")
            if candidate:
                return candidate
    return None


# ---------------------------------------------------------------------------
# Intent classifier (reglas expandidas)
# ---------------------------------------------------------------------------

def _extract_intent_by_rules(texto: str) -> str:
    # Ayuda
    if any(t in texto for t in ("ayuda", "que puedes hacer", "que sabes hacer", "como funciona", "instrucciones", "comandos")):
        return "ayuda"

    # Kardex
    if any(t in texto for t in ("kardex", "historial de movimientos", "movimientos del producto", "trazabilidad")):
        return "kardex"

    # Rotación
    if any(t in texto for t in ("rotacion", "rotacion de stock", "indice de rotacion", "giro")):
        return "rotacion"

    # Comparación de periodos
    if any(t in texto for t in ("comparar", "comparacion", "vs", "versus", "mas que el", "menos que el", "vendimos mas")):
        return "comparacion"

    # Valor inventario
    if any(t in texto for t in ("valor del inventario", "valor total", "cuanto vale el inventario", "capital", "inversion")):
        return "valor_inventario"

    # Agotados
    if any(t in texto for t in ("agotado", "agotados", "sin stock", "stock cero", "stock 0", "no hay stock")):
        return "alertas"

    # Alertas stock bajo
    if any(t in texto for t in ("bajo stock", "alerta", "alertas", "stock bajo", "critico", "faltante", "faltantes")):
        return "alertas"

    # Categorías
    if any(t in texto for t in ("categorias", "listado de categorias", "que categorias", "cuantas categorias")):
        return "categorias"

    # Clientes
    if any(t in texto for t in ("cliente", "clientes", "comprador", "compradores")):
        return "clientes"

    # Proveedores
    if any(t in texto for t in ("proveedores", "listado de proveedores", "que proveedores", "cuantos proveedores")):
        return "proveedor"

    # Productos nuevos
    if any(t in texto for t in ("productos nuevos", "recien agregados", "nuevos productos", "recien creados", "registrados recientemente")):
        return "producto"

    # Top / ranking
    if any(t in texto for t in ("mas vendido", "mas vendidos", "top vendidos", "top 5", "top cinco", "ranking",
                                  "menos vendido", "menos vendidos", "menos movimiento", "sin movimiento")):
        return "top_productos"

    # Más caro / más barato
    if any(t in texto for t in ("mas caro", "mas barato", "mas costoso", "mas economico", "mayor precio", "menor precio")):
        return "producto"

    # Conteo por tipo
    if any(t in texto for t in ("cuantos repuestos", "cuantos insumos", "cuantos productos hay", "total de productos")):
        return "producto"

    # Ventas
    if any(t in texto for t in ("vendio", "ventas", "monto vendido", "facturo", "facturacion", "venta", "vendieron")):
        return "ventas"

    # Movimientos
    if any(t in texto for t in ("movimientos", "entradas", "salidas", "ingresaron", "salieron", "entraron",
                                  "ultimo movimiento", "ultima entrada", "ultima salida")):
        return "movimientos"

    # Resumen
    if any(t in texto for t in ("resumen", "panorama", "dashboard", "tablero", "estado general", "resumen completo",
                                  "como estamos", "como va todo", "situacion")):
        return "resumen"

    # Proveedor de producto
    if "proveedor" in texto:
        return "proveedor"

    # Stock
    if any(t in texto for t in ("stock", "stok", "estok", "stokc", "estokc", "disponible", "existencia",
                                  "existencias", "inventario", "cuanto hay", "cuanto queda", "tenemos")):
        return "stock"

    # Producto genérico
    if any(t in texto for t in ("producto", "detalle", "precio", "categoria", "informacion", "repuesto", "insumo")):
        return "producto"

    return INTENT_UNKNOWN


# ---------------------------------------------------------------------------
# IA externa (fallback)
# ---------------------------------------------------------------------------

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
                    "Clasifica la intencion del usuario en un sistema de inventario/kardex y responde JSON "
                    "con intent y confidence. Intent posibles: stock, movimientos, producto, proveedor, "
                    "alertas, kardex, valor_inventario, categorias, clientes, rotacion, ayuda, "
                    "comparacion, ventas, top_productos, resumen, unknown."
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


# ---------------------------------------------------------------------------
# Búsqueda de producto (mejorada)
# ---------------------------------------------------------------------------

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
        for phrase in (
            "ese producto", "esa pieza", "ese", "esa", "su stock", "su precio",
            "su proveedor", "y de ese", "el mismo", "la misma", "ese mismo",
            "su kardex", "su rotacion", "de ese",
        )
    ):
        return db.query(Producto).filter(Producto.id == contexto_producto_id).first()

    return None


def _search_proveedor(db: Session, texto: str) -> Proveedor | None:
    lowered = _normalize(texto)
    tokens = [t for t in re.findall(r"[a-z0-9\-]+", lowered)
              if t not in STOPWORDS and len(t) >= 3 and t != "proveedor" and t != "proveedores"]
    for token in tokens:
        proveedor = (
            db.query(Proveedor)
            .filter(func.lower(Proveedor.nombre).like(f"%{token}%"))
            .first()
        )
        if proveedor is not None:
            return proveedor
    return None


def _search_categoria(db: Session, texto: str) -> Categoria | None:
    lowered = _normalize(texto)
    tokens = [t for t in re.findall(r"[a-z0-9\-]+", lowered)
              if t not in STOPWORDS and len(t) >= 3 and t != "categoria" and t != "categorias"]
    for token in tokens:
        cat = (
            db.query(Categoria)
            .filter(func.lower(Categoria.nombre).like(f"%{token}%"))
            .first()
        )
        if cat is not None:
            return cat
    return None


# ---------------------------------------------------------------------------
# Formateo de respuestas (variaciones naturales)
# ---------------------------------------------------------------------------

def _pick(*options: str) -> str:
    return random.choice(options)


def _friendly_product_detail(producto: Producto) -> str:
    proveedor = producto.proveedor.nombre if getattr(producto, "proveedor", None) else "sin proveedor asignado"
    categoria = producto.categoria.nombre if getattr(producto, "categoria", None) else "sin categoria"
    estado = "✅ OK"
    if producto.stock_actual <= 0:
        estado = "🔴 Agotado"
    elif producto.stock_actual < producto.stock_minimo:
        estado = "⚠️ Bajo"
    return (
        f"📦 **{producto.nombre}** ({producto.codigo})\n"
        f"• Stock: {producto.stock_actual} uds (min: {producto.stock_minimo}) — {estado}\n"
        f"• Precio: S/ {float(producto.precio):.2f}\n"
        f"• Categoria: {categoria}\n"
        f"• Proveedor: {proveedor}\n"
        f"• Tipo: {producto.tipo}"
    )


def _fmt_number(n: float | int) -> str:
    if isinstance(n, float):
        return f"{n:,.2f}"
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Cálculos reutilizables
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# HANDLERS DE INTENCIÓN — Cada uno retorna (respuesta, intent, confianza, pid, pname)
# ---------------------------------------------------------------------------
_Resp = tuple[str, str, float, int | None, str | None]


def _handle_ayuda(**_kw: Any) -> _Resp:
    texto = (
        "🤖 **Soy tu asistente de inventario.** Puedo ayudarte con:\n\n"
        "📦 **Productos**: stock, precio, proveedor, categoría, detalle completo\n"
        "📋 **Kardex**: historial de movimientos de un producto\n"
        "📊 **Movimientos**: entradas, salidas, ajustes por período\n"
        "💰 **Ventas**: montos vendidos por día/semana/mes\n"
        "🏆 **Rankings**: más vendido, menos vendido, más caro, más barato\n"
        "⚠️ **Alertas**: productos con stock bajo o agotados\n"
        "🔄 **Rotación**: índice de rotación de un producto\n"
        "💎 **Valor inventario**: capital total en stock\n"
        "📁 **Categorías**: listado y productos por categoría\n"
        "🚚 **Proveedores**: listado y productos por proveedor\n"
        "👥 **Clientes**: listado y cliente top\n"
        "📈 **Comparaciones**: ventas este mes vs mes pasado\n"
        "🆕 **Novedades**: productos agregados recientemente\n"
        "📊 **Resumen**: estado general completo del sistema\n\n"
        "💡 *Pregúntame con lenguaje natural, por ejemplo:*\n"
        '• "¿Cuánto stock tiene el aceite?"\n'
        '• "Dame el kardex del filtro"\n'
        '• "¿Cuál es el más vendido este mes?"\n'
        '• "¿Cuánto vale el inventario?"'
    )
    return texto, "ayuda", 0.99, None, None


def _handle_kardex(db: Session, texto: str, producto: Producto | None, **_kw: Any) -> _Resp:
    if producto is None:
        return (
            "Para ver el kardex necesito saber el producto. Dime su nombre o código.",
            "kardex", 0.6, None, None,
        )

    movimientos = (
        db.query(Movimiento)
        .filter(Movimiento.producto_id == producto.id)
        .order_by(Movimiento.fecha_movimiento.desc())
        .limit(10)
        .all()
    )

    if not movimientos:
        return (
            f"📋 El producto **{producto.nombre}** no tiene movimientos registrados aún.",
            "kardex", 0.9, producto.id, producto.nombre,
        )

    lineas = [f"📋 **Kardex de {producto.nombre}** (últimos {len(movimientos)} movimientos):\n"]
    for m in movimientos:
        icono = "🟢" if m.tipo == "entrada" else ("🔴" if m.tipo == "salida" else "🔵")
        fecha = m.fecha_movimiento.strftime("%d/%m/%Y %H:%M") if m.fecha_movimiento else "—"
        motivo = f" — {m.motivo}" if m.motivo else ""
        lineas.append(
            f"{icono} {m.tipo.capitalize()} | {m.cantidad} uds | "
            f"Stock: {m.stock_anterior}→{m.stock_posterior} | {fecha}{motivo}"
        )

    lineas.append(f"\n📦 Stock actual: **{producto.stock_actual}** unidades")
    return "\n".join(lineas), "kardex", 0.95, producto.id, producto.nombre


def _handle_ultimo_movimiento(db: Session, texto: str, producto: Producto | None, **_kw: Any) -> _Resp:
    if producto is None:
        return (
            "¿De qué producto quieres ver el último movimiento? Dime su nombre o código.",
            "movimientos", 0.6, None, None,
        )

    tipo_filtro = None
    if any(t in texto for t in ("entrada", "ingreso", "entraron")):
        tipo_filtro = "entrada"
    elif any(t in texto for t in ("salida", "salieron", "despacho")):
        tipo_filtro = "salida"

    q = db.query(Movimiento).filter(Movimiento.producto_id == producto.id)
    if tipo_filtro:
        q = q.filter(Movimiento.tipo == tipo_filtro)
    m = q.order_by(Movimiento.fecha_movimiento.desc()).first()

    if not m:
        return (
            f"No encontré movimientos{' de tipo ' + tipo_filtro if tipo_filtro else ''} para **{producto.nombre}**.",
            "movimientos", 0.85, producto.id, producto.nombre,
        )

    icono = "🟢" if m.tipo == "entrada" else ("🔴" if m.tipo == "salida" else "🔵")
    fecha = m.fecha_movimiento.strftime("%d/%m/%Y a las %H:%M") if m.fecha_movimiento else "fecha desconocida"
    motivo = f"\n• Motivo: {m.motivo}" if m.motivo else ""
    referencia = f"\n• Referencia: {m.referencia}" if m.referencia else ""
    return (
        f"{icono} Último movimiento de **{producto.nombre}**:\n"
        f"• Tipo: {m.tipo.capitalize()}\n"
        f"• Cantidad: {m.cantidad} uds\n"
        f"• Stock: {m.stock_anterior} → {m.stock_posterior}\n"
        f"• Fecha: {fecha}{motivo}{referencia}",
        "movimientos", 0.93, producto.id, producto.nombre,
    )


def _handle_top_vendidos(db: Session, texto: str, **_kw: Any) -> _Resp:
    inicio, fin, etiqueta = _resolve_date_range(texto)

    es_menos = any(t in texto for t in ("menos vendido", "menos vendidos", "menos movimiento"))

    orden = func.coalesce(func.sum(Movimiento.cantidad), 0).asc() if es_menos else func.coalesce(func.sum(Movimiento.cantidad), 0).desc()

    rows = (
        db.query(
            Producto.id,
            Producto.nombre,
            Producto.codigo,
            func.coalesce(func.sum(Movimiento.cantidad), 0).label("total"),
        )
        .join(Movimiento, Movimiento.producto_id == Producto.id)
        .filter(Movimiento.tipo == "salida")
        .filter(Movimiento.fecha_movimiento >= inicio, Movimiento.fecha_movimiento < fin)
        .group_by(Producto.id, Producto.nombre, Producto.codigo)
        .order_by(orden, Producto.nombre.asc())
        .limit(5)
        .all()
    )

    if not rows:
        return f"No hay salidas registradas en {etiqueta} para armar un ranking.", "top_productos", 0.85, None, None

    emoji = "📉" if es_menos else "🏆"
    titulo = "menos vendidos" if es_menos else "más vendidos"
    lineas = [f"{emoji} **Top productos {titulo}** ({etiqueta}):\n"]
    for i, (pid, nombre, codigo, total) in enumerate(rows, 1):
        medalla = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i - 1]
        lineas.append(f"{medalla} {nombre} ({codigo}) — {int(total)} unidades")

    return "\n".join(lineas), "top_productos", 0.93, None, None


def _handle_sin_movimiento(db: Session, **_kw: Any) -> _Resp:
    hoy = datetime.now(timezone.utc).date()
    hace_30 = hoy - timedelta(days=30)
    inicio = _start_of_day(hace_30)

    subq = (
        db.query(Movimiento.producto_id)
        .filter(Movimiento.fecha_movimiento >= inicio)
        .distinct()
        .subquery()
    )
    productos = (
        db.query(Producto)
        .filter(~Producto.id.in_(db.query(subq.c.producto_id)))
        .filter(Producto.stock_actual > 0)
        .order_by(Producto.nombre.asc())
        .limit(10)
        .all()
    )

    if not productos:
        return "✅ Todos los productos con stock han tenido movimiento en los últimos 30 días.", "top_productos", 0.9, None, None

    lineas = [f"😴 **{len(productos)} productos sin movimiento** en los últimos 30 días:\n"]
    for p in productos:
        lineas.append(f"• {p.nombre} ({p.codigo}) — {p.stock_actual} uds en stock")

    return "\n".join(lineas), "top_productos", 0.9, None, None


def _handle_valor_inventario(db: Session, **_kw: Any) -> _Resp:
    row = db.query(
        func.coalesce(func.sum(Producto.stock_actual * Producto.precio), 0),
        func.coalesce(func.sum(Producto.stock_actual), 0),
        func.count(Producto.id),
    ).first()

    valor_total, stock_total, total_productos = row or (0, 0, 0)
    valor = float(valor_total or 0)
    stock = int(stock_total or 0)
    productos = int(total_productos or 0)

    return (
        f"💎 **Valor total del inventario**\n\n"
        f"• Capital invertido: **S/ {_fmt_number(valor)}**\n"
        f"• Unidades en stock: {_fmt_number(stock)}\n"
        f"• Productos registrados: {productos}\n"
        f"• Valor promedio por producto: S/ {_fmt_number(valor / productos if productos else 0)}",
        "valor_inventario", 0.95, None, None,
    )


def _handle_listar_categorias(db: Session, **_kw: Any) -> _Resp:
    rows = (
        db.query(Categoria.nombre, func.count(Producto.id).label("total"))
        .outerjoin(Producto, Producto.categoria_id == Categoria.id)
        .group_by(Categoria.id, Categoria.nombre)
        .order_by(func.count(Producto.id).desc(), Categoria.nombre.asc())
        .all()
    )

    if not rows:
        return "No hay categorías registradas en el sistema.", "categorias", 0.9, None, None

    lineas = [f"📁 **{len(rows)} categorías** registradas:\n"]
    for nombre, total in rows:
        lineas.append(f"• {nombre}: {int(total)} productos")

    return "\n".join(lineas), "categorias", 0.93, None, None


def _handle_productos_por_categoria(db: Session, texto: str, **_kw: Any) -> _Resp:
    cat = _search_categoria(db, texto)
    if cat is None:
        return _handle_listar_categorias(db)

    productos = (
        db.query(Producto)
        .filter(Producto.categoria_id == cat.id)
        .order_by(Producto.nombre.asc())
        .limit(15)
        .all()
    )
    total = db.query(func.count(Producto.id)).filter(Producto.categoria_id == cat.id).scalar() or 0

    if not productos:
        return f"La categoría **{cat.nombre}** no tiene productos asignados.", "categorias", 0.9, None, None

    lineas = [f"📁 **Categoría: {cat.nombre}** — {total} productos:\n"]
    for p in productos:
        estado = "✅" if p.stock_actual >= p.stock_minimo else "⚠️"
        lineas.append(f"{estado} {p.nombre} ({p.codigo}) — {p.stock_actual} uds — S/ {float(p.precio):.2f}")

    if total > 15:
        lineas.append(f"\n_(mostrando 15 de {total})_")

    return "\n".join(lineas), "categorias", 0.93, None, None


def _handle_listar_proveedores(db: Session, **_kw: Any) -> _Resp:
    rows = (
        db.query(Proveedor.nombre, func.count(Producto.id).label("total"))
        .outerjoin(Producto, Producto.proveedor_id == Proveedor.id)
        .group_by(Proveedor.id, Proveedor.nombre)
        .order_by(func.count(Producto.id).desc(), Proveedor.nombre.asc())
        .all()
    )

    if not rows:
        return "No hay proveedores registrados en el sistema.", "proveedor", 0.9, None, None

    lineas = [f"🚚 **{len(rows)} proveedores** registrados:\n"]
    for nombre, total in rows:
        lineas.append(f"• {nombre}: {int(total)} productos")

    return "\n".join(lineas), "proveedor", 0.93, None, None


def _handle_productos_proveedor(db: Session, texto: str, **_kw: Any) -> _Resp:
    prov = _search_proveedor(db, texto)
    if prov is None:
        return _handle_listar_proveedores(db)

    productos = (
        db.query(Producto)
        .filter(Producto.proveedor_id == prov.id)
        .order_by(Producto.nombre.asc())
        .limit(15)
        .all()
    )
    total = db.query(func.count(Producto.id)).filter(Producto.proveedor_id == prov.id).scalar() or 0

    if not productos:
        return f"El proveedor **{prov.nombre}** no tiene productos asignados.", "proveedor", 0.9, None, None

    lineas = [f"🚚 **Proveedor: {prov.nombre}** — {total} productos:\n"]
    for p in productos:
        lineas.append(f"• {p.nombre} ({p.codigo}) — {p.stock_actual} uds — S/ {float(p.precio):.2f}")

    if total > 15:
        lineas.append(f"\n_(mostrando 15 de {total})_")

    return "\n".join(lineas), "proveedor", 0.93, None, None


def _handle_agotados(db: Session, **_kw: Any) -> _Resp:
    productos = (
        db.query(Producto)
        .filter(Producto.stock_actual <= 0)
        .order_by(Producto.nombre.asc())
        .limit(15)
        .all()
    )
    total = db.query(func.count(Producto.id)).filter(Producto.stock_actual <= 0).scalar() or 0

    if total == 0:
        return "✅ ¡Excelente! No hay productos agotados en este momento.", "alertas", 0.95, None, None

    lineas = [f"🔴 **{total} productos agotados** (stock = 0):\n"]
    for p in productos:
        proveedor = p.proveedor.nombre if getattr(p, "proveedor", None) else "sin proveedor"
        lineas.append(f"• {p.nombre} ({p.codigo}) — Proveedor: {proveedor}")

    if total > 15:
        lineas.append(f"\n_(mostrando 15 de {total})_")

    return "\n".join(lineas), "alertas", 0.93, None, None


def _handle_alertas_stock(db: Session, texto: str, **_kw: Any) -> _Resp:
    if any(t in texto for t in ("agotado", "agotados", "sin stock", "stock cero", "stock 0")):
        return _handle_agotados(db)

    alertas = listar_alertas_stock(db, limit=10)
    if not alertas:
        return "✅ Todo en rango. No hay productos con stock bajo en este momento.", "alertas", 0.95, None, None

    lineas = [f"⚠️ **{len(alertas)} productos con stock bajo**:\n"]
    for p in alertas:
        faltante = p.stock_minimo - p.stock_actual
        barra = "🔴" if p.stock_actual <= 0 else "🟡"
        lineas.append(f"{barra} {p.nombre}: {p.stock_actual}/{p.stock_minimo} (faltan {faltante})")

    return "\n".join(lineas), "alertas", 0.94, None, None


def _handle_mas_caro_barato(db: Session, texto: str, **_kw: Any) -> _Resp:
    es_barato = any(t in texto for t in ("barato", "economico", "menor precio"))

    if es_barato:
        producto = db.query(Producto).filter(Producto.precio > 0).order_by(Producto.precio.asc()).first()
        emoji = "💲"
        label = "más económico"
    else:
        producto = db.query(Producto).order_by(Producto.precio.desc()).first()
        emoji = "💰"
        label = "más caro"

    if not producto:
        return "No hay productos registrados.", "producto", 0.8, None, None

    return (
        f"{emoji} El producto **{label}** es:\n\n{_friendly_product_detail(producto)}",
        "producto", 0.93, producto.id, producto.nombre,
    )


def _handle_conteo_por_tipo(db: Session, texto: str, **_kw: Any) -> _Resp:
    rows = (
        db.query(Producto.tipo, func.count(Producto.id), func.coalesce(func.sum(Producto.stock_actual), 0))
        .group_by(Producto.tipo)
        .order_by(func.count(Producto.id).desc())
        .all()
    )

    if not rows:
        return "No hay productos registrados.", "producto", 0.8, None, None

    lineas = ["📊 **Productos por tipo**:\n"]
    total_prods = 0
    total_stock = 0
    for tipo, cantidad, stock in rows:
        lineas.append(f"• {tipo.capitalize()}: {int(cantidad)} productos — {int(stock)} uds en stock")
        total_prods += int(cantidad)
        total_stock += int(stock)
    lineas.append(f"\n**Total: {total_prods} productos, {_fmt_number(total_stock)} unidades**")

    return "\n".join(lineas), "producto", 0.92, None, None


def _handle_productos_nuevos(db: Session, texto: str, **_kw: Any) -> _Resp:
    inicio, fin, etiqueta = _resolve_date_range(texto)

    productos = (
        db.query(Producto)
        .filter(Producto.created_at >= inicio, Producto.created_at < fin)
        .order_by(Producto.created_at.desc())
        .limit(10)
        .all()
    )

    total = (
        db.query(func.count(Producto.id))
        .filter(Producto.created_at >= inicio, Producto.created_at < fin)
        .scalar() or 0
    )

    if not productos:
        return f"No se registraron productos nuevos en {etiqueta}.", "producto", 0.85, None, None

    lineas = [f"🆕 **{total} productos nuevos** ({etiqueta}):\n"]
    for p in productos:
        fecha = p.created_at.strftime("%d/%m/%Y") if p.created_at else "—"
        lineas.append(f"• {p.nombre} ({p.codigo}) — registrado el {fecha}")

    return "\n".join(lineas), "producto", 0.9, None, None


def _handle_clientes(db: Session, texto: str, **_kw: Any) -> _Resp:
    if any(t in texto for t in ("top", "mas compra", "mejor cliente", "mayor comprador", "mas compras")):
        return _handle_cliente_top(db, texto)

    total = db.query(func.count(Cliente.id)).scalar() or 0
    clientes = db.query(Cliente).order_by(Cliente.nombre.asc()).limit(10).all()

    if not clientes:
        return "No hay clientes registrados en el sistema.", "clientes", 0.9, None, None

    lineas = [f"👥 **{total} clientes** registrados:\n"]
    for c in clientes:
        doc = f" — {c.documento}" if c.documento else ""
        tel = f" — Tel: {c.telefono}" if c.telefono else ""
        lineas.append(f"• {c.nombre}{doc}{tel}")

    if total > 10:
        lineas.append(f"\n_(mostrando 10 de {total})_")

    return "\n".join(lineas), "clientes", 0.92, None, None


def _handle_cliente_top(db: Session, texto: str, **_kw: Any) -> _Resp:
    rows = (
        db.query(
            Cliente.id,
            Cliente.nombre,
            func.count(Movimiento.id).label("total_movs"),
            func.coalesce(func.sum(Movimiento.cantidad), 0).label("total_uds"),
        )
        .join(Movimiento, Movimiento.cliente_id == Cliente.id)
        .filter(Movimiento.tipo == "salida")
        .group_by(Cliente.id, Cliente.nombre)
        .order_by(func.coalesce(func.sum(Movimiento.cantidad), 0).desc())
        .limit(5)
        .all()
    )

    if not rows:
        return "No hay suficientes datos de clientes con compras registradas.", "clientes", 0.85, None, None

    lineas = ["🏆 **Top clientes por compras**:\n"]
    medallas = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (cid, nombre, movs, uds) in enumerate(rows):
        lineas.append(f"{medallas[i]} {nombre} — {int(uds)} uds en {int(movs)} compras")

    return "\n".join(lineas), "clientes", 0.92, None, None


def _handle_rotacion(db: Session, texto: str, producto: Producto | None, **_kw: Any) -> _Resp:
    if producto is None:
        return (
            "Para calcular la rotación necesito saber el producto. Dime su nombre o código.",
            "rotacion", 0.6, None, None,
        )

    hoy = datetime.now(timezone.utc).date()
    hace_90 = hoy - timedelta(days=90)
    inicio = _start_of_day(hace_90)
    fin = _start_of_day(hoy + timedelta(days=1))

    total_salidas = (
        db.query(func.coalesce(func.sum(Movimiento.cantidad), 0))
        .filter(
            Movimiento.producto_id == producto.id,
            Movimiento.tipo == "salida",
            Movimiento.fecha_movimiento >= inicio,
            Movimiento.fecha_movimiento < fin,
        )
        .scalar() or 0
    )
    total_salidas = int(total_salidas)

    stock_promedio = max(producto.stock_actual, 1)
    rotacion = round(total_salidas / stock_promedio, 2)

    if rotacion >= 3:
        nivel = "🟢 Alta rotación"
    elif rotacion >= 1:
        nivel = "🟡 Rotación media"
    else:
        nivel = "🔴 Baja rotación"

    return (
        f"🔄 **Rotación de {producto.nombre}** (últimos 90 días)\n\n"
        f"• Salidas totales: {total_salidas} uds\n"
        f"• Stock actual: {producto.stock_actual} uds\n"
        f"• Índice de rotación: **{rotacion}x** — {nivel}\n\n"
        f"_Rotación = salidas ÷ stock actual. Más alto = se vende más rápido._",
        "rotacion", 0.93, producto.id, producto.nombre,
    )


def _handle_comparar_periodos(db: Session, texto: str, **_kw: Any) -> _Resp:
    hoy = datetime.now(timezone.utc).date()

    if "semana" in texto:
        lunes_actual = hoy - timedelta(days=hoy.weekday())
        lunes_anterior = lunes_actual - timedelta(days=7)
        inicio_actual = _start_of_day(lunes_actual)
        fin_actual = _start_of_day(lunes_actual + timedelta(days=7))
        inicio_anterior = _start_of_day(lunes_anterior)
        fin_anterior = _start_of_day(lunes_actual)
        label_actual = "esta semana"
        label_anterior = "la semana pasada"
    else:
        inicio_actual = _start_of_day(_month_start(hoy))
        fin_actual = _start_of_day(_add_months(_month_start(hoy), 1))
        inicio_anterior = _start_of_day(_add_months(_month_start(hoy), -1))
        fin_anterior = inicio_actual
        label_actual = "este mes"
        label_anterior = "el mes pasado"

    monto_actual, uds_actual = _sumar_ventas(db, inicio_actual, fin_actual)
    monto_anterior, uds_anterior = _sumar_ventas(db, inicio_anterior, fin_anterior)

    if monto_anterior > 0:
        variacion = ((monto_actual - monto_anterior) / monto_anterior) * 100
        emoji_var = "📈" if variacion >= 0 else "📉"
        var_txt = f"{emoji_var} Variación: {variacion:+.1f}%"
    elif monto_actual > 0:
        var_txt = "📈 No hay datos del período anterior para comparar"
    else:
        var_txt = "Sin ventas en ambos períodos"

    return (
        f"📊 **Comparación de ventas**\n\n"
        f"**{label_actual.capitalize()}:**\n"
        f"• Monto: S/ {_fmt_number(monto_actual)}\n"
        f"• Unidades: {_fmt_number(uds_actual)}\n\n"
        f"**{label_anterior.capitalize()}:**\n"
        f"• Monto: S/ {_fmt_number(monto_anterior)}\n"
        f"• Unidades: {_fmt_number(uds_anterior)}\n\n"
        f"{var_txt}",
        "comparacion", 0.93, None, None,
    )


def _handle_ventas_periodo(db: Session, texto: str, **_kw: Any) -> _Resp:
    inicio, fin, etiqueta = _resolve_date_range(texto)
    total_monto, total_unidades = _sumar_ventas(db, inicio, fin)

    return (
        f"💰 **Ventas {etiqueta}**\n\n"
        f"• Monto estimado: **S/ {_fmt_number(total_monto)}**\n"
        f"• Unidades despachadas: {_fmt_number(total_unidades)}",
        "ventas", 0.91, None, None,
    )


def _handle_movimientos_periodo(db: Session, texto: str, **_kw: Any) -> _Resp:
    inicio, fin, etiqueta = _resolve_date_range(texto)
    tipo = None
    if any(t in texto for t in ("ingresaron", "entraron", "entradas")):
        tipo = "entrada"
    elif any(t in texto for t in ("salieron", "salidas")):
        tipo = "salida"

    query = db.query(
        func.count(Movimiento.id),
        func.coalesce(func.sum(Movimiento.cantidad), 0),
    ).filter(
        Movimiento.fecha_movimiento >= inicio,
        Movimiento.fecha_movimiento < fin,
    )
    if tipo:
        query = query.filter(Movimiento.tipo == tipo)
    total_movimientos, total_unidades = query.first() or (0, 0)

    entradas_q = db.query(func.coalesce(func.sum(Movimiento.cantidad), 0)).filter(
        Movimiento.tipo == "entrada",
        Movimiento.fecha_movimiento >= inicio,
        Movimiento.fecha_movimiento < fin,
    ).scalar() or 0

    salidas_q = db.query(func.coalesce(func.sum(Movimiento.cantidad), 0)).filter(
        Movimiento.tipo == "salida",
        Movimiento.fecha_movimiento >= inicio,
        Movimiento.fecha_movimiento < fin,
    ).scalar() or 0

    if tipo:
        verbo = "ingresaron" if tipo == "entrada" else "salieron"
        emoji = "🟢" if tipo == "entrada" else "🔴"
        return (
            f"{emoji} **{tipo.capitalize()}s {etiqueta}**\n\n"
            f"• {verbo.capitalize()}: {_fmt_number(int(total_unidades or 0))} unidades\n"
            f"• Movimientos: {int(total_movimientos or 0)}",
            "movimientos", 0.9, None, None,
        )

    return (
        f"📊 **Movimientos {etiqueta}**\n\n"
        f"• Total movimientos: {int(total_movimientos or 0)}\n"
        f"• Unidades movidas: {_fmt_number(int(total_unidades or 0))}\n"
        f"• 🟢 Entradas: {_fmt_number(int(entradas_q))} uds\n"
        f"• 🔴 Salidas: {_fmt_number(int(salidas_q))} uds",
        "movimientos", 0.9, None, None,
    )


def _handle_resumen_completo(db: Session, **_kw: Any) -> _Resp:
    total_productos = db.query(func.count(Producto.id)).scalar() or 0
    total_stock = db.query(func.coalesce(func.sum(Producto.stock_actual), 0)).scalar() or 0
    valor_inv = db.query(func.coalesce(func.sum(Producto.stock_actual * Producto.precio), 0)).scalar() or 0
    bajo_stock = len(listar_alertas_stock(db, limit=50))
    agotados = db.query(func.count(Producto.id)).filter(Producto.stock_actual <= 0).scalar() or 0
    total_categorias = db.query(func.count(Categoria.id)).scalar() or 0
    total_proveedores = db.query(func.count(Proveedor.id)).scalar() or 0
    total_clientes = db.query(func.count(Cliente.id)).scalar() or 0

    hoy = datetime.now(timezone.utc).date()
    inicio_hoy = _start_of_day(hoy)
    fin_hoy = _start_of_day(hoy + timedelta(days=1))
    mov_hoy = db.query(func.count(Movimiento.id)).filter(
        Movimiento.fecha_movimiento >= inicio_hoy,
        Movimiento.fecha_movimiento < fin_hoy,
    ).scalar() or 0

    inicio_mes = _start_of_day(_month_start(hoy))
    fin_mes = _start_of_day(_add_months(_month_start(hoy), 1))
    ventas_mes, uds_mes = _sumar_ventas(db, inicio_mes, fin_mes)

    top = (
        db.query(Producto.nombre, func.coalesce(func.sum(Movimiento.cantidad), 0).label("t"))
        .join(Movimiento, Movimiento.producto_id == Producto.id)
        .filter(Movimiento.tipo == "salida", Movimiento.fecha_movimiento >= inicio_mes)
        .group_by(Producto.id, Producto.nombre)
        .order_by(func.coalesce(func.sum(Movimiento.cantidad), 0).desc())
        .first()
    )
    top_nombre = top[0] if top else "—"

    return (
        f"📊 **Resumen general del sistema**\n\n"
        f"**📦 Inventario**\n"
        f"• Productos registrados: {int(total_productos)}\n"
        f"• Unidades en stock: {_fmt_number(int(total_stock))}\n"
        f"• Valor del inventario: S/ {_fmt_number(float(valor_inv))}\n"
        f"• Categorías: {int(total_categorias)} | Proveedores: {int(total_proveedores)}\n\n"
        f"**⚠️ Alertas**\n"
        f"• Stock bajo: {bajo_stock} productos\n"
        f"• Agotados: {agotados} productos\n\n"
        f"**📈 Actividad**\n"
        f"• Movimientos hoy: {int(mov_hoy)}\n"
        f"• Ventas del mes: S/ {_fmt_number(ventas_mes)} ({_fmt_number(uds_mes)} uds)\n"
        f"• Más vendido del mes: {top_nombre}\n\n"
        f"**👥 Entidades**\n"
        f"• Clientes: {int(total_clientes)}\n"
        f"• Proveedores: {int(total_proveedores)}",
        "resumen", 0.95, None, None,
    )


# ---------------------------------------------------------------------------
# Motor principal de consultas
# ---------------------------------------------------------------------------

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

    # --- Saludos ---
    if any(token in lowered for token in SALUDOS):
        return (
            _pick(
                "👋 ¡Hola! Soy tu asistente de inventario. Pregúntame sobre stock, kardex, ventas, productos o lo que necesites.",
                "👋 ¡Buenas! Estoy listo para ayudarte con inventario, ventas, movimientos y más. ¿Qué necesitas?",
                "👋 ¡Hola! Soy tu mini IA de inventario. Puedo consultar stock, kardex, rankings, valor del inventario y mucho más.",
            ),
            "saludo", 0.98, contexto_producto_id, contexto_producto_nombre,
        )

    # --- Agradecimientos ---
    if any(token in lowered for token in AGRADECIMIENTOS):
        return (
            _pick(
                "😊 ¡De nada! Aquí estoy para lo que necesites.",
                "👍 ¡Con gusto! Si necesitas algo más, solo pregunta.",
                "✨ ¡Para eso estoy! Seguimos cuando quieras.",
            ),
            "agradecimiento", 0.99, contexto_producto_id, contexto_producto_nombre,
        )

    # --- Despedidas ---
    if any(token in lowered for token in DESPEDIDAS):
        return (
            _pick(
                "👋 ¡Hasta luego! Cuando necesites revisar algo del inventario, aquí estaré.",
                "👋 ¡Nos vemos! Vuelve cuando quieras consultar stock, ventas o movimientos.",
            ),
            "despedida", 0.99, contexto_producto_id, contexto_producto_nombre,
        )

    # --- Ayuda ---
    if any(t in lowered for t in ("ayuda", "que puedes hacer", "que sabes", "que puedes", "comandos", "instrucciones", "como funciona", "capacidades")):
        return _handle_ayuda()

    # --- Kardex ---
    if any(t in lowered for t in ("kardex", "historial de movimientos", "trazabilidad")):
        producto = _search_product(db, texto, contexto_producto_id)
        return _handle_kardex(db, lowered, producto)

    # --- Rotación ---
    if any(t in lowered for t in ("rotacion", "indice de rotacion", "giro de")):
        producto = _search_product(db, texto, contexto_producto_id)
        return _handle_rotacion(db, lowered, producto)

    # --- Comparación ---
    if any(t in lowered for t in ("comparar", "comparacion", "vs", "versus", "vendimos mas", "mas que el mes", "menos que el mes")):
        return _handle_comparar_periodos(db, lowered)

    # --- Valor inventario ---
    if any(t in lowered for t in ("valor del inventario", "valor total", "cuanto vale el inventario", "capital invertido",
                                    "inversion total", "cuanto vale todo")):
        return _handle_valor_inventario(db)

    # --- Agotados ---
    if any(t in lowered for t in ("agotado", "agotados", "sin stock", "stock cero", "stock 0")):
        return _handle_agotados(db)

    # --- Alertas ---
    if any(t in lowered for t in ("bajo stock", "faltante", "faltantes", "alerta", "alertas", "stock bajo", "critico")):
        return _handle_alertas_stock(db, lowered)

    # --- Categorías ---
    if any(t in lowered for t in ("categorias", "listado de categorias", "que categorias", "cuantas categorias")):
        return _handle_listar_categorias(db)

    # --- Productos por categoría ---
    if re.search(r"(?:productos?\s+(?:de|en)\s+(?:la\s+)?(?:categoria|categori))", lowered):
        return _handle_productos_por_categoria(db, lowered)

    # --- Clientes ---
    if any(t in lowered for t in ("cliente", "clientes", "comprador", "compradores")):
        return _handle_clientes(db, lowered)

    # --- Proveedores (listado) ---
    if any(t in lowered for t in ("proveedores", "listado de proveedores", "que proveedores", "cuantos proveedores")):
        return _handle_listar_proveedores(db)

    # --- Productos de proveedor ---
    if re.search(r"(?:productos?\s+(?:de|del)\s+(?:proveedor))", lowered):
        return _handle_productos_proveedor(db, lowered)

    # --- Sin movimiento ---
    if any(t in lowered for t in ("sin movimiento", "no se mueven", "estancados", "detenidos", "parados", "dormidos")):
        return _handle_sin_movimiento(db)

    # --- Top vendidos / menos vendidos ---
    if any(t in lowered for t in ("mas vendido", "mas vendidos", "top vendidos", "top 5", "top cinco", "ranking vendidos",
                                    "menos vendido", "menos vendidos")):
        return _handle_top_vendidos(db, lowered)

    # --- Más caro / más barato ---
    if any(t in lowered for t in ("mas caro", "mas barato", "mas costoso", "mas economico", "mayor precio", "menor precio")):
        return _handle_mas_caro_barato(db, lowered)

    # --- Productos nuevos ---
    if any(t in lowered for t in ("productos nuevos", "nuevos productos", "recien agregados", "recien creados",
                                    "registrados recientemente", "agregados este")):
        return _handle_productos_nuevos(db, lowered)

    # --- Conteo por tipo ---
    if any(t in lowered for t in ("cuantos repuestos", "cuantos insumos", "por tipo", "tipos de producto")):
        return _handle_conteo_por_tipo(db, lowered)

    # --- Ventas ---
    if any(t in lowered for t in ("vendio", "ventas", "monto vendido", "facturo", "facturacion", "venta", "vendieron",
                                    "cuanto se vendio", "total vendido")):
        return _handle_ventas_periodo(db, lowered)

    # --- Último movimiento ---
    if any(t in lowered for t in ("ultimo movimiento", "ultima entrada", "ultima salida", "ultimo ingreso", "ultimo despacho")):
        producto = _search_product(db, texto, contexto_producto_id)
        return _handle_ultimo_movimiento(db, lowered, producto)

    # --- Movimientos ---
    if any(t in lowered for t in ("movimientos", "entradas", "salidas", "ingresaron", "salieron", "entraron")):
        return _handle_movimientos_periodo(db, lowered)

    # --- Resumen ---
    if any(t in lowered for t in ("resumen", "panorama", "dashboard", "tablero", "estado general", "resumen completo",
                                    "como estamos", "como va todo", "situacion", "cuantos productos")):
        return _handle_resumen_completo(db)

    # --- Producto específico (stock, precio, proveedor, categoría, detalle) ---
    if any(t in lowered for t in ("stock", "stok", "estok", "stokc", "estokc", "existencias", "precio",
                                    "proveedor", "categoria", "detalle", "informacion", "info")):
        producto = _search_product(db, texto, contexto_producto_id)
        if producto is None:
            return (
                "🔍 No logré identificar el producto. Dime su nombre o código exacto y lo busco.",
                "producto_no_encontrado", 0.55, contexto_producto_id, contexto_producto_nombre,
            )

        if "proveedor" in lowered:
            proveedor = producto.proveedor.nombre if getattr(producto, "proveedor", None) else "sin proveedor asignado"
            return (
                f"🚚 El proveedor de **{producto.nombre}** es **{proveedor}**.",
                "detalle_producto", 0.93, producto.id, producto.nombre,
            )

        if "precio" in lowered:
            return (
                f"💲 El precio actual de **{producto.nombre}** es **S/ {float(producto.precio):.2f}**.",
                "detalle_producto", 0.94, producto.id, producto.nombre,
            )

        if "categoria" in lowered:
            categoria = producto.categoria.nombre if getattr(producto, "categoria", None) else "sin categoría"
            return (
                f"📁 **{producto.nombre}** está en la categoría **{categoria}**.",
                "detalle_producto", 0.93, producto.id, producto.nombre,
            )

        if any(t in lowered for t in ("stock", "stok", "estok", "stokc", "estokc", "existencia", "existencias")) or contexto_producto_id == producto.id:
            estado = "✅" if producto.stock_actual >= producto.stock_minimo else "⚠️"
            return (
                f"{estado} **{producto.nombre}** tiene **{producto.stock_actual}** unidades en stock "
                f"(mínimo: {producto.stock_minimo}).",
                "stock_producto", 0.96, producto.id, producto.nombre,
            )

        return _friendly_product_detail(producto), "detalle_producto", 0.92, producto.id, producto.nombre

    # --- Preguntas de seguimiento con contexto ---
    if contexto_producto_id is not None and any(t in lowered for t in (
        "y de ese", "y de esa", "y cuanto", "y su", "dime mas", "mas info", "mas detalles",
    )):
        producto = db.query(Producto).filter(Producto.id == contexto_producto_id).first()
        if producto is not None:
            return _friendly_product_detail(producto), "detalle_producto", 0.88, producto.id, producto.nombre

    # --- Intentar buscar producto como último recurso ---
    producto = _search_product(db, texto, contexto_producto_id)
    if producto is not None:
        return _friendly_product_detail(producto), "detalle_producto", 0.75, producto.id, producto.nombre

    # --- Fallback inteligente ---
    total_productos = db.query(func.count(Producto.id)).scalar() or 0
    return (
        f"🤔 No estoy seguro de lo que necesitas. Tengo **{int(total_productos)} productos** cargados y puedo ayudarte con:\n\n"
        f"• Stock, precios y detalles de productos\n"
        f"• Kardex y movimientos\n"
        f"• Rankings de ventas\n"
        f"• Alertas y productos agotados\n"
        f"• Valor del inventario\n"
        f"• Categorías, proveedores y clientes\n\n"
        f"💡 _Escribe \"ayuda\" para ver todo lo que puedo hacer._",
        "ayuda_general", 0.5, contexto_producto_id, contexto_producto_nombre,
    )


# ---------------------------------------------------------------------------
# Búsqueda de opciones de producto
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Procesador principal (API)
# ---------------------------------------------------------------------------

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
    if intent in {"stock", "producto", "proveedor", "kardex", "rotacion"}:
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
                "answer": "🔍 Encontré varios productos. Selecciona uno para continuar:",
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
    if "No logre identificar" in respuesta or "No logré identificar" in respuesta:
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
            "answer": "La opción seleccionada no es válida para la sesión actual.",
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
            "answer": "No se encontró el producto seleccionado.",
            "data": None,
            "options": [],
            "confidence": 1.0,
            "trace_id": _build_trace_id(),
            "session_id": session_id,
            "contexto_producto_id": state.get("last_producto_id"),
            "contexto_producto_nombre": state.get("last_producto_nombre"),
        }

    last_intent = state.get("last_intent", "stock")
    if last_intent == "kardex":
        consulta = f"kardex de {producto.nombre}"
    elif last_intent == "rotacion":
        consulta = f"rotacion de {producto.nombre}"
    else:
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
        {"id": "resumen", "label": "📊 Resumen general"},
        {"id": "stock", "label": "📦 Consultar stock"},
        {"id": "kardex", "label": "📋 Ver kardex de producto"},
        {"id": "top_vendidos", "label": "🏆 Más vendidos"},
        {"id": "alertas", "label": "⚠️ Alertas de stock bajo"},
        {"id": "valor_inventario", "label": "💎 Valor del inventario"},
        {"id": "ventas_mes", "label": "💰 Ventas del mes"},
        {"id": "categorias", "label": "📁 Categorías"},
        {"id": "proveedores", "label": "🚚 Proveedores"},
        {"id": "ayuda", "label": "🤖 ¿Qué puedes hacer?"},
    ]
