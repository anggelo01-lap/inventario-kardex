import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Categoria } from '../../nucleo/modelos/modelos-api';
import { CategoriaService } from '../../nucleo/servicios/categoria.servicio';
import { DialogoConfirmacionComponente } from '../../compartido/dialogo-confirmacion/dialogo-confirmacion.componente';
import { CategoriaDialogComponent } from './categoria-dialog.component';

@Component({
  selector: 'app-categorias',
  templateUrl: './categorias.component.html',
  styleUrls: ['./categorias.component.scss'],
  standalone: false
})
export class CategoriasComponent implements OnInit {
  displayedColumns = ['nombre', 'descripcion', 'acciones'];
  loading = true;
  rows: Categoria[] = [];

  constructor(
    private readonly categorias: CategoriaService,
    private readonly dialog: MatDialog,
    private readonly snack: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.categorias.list().subscribe({
      next: (rows) => {
        this.rows = rows;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.snack.open('No se pudieron cargar las categorías', 'Cerrar', { duration: 4000 });
      }
    });
  }

  nueva(): void {
    const ref = this.dialog.open(CategoriaDialogComponent, { width: '480px' });
    ref.afterClosed().subscribe((saved) => {
      if (saved) {
        this.refresh();
      }
    });
  }

  editar(row: Categoria): void {
    const ref = this.dialog.open(CategoriaDialogComponent, { width: '480px', data: { categoria: row } });
    ref.afterClosed().subscribe((saved) => {
      if (saved) {
        this.refresh();
      }
    });
  }

  eliminar(row: Categoria): void {
    const ref = this.dialog.open(DialogoConfirmacionComponente, {
      width: '400px',
      data: {
        title: 'Eliminar categoría',
        message: `¿Eliminar «${row.nombre}»?`,
        confirmLabel: 'Eliminar',
        confirmColor: 'warn' as const
      }
    });
    ref.afterClosed().subscribe((ok) => {
      if (!ok) {
        return;
      }
      this.categorias.delete(row.id).subscribe({
        next: () => {
          this.snack.open('Categoría eliminada', 'OK', { duration: 2500 });
          this.refresh();
        },
        error: (err) => {
          const d = err?.error?.detail;
          this.snack.open(typeof d === 'string' ? d : 'No se pudo eliminar la categoría', 'Cerrar', {
            duration: 5000
          });
        }
      });
    });
  }
}
