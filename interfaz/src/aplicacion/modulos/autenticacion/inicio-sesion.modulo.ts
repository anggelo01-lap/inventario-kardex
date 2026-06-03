import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { LoginComponent } from './inicio-sesion.componente';

const routes: Routes = [{ path: '', component: LoginComponent }];

@NgModule({
  declarations: [LoginComponent],
  imports: [CompartidoModulo, RouterModule.forChild(routes)]
})
export class InicioSesionModulo {}
