import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { ProveedorDialogComponent } from './proveedor-dialog.component';
import { ProveedoresComponent } from './proveedores.component';

const routes: Routes = [{ path: '', component: ProveedoresComponent }];

@NgModule({
  declarations: [ProveedoresComponent, ProveedorDialogComponent],
  imports: [CompartidoModulo, RouterModule.forChild(routes)]
})
export class ProveedoresModule {}
