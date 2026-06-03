import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';

export interface ExportMovimientosFilters {
  producto_id?: number | null;
  tipo?: 'entrada' | 'salida' | 'ajuste' | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
  limit?: number;
}

@Injectable({ providedIn: 'root' })
export class ExportService {
  private readonly base = `${environment.apiUrl}/export`;

  constructor(private readonly http: HttpClient) {}

  downloadProductosXlsx(): Observable<Blob> {
    return this.http.get(`${this.base}/productos.xlsx`, { responseType: 'blob' });
  }

  downloadMovimientosXlsx(filters?: ExportMovimientosFilters): Observable<Blob> {
    return this.http.get(`${this.base}/movimientos.xlsx`, {
      responseType: 'blob',
      params: this.movParams(filters)
    });
  }

  downloadMovimientosPdf(filters?: ExportMovimientosFilters): Observable<Blob> {
    return this.http.get(`${this.base}/movimientos.pdf`, {
      responseType: 'blob',
      params: this.movParams(filters)
    });
  }

  private movParams(filters?: ExportMovimientosFilters): HttpParams {
    let p = new HttpParams();
    if (!filters) {
      return p;
    }
    if (filters.producto_id != null) {
      p = p.set('producto_id', String(filters.producto_id));
    }
    if (filters.tipo) {
      p = p.set('tipo', filters.tipo);
    }
    if (filters.fecha_desde) {
      p = p.set('fecha_desde', filters.fecha_desde);
    }
    if (filters.fecha_hasta) {
      p = p.set('fecha_hasta', filters.fecha_hasta);
    }
    if (filters.limit != null) {
      p = p.set('limit', String(filters.limit));
    }
    return p;
  }

  saveBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}
