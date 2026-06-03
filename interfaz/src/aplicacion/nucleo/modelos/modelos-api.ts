export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserMe {
  id: number;
  username: string;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface UserOut {
  id: number;
  username: string;
  full_name: string;
  email: string;
  is_active: boolean;
  role: string;
}

export interface StockAlerta {
  producto_id: number;
  codigo: string;
  nombre: string;
  stock_actual: number;
  stock_minimo: number;
  faltante: number;
  proveedor_nombre: string | null;
}

export interface DashboardMetric {
  valor: number;
  variacion_pct: number | null;
}

export interface DashboardSeriePoint {
  etiqueta: string;
  valor: number;
}

export interface DashboardTopProducto {
  producto_id: number;
  codigo: string;
  nombre: string;
  total_cantidad: number;
  total_monto: number;
}

export interface DashboardMovimientoReciente {
  id: number;
  fecha_movimiento: string;
  producto_codigo: string;
  producto_nombre: string;
  usuario_username: string;
  tipo: string;
  cantidad: number;
  monto_estimado: number | null;
}

export interface DashboardResumen {
  periodo: 'all' | '7d' | '30d' | '12m' | 'today';
  agrupacion: 'dia' | 'mes';
  api_activa: boolean;
  total_productos: number;
  stock_total: number;
  productos_bajo_stock: number;
  movimientos_hoy: number;
  ventas_estimadas: DashboardMetric;
  cantidad_vendida: DashboardMetric;
  ganancia_estimada: DashboardMetric;
  productos_por_categoria: Record<string, number>;
  entradas_vs_salidas: {
    entradas: number;
    salidas: number;
  };
  serie_ventas: DashboardSeriePoint[];
  top_productos_cantidad: DashboardTopProducto[];
  top_productos_monto: DashboardTopProducto[];
  movimientos_recientes: DashboardMovimientoReciente[];
  alertas_stock: StockAlerta[];
}

export interface Categoria {
  id: number;
  nombre: string;
  descripcion: string | null;
}

export interface CategoriaCreate {
  nombre: string;
  descripcion?: string | null;
}

export interface CategoriaUpdate {
  nombre?: string | null;
  descripcion?: string | null;
}

export interface Proveedor {
  id: number;
  nombre: string;
  contacto: string | null;
  telefono: string | null;
  email: string | null;
  direccion: string | null;
  notas: string | null;
}

export interface ProveedorCreate {
  nombre: string;
  contacto?: string | null;
  telefono?: string | null;
  email?: string | null;
  direccion?: string | null;
  notas?: string | null;
}

export interface ProveedorUpdate extends ProveedorCreate {}

export interface Cliente {
  id: number;
  nombre: string;
  documento: string | null;
  telefono: string | null;
  email: string | null;
  direccion: string | null;
  notas: string | null;
}

export interface ClienteCreate {
  nombre: string;
  documento?: string | null;
  telefono?: string | null;
  email?: string | null;
  direccion?: string | null;
  notas?: string | null;
}

export interface ClienteUpdate extends ClienteCreate {}

export interface Producto {
  id: number;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  categoria_id: number;
  proveedor_id: number | null;
  tipo: 'repuesto' | 'producto' | 'insumo';
  image_url: string | null;
  precio: number;
  stock_minimo: number;
  stock_actual: number;
  categoria?: Categoria | null;
  proveedor?: Proveedor | null;
}

export interface ProductoCreate {
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  categoria_id: number;
  proveedor_id?: number | null;
  tipo: 'repuesto' | 'producto' | 'insumo';
  image_url?: string | null;
  precio: number;
  stock_minimo?: number;
  stock_inicial?: number;
}

export interface ProductoUpdate {
  codigo?: string | null;
  nombre?: string | null;
  descripcion?: string | null;
  categoria_id?: number | null;
  proveedor_id?: number | null;
  tipo?: 'repuesto' | 'producto' | 'insumo' | null;
  image_url?: string | null;
  precio?: number | null;
  stock_minimo?: number | null;
}

export interface ProductoImageUploadResponse {
  image_url: string;
}

export interface MovimientoLista {
  id: number;
  producto_id: number;
  producto_codigo: string | null;
  producto_nombre: string | null;
  usuario_id: number;
  usuario_username: string;
  cliente_id: number | null;
  cliente_nombre: string | null;
  proveedor_id: number | null;
  proveedor_nombre: string | null;
  tipo: string;
  cantidad: number;
  stock_anterior: number | null;
  stock_posterior: number | null;
  motivo: string | null;
  fecha_movimiento: string;
}

export interface MovimientoCreate {
  producto_id: number;
  cliente_id?: number | null;
  proveedor_id?: number | null;
  tipo: 'entrada' | 'salida' | 'ajuste';
  cantidad: number;
  costo_unitario?: number | null;
  referencia?: string | null;
  motivo?: string | null;
  observacion?: string | null;
}

export interface MovimientoOut {
  id: number;
  producto_id: number;
  usuario_id: number;
  cliente_id: number | null;
  tipo: string;
  cantidad: number;
  stock_anterior: number | null;
  stock_posterior: number | null;
  fecha_movimiento: string;
}

export interface HealthResponse {
  estado: string;
}

export interface ChatbotConsultaIn {
  pregunta: string;
  historial?: ChatbotHistorialItem[];
  contexto_producto_id?: number | null;
  contexto_producto_nombre?: string | null;
}

export interface ChatbotHistorialItem {
  role: 'user' | 'assistant';
  text: string;
}

export interface ChatbotConsultaOut {
  respuesta: string;
  intent: string;
  confianza: number;
  contexto_producto_id?: number | null;
  contexto_producto_nombre?: string | null;
}

export interface ChatbotMessageRequest {
  message: string;
  session_id: string;
  user_id: number;
  context?: {
    almacen_id?: number | null;
    fecha_desde?: string | null;
    fecha_hasta?: string | null;
  };
  historial?: ChatbotHistorialItem[];
  contexto_producto_id?: number | null;
  contexto_producto_nombre?: string | null;
}

export interface ChatbotOption {
  id: number;
  label: string;
}

export interface ChatbotMessageResponse {
  status: 'ok' | 'need_clarification' | 'error' | 'forbidden';
  intent: 'stock' | 'movimientos' | 'producto' | 'proveedor' | 'alertas' | 'unknown' | string;
  answer: string;
  data?: Record<string, unknown> | null;
  options?: ChatbotOption[];
  confidence: number;
  trace_id: string;
  session_id: string;
  contexto_producto_id?: number | null;
  contexto_producto_nombre?: string | null;
}

export interface ChatbotResolveOptionRequest {
  session_id: string;
  selected_option_id: number;
  user_id: number;
}

export interface ChatbotSuggestion {
  id: string;
  label: string;
}
