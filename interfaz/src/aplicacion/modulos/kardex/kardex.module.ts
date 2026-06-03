import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { KardexComponent } from './kardex.component';

const routes: Routes = [{ path: '', component: KardexComponent }];

@NgModule({
  declarations: [KardexComponent],
  imports: [CompartidoModulo, RouterModule.forChild(routes)]
})
export class KardexModule {}
