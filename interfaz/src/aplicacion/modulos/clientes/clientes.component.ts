import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Cliente } from '../../nucleo/modelos/modelos-api';
import { ClienteService } from '../../nucleo/servicios/cliente.servicio';
import { DialogoConfirmacionComponente } from '../../compartido/dialogo-confirmacion/dialogo-confirmacion.componente';
import { ClienteDialogComponent } from './cliente-dialog.component';

@Component({
  selector: 'app-clientes',
  templateUrl: './clientes.component.html',
  styleUrls: ['./clientes.component.scss'],
  standalone: false
})
export class ClientesComponent implements OnInit {
  displayedColumns = ['nombre', 'documento', 'telefono', 'email', 'acciones'];
  loading = true;
  rows: Cliente[] = [];

  constructor(
    private readonly clientes: ClienteService,
    private readonly dialog: MatDialog,
    private readonly snack: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.clientes.list().subscribe({
      next: (rows) => {
        this.rows = rows;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.snack.open('No se pudieron cargar los clientes', 'Cerrar', { duration: 4000 });
      }
    });
  }

  nuevo(): void {
    const ref = this.dialog.open(ClienteDialogComponent, { width: '520px' });
    ref.afterClosed().subscribe((saved) => saved && this.refresh());
  }

  editar(row: Cliente): void {
    const ref = this.dialog.open(ClienteDialogComponent, { width: '520px', data: { cliente: row } });
    ref.afterClosed().subscribe((saved) => saved && this.refresh());
  }

  eliminar(row: Cliente): void {
    const ref = this.dialog.open(DialogoConfirmacionComponente, {
      width: '400px',
      data: {
        title: 'Eliminar cliente',
        message: `Eliminar "${row.nombre}"?`,
        confirmLabel: 'Eliminar',
        confirmColor: 'warn' as const
      }
    });
    ref.afterClosed().subscribe((ok) => {
      if (!ok) {
        return;
      }
      this.clientes.delete(row.id).subscribe({
        next: () => {
          this.snack.open('Cliente eliminado', 'OK', { duration: 2500 });
          this.refresh();
        },
        error: (err) => {
          const d = err?.error?.detail;
          this.snack.open(typeof d === 'string' ? d : 'No se pudo eliminar el cliente', 'Cerrar', {
            duration: 5000
          });
        }
      });
    });
  }
}
