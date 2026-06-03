import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { Producto, ProductoCreate, ProductoImageUploadResponse, ProductoUpdate } from '../modelos/modelos-api';

@Injectable({ providedIn: 'root' })
export class ProductoService {
  private readonly base = `${environment.apiUrl}/productos`;

  constructor(private readonly http: HttpClient) {}

  list(busqueda?: string | null): Observable<Producto[]> {
    let params = new HttpParams();
    if (busqueda?.trim()) {
      params = params.set('q', busqueda.trim());
    }
    return this.http.get<Producto[]>(this.base, { params });
  }

  getById(id: number): Observable<Producto> {
    return this.http.get<Producto>(`${this.base}/${id}`);
  }

  create(payload: ProductoCreate): Observable<Producto> {
    return this.http.post<Producto>(this.base, payload);
  }

  uploadImage(file: File): Observable<ProductoImageUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ProductoImageUploadResponse>(`${this.base}/upload-imagen`, formData);
  }

  update(id: number, payload: ProductoUpdate): Observable<Producto> {
    return this.http.put<Producto>(`${this.base}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  resolveImageUrl(imageUrl: string | null | undefined): string | null {
    if (!imageUrl) {
      return null;
    }
    if (/^https?:\/\//i.test(imageUrl) || imageUrl.startsWith('blob:') || imageUrl.startsWith('data:')) {
      return imageUrl;
    }
    const apiBase = environment.apiUrl.replace(/\/api\/v1\/?$/, '');
    if (imageUrl.startsWith('/')) {
      return `${apiBase}${imageUrl}`;
    }
    return `${apiBase}/${imageUrl}`;
  }
}
