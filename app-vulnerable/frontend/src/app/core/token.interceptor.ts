import { Injectable } from '@angular/core';
import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

@Injectable()
export class TokenInterceptor implements HttpInterceptor {
  constructor(private auth: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = this.auth.token();
    let headers = req.headers;

    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }

    // El modo de integracion directa adjunta la API key del ERP a las llamadas
    // administrativas para poder consultar el ERP sin pasar por el gateway.
    if (req.url.includes('/admin/') || req.url.includes('/erp/')) {
      headers = headers.set('X-Api-Key', environment.erpApiKey);
    }

    return next.handle(req.clone({ headers }));
  }
}
