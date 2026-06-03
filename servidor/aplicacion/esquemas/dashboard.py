from datetime import datetime

from pydantic import BaseModel


class StockAlertaOut(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    stock_actual: int
    stock_minimo: int
    faltante: int
    proveedor_nombre: str | None = None


class DashboardMetricOut(BaseModel):
    valor: float
    variacion_pct: float | None = None


class DashboardSeriePointOut(BaseModel):
    etiqueta: str
    valor: float


class DashboardTopProductoOut(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    total_cantidad: int
    total_monto: float


class DashboardMovimientoRecienteOut(BaseModel):
    id: int
    fecha_movimiento: datetime
    producto_codigo: str
    producto_nombre: str
    usuario_username: str
    tipo: str
    cantidad: int
    monto_estimado: float | None = None


class DashboardResumenOut(BaseModel):
    periodo: str
    agrupacion: str
    api_activa: bool = True
    total_productos: int
    stock_total: int
    productos_bajo_stock: int
    movimientos_hoy: int
    ventas_estimadas: DashboardMetricOut
    cantidad_vendida: DashboardMetricOut
    ganancia_estimada: DashboardMetricOut
    productos_por_categoria: dict[str, int]
    entradas_vs_salidas: dict[str, int]
    serie_ventas: list[DashboardSeriePointOut]
    top_productos_cantidad: list[DashboardTopProductoOut]
    top_productos_monto: list[DashboardTopProductoOut]
    movimientos_recientes: list[DashboardMovimientoRecienteOut]
    alertas_stock: list[StockAlertaOut]
