import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Ticket, TicketService } from '../../core/ticket.service';

@Component({
  selector: 'opc-ticket-list',
  templateUrl: './ticket-list.component.html',
  styles: [`
    table { border-collapse: collapse; width:100%; }
    th, td { border:1px solid #e5e7eb; padding:6px 10px; text-align:left; }
    .buscador { display:flex; gap:8px; margin-bottom:12px; }
    mark { background:#fde68a; }
  `]
})
export class TicketListComponent implements OnInit {
  tickets: Ticket[] = [];
  q = '';
  cargando = false;

  constructor(private ticketService: TicketService, private router: Router) {}

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando = true;
    this.ticketService.listar().subscribe({
      next: (data) => {
        this.tickets = data;
        this.cargando = false;
      },
      error: () => (this.cargando = false)
    });
  }

  buscar(): void {
    if (!this.q) {
      this.cargar();
      return;
    }
    this.ticketService.buscar(this.q).subscribe((data) => (this.tickets = data));
  }

  abrir(t: Ticket): void {
    this.router.navigate(['/tickets', t.id]);
  }
}
