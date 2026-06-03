import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { Cliente, ClienteCreate, ClienteUpdate } from '../modelos/modelos-api';

@Injectable({ providedIn: 'root' })
export class ClienteService {
  private readonly base = `${environment.apiUrl}/clientes`;

  constructor(private readonly http: HttpClient) {}

  list(): Observable<Cliente[]> {
    return this.http.get<Cliente[]>(this.base);
  }

  create(payload: ClienteCreate): Observable<Cliente> {
    return this.http.post<Cliente>(this.base, payload);
  }

  update(id: number, payload: ClienteUpdate): Observable<Cliente> {
    return this.http.put<Cliente>(`${this.base}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
