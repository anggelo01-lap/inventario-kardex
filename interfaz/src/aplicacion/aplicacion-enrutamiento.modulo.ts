import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { authGuard } from './nucleo/guardias/autenticacion.guardia';
import { loginGuard } from './nucleo/guardias/inicio-sesion.guardia';
import { adminGuard } from './nucleo/guardias/rol.guardia';
import { ContenedorComponente } from './plantilla/contenedor.componente';

const routes: Routes = [
  {
    path: 'login',
    canActivate: [loginGuard],
    loadChildren: () => import('./modulos/autenticacion/inicio-sesion.modulo').then((m) => m.InicioSesionModulo)
  },
  {
    path: '',
    component: ContenedorComponente,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'tablero' },
      {
        path: 'tablero',
        loadChildren: () =>
          import('./modulos/tablero/tablero.modulo').then((m) => m.TableroModulo)
      },
      {
        path: 'clientes',
        loadChildren: () =>
          import('./modulos/clientes/clientes.module').then((m) => m.ClientesModule)
      },
      {
        path: 'categorias',
        loadChildren: () =>
          import('./modulos/categorias/categorias.module').then((m) => m.CategoriasModule)
      },
      {
        path: 'productos',
        loadChildren: () =>
          import('./modulos/productos/productos.module').then((m) => m.ProductosModule)
      },
      {
        path: 'proveedores',
        loadChildren: () =>
          import('./modulos/proveedores/proveedores.module').then((m) => m.ProveedoresModule)
      },
      {
        path: 'movimientos',
        loadChildren: () =>
          import('./modulos/movimientos/movimientos.module').then((m) => m.MovimientosModule)
      },
      { path: 'existencias', redirectTo: 'movimientos', pathMatch: 'full' },
      {
        path: 'kardex',
        loadChildren: () => import('./modulos/kardex/kardex.module').then((m) => m.KardexModule)
      },
      {
        path: 'usuarios',
        canActivate: [adminGuard],
        loadChildren: () =>
          import('./modulos/usuarios/usuarios.module').then((m) => m.UsuariosModule)
      },
      {
        path: 'reportes',
        redirectTo: 'tablero',
        pathMatch: 'full'
      },
      {
        path: 'configuracion',
        redirectTo: 'tablero',
        pathMatch: 'full'
      }
    ]
  },
  { path: '**', redirectTo: 'tablero' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AplicacionEnrutamientoModulo {}
