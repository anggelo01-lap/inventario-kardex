import { AfterViewInit, Component, OnInit, ViewChild } from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { MatTableDataSource } from '@angular/material/table';
import { MatSnackBar } from '@angular/material/snack-bar';
import { UserOut } from '../../nucleo/modelos/modelos-api';
import { UsuarioService } from '../../nucleo/servicios/usuario.servicio';

@Component({
  selector: 'app-usuarios',
  templateUrl: './usuarios.component.html',
  styleUrls: ['./usuarios.component.scss'],
  standalone: false
})
export class UsuariosComponent implements OnInit, AfterViewInit {
  displayedColumns = ['id', 'username', 'full_name', 'email', 'role', 'is_active'];
  dataSource = new MatTableDataSource<UserOut>([]);
  loading = true;
  updatingId: number | null = null;

  @ViewChild(MatPaginator) paginator!: MatPaginator;

  constructor(
    private readonly usuarios: UsuarioService,
    private readonly snack: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
  }

  refresh(): void {
    this.loading = true;
    this.usuarios.list().subscribe({
      next: (rows) => {
        this.dataSource.data = rows;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        const d = err?.error?.detail;
        this.snack.open(typeof d === 'string' ? d : 'No se pudieron cargar los usuarios', 'Cerrar');
      }
    });
  }

  cambiarRol(row: UserOut, role: string): void {
    const r = role as 'admin' | 'usuario';
    if (row.role === r) {
      return;
    }
    this.updatingId = row.id;
    this.usuarios.updateRole(row.id, r).subscribe({
      next: (u) => {
        this.updatingId = null;
        const idx = this.dataSource.data.findIndex((x) => x.id === u.id);
        if (idx >= 0) {
          const next = [...this.dataSource.data];
          next[idx] = u;
          this.dataSource.data = next;
        }
        this.snack.open('Rol actualizado', 'OK', { duration: 3000 });
      },
      error: (err) => {
        this.updatingId = null;
        const d = err?.error?.detail;
        this.snack.open(typeof d === 'string' ? d : 'No se pudo actualizar el rol', 'Cerrar', { duration: 5000 });
        this.refresh();
      }
    });
  }

  cambiarActivo(row: UserOut, active: boolean): void {
    if (row.is_active === active) {
      return;
    }
    this.updatingId = row.id;
    this.usuarios.updateActive(row.id, active).subscribe({
      next: (u) => {
        this.updatingId = null;
        const idx = this.dataSource.data.findIndex((x) => x.id === u.id);
        if (idx >= 0) {
          const next = [...this.dataSource.data];
          next[idx] = u;
          this.dataSource.data = next;
        }
        this.snack.open('Estado actualizado', 'OK', { duration: 3000 });
      },
      error: (err) => {
        this.updatingId = null;
        const d = err?.error?.detail;
        this.snack.open(typeof d === 'string' ? d : 'No se pudo actualizar el estado', 'Cerrar', { duration: 5000 });
        this.refresh();
      }
    });
  }
}
