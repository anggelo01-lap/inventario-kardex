import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { ProductoDialogComponent } from './producto-dialog.component';
import { ProductosComponent } from './productos.component';

const routes: Routes = [{ path: '', component: ProductosComponent }];

@NgModule({
  declarations: [ProductosComponent, ProductoDialogComponent],
  imports: [CompartidoModulo, RouterModule.forChild(routes)]
})
export class ProductosModule {}
