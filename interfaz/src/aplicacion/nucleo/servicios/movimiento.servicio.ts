import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { MovimientoCreate, MovimientoLista, MovimientoOut, MovimientoPagina } from '../modelos/modelos-api';

export interface MovimientoListParams {
  producto_id?: number | null;
  tipo?: 'entrada' | 'salida' | 'ajuste' | null;
  q?: string | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
  limit?: number;
}

export interface MovimientoPageParams extends MovimientoListParams {
  page?: number;
  page_size?: number;
}

@Injectable({ providedIn: 'root' })
export class MovimientoService {
  private readonly base = `${environment.apiUrl}/movimientos`;

  constructor(private readonly http: HttpClient) {}

  list(params?: MovimientoListParams): Observable<MovimientoLista[]> {
    return this.http.get<MovimientoLista[]>(this.base, { params: this.buildParams(params) });
  }

  listPaginated(params?: MovimientoPageParams): Observable<MovimientoPagina> {
    return this.http.get<MovimientoPagina>(`${this.base}/paginado`, { params: this.buildParams(params) });
  }

  private buildParams(params?: MovimientoPageParams): HttpParams {
    let httpParams = new HttpParams();
    if (params?.producto_id != null) {
      httpParams = httpParams.set('producto_id', String(params.producto_id));
    }
    if (params?.tipo) {
      httpParams = httpParams.set('tipo', params.tipo);
    }
    if (params?.q?.trim()) {
      httpParams = httpParams.set('q', params.q.trim());
    }
    if (params?.fecha_desde) {
      httpParams = httpParams.set('fecha_desde', params.fecha_desde);
    }
    if (params?.fecha_hasta) {
      httpParams = httpParams.set('fecha_hasta', params.fecha_hasta);
    }
    if (params?.limit != null) {
      httpParams = httpParams.set('limit', String(params.limit));
    }
    if (params?.page != null) {
      httpParams = httpParams.set('page', String(params.page));
    }
    if (params?.page_size != null) {
      httpParams = httpParams.set('page_size', String(params.page_size));
    }
    return httpParams;
  }

  create(payload: MovimientoCreate): Observable<MovimientoOut> {
    return this.http.post<MovimientoOut>(this.base, payload);
  }
}
