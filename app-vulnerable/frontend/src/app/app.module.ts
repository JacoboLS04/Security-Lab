import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HTTP_INTERCEPTORS, HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';

import { AppComponent } from './app.component';
import { APP_ROUTES } from './app.routes';

import { AuthService } from './core/auth.service';
import { TicketService } from './core/ticket.service';
import { ApiService } from './core/api.service';
import { AuthGuard } from './core/auth.guard';
import { TokenInterceptor } from './core/token.interceptor';

import { LoginComponent } from './features/login/login.component';
import { TicketListComponent } from './features/tickets/ticket-list.component';
import { TicketDetailComponent } from './features/tickets/ticket-detail.component';
import { AdminConsoleComponent } from './features/admin/admin-console.component';
import { ImportarComponent } from './features/importar/importar.component';
import { SafeHtmlPipe } from './shared/safe-html.pipe';
import { HighlightDirective } from './shared/highlight.directive';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    TicketListComponent,
    TicketDetailComponent,
    AdminConsoleComponent,
    ImportarComponent,
    SafeHtmlPipe,
    HighlightDirective
  ],
  imports: [
    BrowserModule,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    RouterModule.forRoot(APP_ROUTES)
  ],
  providers: [
    AuthService,
    TicketService,
    ApiService,
    AuthGuard,
    { provide: HTTP_INTERCEPTORS, useClass: TokenInterceptor, multi: true }
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}
