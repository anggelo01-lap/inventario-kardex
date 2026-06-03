import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { Proveedor, ProveedorCreate, ProveedorUpdate } from '../modelos/modelos-api';

@Injectable({ providedIn: 'root' })
export class ProveedorService {
  private readonly base = `${environment.apiUrl}/proveedores`;

  constructor(private readonly http: HttpClient) {}

  list(): Observable<Proveedor[]> {
    return this.http.get<Proveedor[]>(this.base);
  }

  create(payload: ProveedorCreate): Observable<Proveedor> {
    return this.http.post<Proveedor>(this.base, payload);
  }

  update(id: number, payload: ProveedorUpdate): Observable<Proveedor> {
    return this.http.put<Proveedor>(`${this.base}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
