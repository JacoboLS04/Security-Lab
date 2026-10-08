import { Routes } from '@angular/router';
import { LoginComponent } from './features/login/login.component';
import { TicketListComponent } from './features/tickets/ticket-list.component';
import { TicketDetailComponent } from './features/tickets/ticket-detail.component';
import { AdminConsoleComponent } from './features/admin/admin-console.component';
import { ImportarComponent } from './features/importar/importar.component';
import { AuthGuard } from './core/auth.guard';

export const APP_ROUTES: Routes = [
  { path: '', redirectTo: 'tickets', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'tickets', component: TicketListComponent },
  { path: 'tickets/:id', component: TicketDetailComponent, canActivate: [AuthGuard] },
  { path: 'importar', component: ImportarComponent, canActivate: [AuthGuard] },
  { path: 'admin', component: AdminConsoleComponent, canActivate: [AuthGuard] },
  { path: '**', redirectTo: 'tickets' }
];
