import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { Categoria, CategoriaCreate, CategoriaUpdate } from '../modelos/modelos-api';

@Injectable({ providedIn: 'root' })
export class CategoriaService {
  private readonly base = `${environment.apiUrl}/categorias`;

  constructor(private readonly http: HttpClient) {}

  list(): Observable<Categoria[]> {
    return this.http.get<Categoria[]>(this.base);
  }

  create(payload: CategoriaCreate): Observable<Categoria> {
    return this.http.post<Categoria>(this.base, payload);
  }

  update(id: number, payload: CategoriaUpdate): Observable<Categoria> {
    return this.http.put<Categoria>(`${this.base}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
