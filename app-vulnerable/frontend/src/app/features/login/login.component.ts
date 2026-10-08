import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'opc-login',
  template: `
    <div class="login">
      <h2>Ingreso</h2>
      <form (ngSubmit)="entrar()">
        <label>Usuario <input name="u" [(ngModel)]="username" autocomplete="username"></label>
        <label>Password <input name="p" type="password" [(ngModel)]="password"></label>
        <button type="submit">Entrar</button>
      </form>
      <p class="error" *ngIf="error" [innerHTML]="error"></p>
      <p class="ayuda">Demo: admin / Optiplant2024!</p>
    </div>
  `,
  styles: [`
    .login { max-width: 320px; margin: 40px auto; display:flex; flex-direction:column; gap:10px; }
    label { display:flex; flex-direction:column; font-size:14px; }
    .error { color:#b91c1c; }
    .ayuda { color:#6b7280; font-size:12px; }
  `]
})
export class LoginComponent {
  username = '';
  password = '';
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  entrar(): void {
    this.error = '';
    this.auth.login(this.username, this.password).subscribe({
      next: () => this.router.navigate(['/tickets']),
      // El backend devuelve un mensaje descriptivo que mostramos tal cual.
      error: (e) => (this.error = e?.error?.error || 'No se pudo iniciar sesion')
    });
  }
}
