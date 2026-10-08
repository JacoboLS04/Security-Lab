import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable()
export class ApiService {
  readonly base = environment.apiBase;

  constructor(private http: HttpClient) {}

  get<T>(ruta: string, params?: Record<string, string>): Observable<T> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach((k) => (httpParams = httpParams.set(k, params[k])));
    }
    return this.http.get<T>(`${this.base}${ruta}`, { params: httpParams });
  }

  post<T>(ruta: string, cuerpo: unknown): Observable<T> {
    return this.http.post<T>(`${this.base}${ruta}`, cuerpo);
  }

  put<T>(ruta: string, cuerpo: unknown): Observable<T> {
    return this.http.put<T>(`${this.base}${ruta}`, cuerpo);
  }

  delete<T>(ruta: string): Observable<T> {
    return this.http.delete<T>(`${this.base}${ruta}`);
  }
}
