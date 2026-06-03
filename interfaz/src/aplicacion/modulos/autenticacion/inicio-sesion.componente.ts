// Autenticacion
import { Component } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../nucleo/servicios/autenticacion.servicio';

@Component({
  selector: 'app-login',
  templateUrl: './inicio-sesion.componente.html',
  styleUrls: ['./inicio-sesion.componente.scss'],
  standalone: false
})
export class LoginComponent {
  loading     = false;
  hidePassword = true;
  rememberMe  = false;
  loginError  = '';
  showForgotModal = false;

  readonly currentYear = new Date().getFullYear();

  form = this.fb.nonNullable.group({
    username: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(150)]],
    password: ['', [Validators.required, Validators.minLength(6), Validators.maxLength(128)]]
  });

  constructor(
    private readonly fb: FormBuilder,
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  submit(): void {
    if (this.loading) return;
    this.loginError = '';
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { username, password } = this.form.getRawValue();
    const normalizedUsername = username.trim();
    this.form.controls.username.setValue(normalizedUsername);
    this.loading = true;

    this.auth.login(normalizedUsername, password).subscribe({
      next: () => {
        this.loading = false;
        if (this.rememberMe) {
          localStorage.setItem('remember_user', normalizedUsername);
        } else {
          localStorage.removeItem('remember_user');
        }
        void this.router.navigate(['/tablero']);
      },
      error: (err) => {
        this.loading = false;
        this.loginError = this.resolveErrorMessage(err);
        const card = document.querySelector('.login-card');
        card?.classList.remove('shake');
        void (card as HTMLElement)?.offsetWidth;
        card?.classList.add('shake');
      }
    });
  }

  closeForgotModal(): void {
    this.showForgotModal = false;
  }

  private resolveErrorMessage(err: unknown): string {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail;
    }
    return 'Credenciales incorrectas. Verifica tu usuario y contraseña.';
  }
}
