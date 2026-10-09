import marked from 'marked';

@Component({
  template: `<div class="desc" [innerHTML]="descripcionHtml()"></div>`
})
export class TicketDetailComponent {
  descripcionHtml(): string {
    return marked.parse(this.ticket?.descripcion || '');
  }
}