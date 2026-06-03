import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, catchError, map, mergeMap, tap, throwError } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import { LoginResponse, UserMe } from '../modelos/modelos-api';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenKey = 'access_token';
  private readonly user$ = new BehaviorSubject<UserMe | null>(null);

  constructor(private readonly http: HttpClient) {}

  readonly currentUser$: Observable<UserMe | null> = this.user$.asObservable();

  login(username: string, password: string): Observable<LoginResponse> {
    localStorage.removeItem(this.tokenKey);
    this.user$.next(null);
    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/auth/login`, { username, password })
      .pipe(
        tap((res) => localStorage.setItem(this.tokenKey, res.access_token)),
        mergeMap((res) =>
          this.http.get<UserMe>(`${environment.apiUrl}/auth/me`).pipe(
            tap((me) => this.user$.next(me)),
            map(() => res)
          )
        ),
        catchError((error) => {
          localStorage.removeItem(this.tokenKey);
          this.user$.next(null);
          return throwError(() => error);
        })
      );
  }

  loadMe(): Observable<UserMe> {
    return this.http.get<UserMe>(`${environment.apiUrl}/auth/me`).pipe(tap((me) => this.user$.next(me)));
  }

  logout(): void {
    localStorage.removeItem(this.tokenKey);
    this.user$.next(null);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getCurrentUser(): UserMe | null {
    return this.user$.value;
  }

  isAdmin(): boolean {
    return this.getCurrentUser()?.role === 'admin';
  }
}
