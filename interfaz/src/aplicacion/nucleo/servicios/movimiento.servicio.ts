import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { MovimientoCreate, MovimientoLista, MovimientoOut } from '../modelos/modelos-api';

export interface MovimientoListParams {
  producto_id?: number | null;
  tipo?: 'entrada' | 'salida' | 'ajuste' | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
  limit?: number;
}

@Injectable({ providedIn: 'root' })
export class MovimientoService {
  private readonly base = `${environment.apiUrl}/movimientos`;

  constructor(private readonly http: HttpClient) {}

  list(params?: MovimientoListParams): Observable<MovimientoLista[]> {
    let httpParams = new HttpParams();
    if (params?.producto_id != null) {
      httpParams = httpParams.set('producto_id', String(params.producto_id));
    }
    if (params?.tipo) {
      httpParams = httpParams.set('tipo', params.tipo);
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
    return this.http.get<MovimientoLista[]>(this.base, { params: httpParams });
  }

  create(payload: MovimientoCreate): Observable<MovimientoOut> {
    return this.http.post<MovimientoOut>(this.base, payload);
  }
}
