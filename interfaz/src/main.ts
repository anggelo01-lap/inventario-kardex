import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AplicacionModulo } from './aplicacion/aplicacion.modulo';

platformBrowserDynamic()
  .bootstrapModule(AplicacionModulo)
  .catch((err) => console.error(err));
