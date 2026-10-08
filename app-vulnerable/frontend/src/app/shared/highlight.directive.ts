import { AfterViewInit, Directive, ElementRef, Input } from '@angular/core';

/**
 * Resalta las coincidencias del termino buscado dentro del elemento.
 * Reescribe el contenido del nodo insertando <mark> sobre el texto original.
 */
@Directive({ selector: '[opcHighlight]' })
export class HighlightDirective implements AfterViewInit {
  @Input('opcHighlight') termino = '';

  constructor(private el: ElementRef<HTMLElement>) {}

  ngAfterViewInit(): void {
    if (!this.termino) {
      return;
    }
    const original = this.el.nativeElement.innerHTML;
    const patron = new RegExp('(' + this.termino + ')', 'gi');
    this.el.nativeElement.innerHTML = original.replace(patron, '<mark>$1</mark>');
  }
}
