import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Proveedor } from '../../nucleo/modelos/modelos-api';
import { ProveedorService } from '../../nucleo/servicios/proveedor.servicio';
import { DialogoConfirmacionComponente } from '../../compartido/dialogo-confirmacion/dialogo-confirmacion.componente';
import { ProveedorDialogComponent } from './proveedor-dialog.component';

@Component({
  selector: 'app-proveedores',
  templateUrl: './proveedores.component.html',
  styleUrls: ['./proveedores.component.scss'],
  standalone: false
})
export class ProveedoresComponent implements OnInit {
  displayedColumns = ['nombre', 'contacto', 'telefono', 'email', 'acciones'];
  loading = true;
  rows: Proveedor[] = [];

  constructor(
    private readonly proveedores: ProveedorService,
    private readonly dialog: MatDialog,
    private readonly snack: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.proveedores.list().subscribe({
      next: (rows) => {
        this.rows = rows;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.snack.open('No se pudieron cargar los proveedores', 'Cerrar', { duration: 4000 });
      }
    });
  }

  nuevo(): void {
    const ref = this.dialog.open(ProveedorDialogComponent, { width: '520px' });
    ref.afterClosed().subscribe((saved) => saved && this.refresh());
  }

  editar(row: Proveedor): void {
    const ref = this.dialog.open(ProveedorDialogComponent, { width: '520px', data: { proveedor: row } });
    ref.afterClosed().subscribe((saved) => saved && this.refresh());
  }

  eliminar(row: Proveedor): void {
    const ref = this.dialog.open(DialogoConfirmacionComponente, {
      width: '400px',
      data: {
        title: 'Eliminar proveedor',
        message: `Eliminar "${row.nombre}"?`,
        confirmLabel: 'Eliminar',
        confirmColor: 'warn' as const
      }
    });
    ref.afterClosed().subscribe((ok) => {
      if (!ok) {
        return;
      }
      this.proveedores.delete(row.id).subscribe({
        next: () => {
          this.snack.open('Proveedor eliminado', 'OK', { duration: 2500 });
          this.refresh();
        },
        error: (err) => {
          const d = err?.error?.detail;
          this.snack.open(typeof d === 'string' ? d : 'No se pudo eliminar el proveedor', 'Cerrar', {
            duration: 5000
          });
        }
      });
    });
  }
}
