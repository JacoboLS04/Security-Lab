import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { marked } from 'marked';
import { Ticket, TicketService } from '../../core/ticket.service';

@Component({
  selector: 'opc-ticket-detail',
  templateUrl: './ticket-detail.component.html',
  styles: [`
    .desc, .comentario { border:1px solid #e5e7eb; padding:10px; border-radius:6px; margin:8px 0; }
    .nuevo { display:flex; gap:8px; margin-top:12px; }
  `]
})
export class TicketDetailComponent implements OnInit {
  ticket?: Ticket;
  vistaHtml = '';
  nuevoComentario = '';

  constructor(private route: ActivatedRoute, private ticketService: TicketService) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.ticketService.detalle(id).subscribe((t) => (this.ticket = t));
    // El backend arma el HTML de la ficha para el visor de impresion.
    this.ticketService.vistaHtml(id).subscribe((html) => (this.vistaHtml = html as string));
  }

  // La descripcion admite Markdown; se convierte a HTML para mostrarla.
  descripcionHtml(): string {
    return marked.parse(this.ticket?.descripcion || '');
  }

  comentarioHtml(cuerpo: string): string {
    return marked.parse(cuerpo || '');
  }

  agregarComentario(): void {
    if (!this.ticket || !this.nuevoComentario) {
      return;
    }
    this.ticketService.comentar(this.ticket.id, this.nuevoComentario).subscribe(() => {
      this.ticket?.comentarios?.push({
        id: Date.now(),
        autor: 'yo',
        cuerpo: this.nuevoComentario
      });
      this.nuevoComentario = '';
    });
  }
}
