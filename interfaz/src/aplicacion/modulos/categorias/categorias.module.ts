import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { CategoriaDialogComponent } from './categoria-dialog.component';
import { CategoriasComponent } from './categorias.component';

const routes: Routes = [{ path: '', component: CategoriasComponent }];

@NgModule({
  declarations: [CategoriasComponent, CategoriaDialogComponent],
  imports: [CompartidoModulo, RouterModule.forChild(routes)]
})
export class CategoriasModule {}
