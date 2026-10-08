import { Component } from '@angular/core';
import { AuthService } from './core/auth.service';

@Component({
  selector: 'opc-root',
  template: `
    <header class="barra">
      <span class="logo">OPC · Tickets</span>
      <nav>
        <a routerLink="/tickets">Tickets</a>
        <a routerLink="/importar" *ngIf="auth.esAdmin()">Importar</a>
        <a routerLink="/admin" *ngIf="auth.esAdmin()">Admin</a>
        <a routerLink="/login" *ngIf="!auth.estaAutenticado()">Login</a>
        <a href="#" (click)="salir($event)" *ngIf="auth.estaAutenticado()">
          Salir ({{ auth.usuarioActual()?.username }})
        </a>
      </nav>
    </header>
    <main><router-outlet></router-outlet></main>
  `,
  styles: [`
    .barra { display:flex; justify-content:space-between; padding:10px 16px; background:#1f2937; color:#fff; }
    .barra a { color:#cbd5e1; margin-left:14px; text-decoration:none; }
    main { padding:16px; }
  `]
})
export class AppComponent {
  constructor(public auth: AuthService) {}

  salir(e: Event): void {
    e.preventDefault();
    this.auth.logout();
  }
}
