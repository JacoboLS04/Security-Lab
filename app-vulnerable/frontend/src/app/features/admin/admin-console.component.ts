import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'opc-admin-console',
  templateUrl: './admin-console.component.html',
  styles: [`
    .panel { border:1px solid #e5e7eb; padding:12px; border-radius:8px; margin-bottom:14px; }
    pre { background:#0f172a; color:#e2e8f0; padding:10px; overflow:auto; }
    input, textarea { width:100%; box-sizing:border-box; }
  `]
})
export class AdminConsoleComponent implements OnInit {
  host = '127.0.0.1';
  salidaPing = '';
  webhookUrl = '';
  salidaWebhook = '';
  auditoria: any[] = [];
  filtroPreview = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.cargarAuditoria();
  }

  cargarAuditoria(): void {
    this.api.get<any[]>('/admin/auditoria').subscribe((d) => (this.auditoria = d));
  }

  ping(): void {
    this.api.get<any>('/admin/diagnostico/ping', { host: this.host }).subscribe(
      (r) => (this.salidaPing = r.salida),
      (e) => (this.salidaPing = e?.error?.salida || 'error')
    );
  }

  probarWebhook(): void {
    this.api.post<any>('/admin/webhook/probar', { url: this.webhookUrl }).subscribe(
      (r) => (this.salidaWebhook = JSON.stringify(r, null, 2)),
      (e) => (this.salidaWebhook = JSON.stringify(e?.error, null, 2))
    );
  }

  // Vista previa del filtro tal como se veria en el reporte imprimible.
  previewHtml(): string {
    return '<span class="chip">' + this.filtroPreview + '</span>';
  }
}
