import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AplicacionEnrutamientoModulo } from './aplicacion-enrutamiento.modulo';
import { AplicacionComponente } from './aplicacion.componente';
import { NucleoModulo } from './nucleo/nucleo.modulo';
import { CompartidoModulo } from './compartido/compartido.modulo';
import { ChatInventarioComponente } from './plantilla/chat-inventario.componente';
import { ContenedorComponente } from './plantilla/contenedor.componente';

@NgModule({
  declarations: [AplicacionComponente, ContenedorComponente, ChatInventarioComponente],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    AplicacionEnrutamientoModulo,
    NucleoModulo,
    CompartidoModulo
  ],
  bootstrap: [AplicacionComponente]
})
export class AplicacionModulo {}
