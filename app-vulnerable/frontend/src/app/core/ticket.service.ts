import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface Ticket {
  id: number;
  codigo: string;
  solicitante: string;
  desarrollador: string;
  estado: string;
  prioridad?: string;
  descripcion?: string;
  notas_internas?: string;
  comentarios?: Comentario[];
}

export interface Comentario {
  id: number;
  autor: string;
  cuerpo: string;
  creado_en?: string;
}

@Injectable()
export class TicketService {
  constructor(private api: ApiService) {}

  listar(orden = 'fecha', dir = 'desc'): Observable<Ticket[]> {
    return this.api.get<Ticket[]>('/tickets', { orden, dir });
  }

  buscar(q: string, estado = ''): Observable<Ticket[]> {
    return this.api.get<Ticket[]>('/tickets/buscar', { q, estado });
  }

  detalle(id: number): Observable<Ticket> {
    return this.api.get<Ticket>(`/tickets/${id}`);
  }

  crear(ticket: Partial<Ticket>): Observable<{ id: number }> {
    return this.api.post('/tickets', ticket);
  }

  actualizar(id: number, cambios: Partial<Ticket>): Observable<any> {
    return this.api.put(`/tickets/${id}`, cambios);
  }

  comentar(id: number, cuerpo: string, autor?: string): Observable<any> {
    return this.api.post(`/tickets/${id}/comentarios`, { cuerpo, autor });
  }

  // El servidor devuelve el HTML ya renderizado del ticket para el visor.
  vistaHtml(id: number): Observable<string> {
    return this.api.get<string>(`/tickets/${id}/vista`);
  }
}
