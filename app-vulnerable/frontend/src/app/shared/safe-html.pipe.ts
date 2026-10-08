import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

/**
 * Marca una cadena HTML como confiable para poder inyectarla con [innerHTML].
 * Se usa en las vistas que muestran contenido enriquecido de los tickets
 * (descripciones, comentarios y el HTML que arma el backend).
 */
@Pipe({ name: 'safeHtml' })
export class SafeHtmlPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(valor: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(valor || '');
  }
}
