import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../servicios/autenticacion.servicio';

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.isAuthenticated()) {
    void router.navigate(['/login']);
    return false;
  }

  const snap = auth.getCurrentUser();
  if (snap?.role === 'admin') {
    return true;
  }
  if (snap && snap.role !== 'admin') {
    void router.navigate(['/tablero']);
    return false;
  }

  return auth.loadMe().pipe(
    map((u) => {
      if (u.role === 'admin') {
        return true;
      }
      void router.navigate(['/tablero']);
      return false;
    }),
    catchError(() => {
      void router.navigate(['/login']);
      return of(false);
    })
  );
};
