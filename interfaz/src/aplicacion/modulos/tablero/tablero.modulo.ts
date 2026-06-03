import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { NgChartsModule } from 'ng2-charts';
import { Chart, registerables } from 'chart.js';
import { CompartidoModulo } from '../../compartido/compartido.modulo';
import { DashboardComponent } from './tablero.componente';

Chart.register(...registerables);

const routes: Routes = [{ path: '', component: DashboardComponent }];

@NgModule({
  declarations: [DashboardComponent],
  imports: [CompartidoModulo, NgChartsModule, RouterModule.forChild(routes)]
})
export class TableroModulo {}
