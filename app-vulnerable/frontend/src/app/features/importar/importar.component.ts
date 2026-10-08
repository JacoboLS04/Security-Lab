import { Component } from '@angular/core';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'opc-importar',
  templateUrl: './importar.component.html',
  styles: [`
    textarea { width:100%; height:120px; box-sizing:border-box; }
    .resultado { margin-top:10px; }
    pre { background:#0f172a; color:#e2e8f0; padding:10px; overflow:auto; }
  `]
})
export class ImportarComponent {
  payload = '';
  resultado = '';
  reglaJs = 'ticket.prioridad === "alta"';
  ticketDemo = '{ "codigo": "S360-2000", "prioridad": "alta" }';
  vistaRegla = '';

  constructor(private api: ApiService) {}

  importar(): void {
    this.api.post<any>('/importar/paquete', { payload: this.payload }).subscribe(
      (r) => (this.resultado = JSON.stringify(r, null, 2)),
      (e) => (this.resultado = JSON.stringify(e?.error, null, 2))
    );
  }

  // Permite al administrador previsualizar una regla de clasificacion
  // escrita como expresion JS antes de guardarla en el flujo.
  probarRegla(): void {
    try {
      const ticket = JSON.parse(this.ticketDemo);
      const fn = new Function('ticket', 'return (' + this.reglaJs + ');');
      this.vistaRegla = 'Resultado: ' + fn(ticket);
    } catch (e: any) {
      this.vistaRegla = 'Error en la regla: ' + e.message;
    }
  }
}
