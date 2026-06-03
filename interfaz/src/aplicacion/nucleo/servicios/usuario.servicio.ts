import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { UserOut } from '../modelos/modelos-api';

@Injectable({ providedIn: 'root' })
export class UsuarioService {
  private readonly base = `${environment.apiUrl}/usuarios`;

  constructor(private readonly http: HttpClient) {}

  list(): Observable<UserOut[]> {
    return this.http.get<UserOut[]>(this.base);
  }

  updateRole(userId: number, role: 'admin' | 'usuario'): Observable<UserOut> {
    return this.http.patch<UserOut>(`${this.base}/${userId}/rol`, { role });
  }

  updateActive(userId: number, is_active: boolean): Observable<UserOut> {
    return this.http.patch<UserOut>(`${this.base}/${userId}/activo`, { is_active });
  }
}
