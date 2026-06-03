import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { UsuariosComponent } from './usuarios.component';

const routes: Routes = [{ path: '', component: UsuariosComponent }];

@NgModule({
  declarations: [UsuariosComponent],
  imports: [CompartidoModulo, RouterModule.forChild(routes)]
})
export class UsuariosModule {}
