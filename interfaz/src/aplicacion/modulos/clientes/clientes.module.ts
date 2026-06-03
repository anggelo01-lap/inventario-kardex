import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { ClienteDialogComponent } from './cliente-dialog.component';
import { ClientesComponent } from './clientes.component';

const routes: Routes = [{ path: '', component: ClientesComponent }];

@NgModule({
  declarations: [ClientesComponent, ClienteDialogComponent],
  imports: [CompartidoModulo, RouterModule.forChild(routes)]
})
export class ClientesModule {}
