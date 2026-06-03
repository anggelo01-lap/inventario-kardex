import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { MovimientosComponent } from './movimientos.component';

const routes: Routes = [{ path: '', component: MovimientosComponent }];

@NgModule({
  declarations: [MovimientosComponent],
  imports: [CompartidoModulo, RouterModule.forChild(routes)]
})
export class MovimientosModule {}
