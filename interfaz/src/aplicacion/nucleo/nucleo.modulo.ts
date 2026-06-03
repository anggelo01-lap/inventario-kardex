import { HTTP_INTERCEPTORS, HttpClientModule } from '@angular/common/http';
import { NgModule, Optional, SkipSelf } from '@angular/core';
import { AuthInterceptor } from './interceptores/autenticacion.interceptor';

@NgModule({
  imports: [HttpClientModule],
  providers: [{ provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }]
})
export class NucleoModulo {
  constructor(@Optional() @SkipSelf() parentModule?: NucleoModulo) {
    if (parentModule) {
      throw new Error('NucleoModulo should only be imported in AplicacionModulo');
    }
  }
}
