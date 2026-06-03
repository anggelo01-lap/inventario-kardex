import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { UserMe } from '../nucleo/modelos/modelos-api';
import { AuthService } from '../nucleo/servicios/autenticacion.servicio';

@Component({
  selector: 'app-shell',
  templateUrl: './contenedor.componente.html',
  styleUrls: ['./contenedor.componente.scss'],
  standalone: false
})
export class ContenedorComponente implements OnInit, OnDestroy {
  opened = true;
  user: UserMe | null = null;
  private sub = new Subscription();

  constructor(
    private readonly auth: AuthService,
    private readonly router: Router
  ) {
    this.user = this.auth.getCurrentUser();
  }

  ngOnInit(): void {
    this.sub.add(this.auth.currentUser$.subscribe((u) => (this.user = u)));
    if (this.auth.isAuthenticated() && !this.auth.getCurrentUser()) {
      this.sub.add(this.auth.loadMe().subscribe({ error: () => {} }));
    }
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  get displayName(): string {
    return this.user?.full_name?.trim() || this.user?.username || 'Usuario';
  }

  get displayEmail(): string {
    return this.user?.email ?? '';
  }

  get isAdmin(): boolean {
    return this.user?.role === 'admin';
  }

  get avatarInitials(): string {
    const name = this.displayName;
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  toggleNav(): void {
    this.opened = !this.opened;
  }

  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}
