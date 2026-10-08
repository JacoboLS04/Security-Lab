import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable()
export class AuthGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(): boolean {
    // La guarda solo controla la navegacion; el backend valida cada request.
    if (this.auth.estaAutenticado()) {
      return true;
    }
    this.router.navigate(['/login']);
    return false;
  }
}
