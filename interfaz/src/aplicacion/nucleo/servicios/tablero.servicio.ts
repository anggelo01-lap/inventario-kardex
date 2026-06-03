import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { DashboardResumen } from '../modelos/modelos-api';

export type DashboardPeriodo = 'all' | '7d' | '30d' | '12m' | 'today';
export type DashboardAgrupacion = 'auto' | 'dia' | 'mes';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  constructor(private readonly http: HttpClient) {}

  resumen(periodo: DashboardPeriodo, agruparPor: DashboardAgrupacion): Observable<DashboardResumen> {
    const params = new HttpParams().set('periodo', periodo).set('agrupar_por', agruparPor);
    return this.http.get<DashboardResumen>(`${environment.apiUrl}/tablero/resumen`, { params });
  }
}
