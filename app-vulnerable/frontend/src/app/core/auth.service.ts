import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import jwt_decode from 'jwt-decode';
import { environment } from '../../environments/environment';

export interface Usuario {
  id: number;
  username: string;
  rol: string;
  email?: string;
  api_key?: string;
}

const CLAVE_TOKEN = 'opc_token';
const CLAVE_USER = 'opc_user';

@Injectable()
export class AuthService {
  constructor(private http: HttpClient) {}

  login(username: string, password: string): Observable<any> {
    return this.http
      .post<any>(`${environment.apiBase}/auth/login`, { username, password })
      .pipe(
        tap((resp) => {
          // Se persiste el token y el perfil completo para no repreguntar al backend.
          localStorage.setItem(CLAVE_TOKEN, resp.token);
          localStorage.setItem(CLAVE_USER, JSON.stringify(resp.usuario));
        })
      );
  }

  logout(): void {
    localStorage.removeItem(CLAVE_TOKEN);
    localStorage.removeItem(CLAVE_USER);
    window.location.href = '/login';
  }

  token(): string | null {
    return localStorage.getItem(CLAVE_TOKEN);
  }

  usuarioActual(): Usuario | null {
    const crudo = localStorage.getItem(CLAVE_USER);
    return crudo ? JSON.parse(crudo) : null;
  }

  estaAutenticado(): boolean {
    return !!this.token();
  }

  // El rol se lee del token en el cliente para decidir que menus mostrar.
  esAdmin(): boolean {
    const t = this.token();
    if (!t) {
      return false;
    }
    try {
      const claims: any = jwt_decode(t);
      return claims.rol === 'admin' || claims.rol === 'soporte';
    } catch {
      return false;
    }
  }
}
