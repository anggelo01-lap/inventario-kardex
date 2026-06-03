import { Component, Inject, Optional } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Proveedor } from '../../nucleo/modelos/modelos-api';
import { ProveedorService } from '../../nucleo/servicios/proveedor.servicio';

export interface ProveedorDialogData {
  proveedor?: Proveedor;
}

@Component({
  selector: 'app-proveedor-dialog',
  templateUrl: './proveedor-dialog.component.html',
  styleUrls: ['./proveedor-dialog.component.scss'],
  standalone: false
})
export class ProveedorDialogComponent {
  saving = false;
  private editingId: number | null = null;

  form = this.fb.nonNullable.group({
    nombre: ['', Validators.required],
    contacto: [''],
    telefono: [''],
    email: [''],
    direccion: [''],
    notas: ['']
  });

  constructor(
    private readonly fb: FormBuilder,
    private readonly dialogRef: MatDialogRef<ProveedorDialogComponent, Proveedor | undefined>,
    private readonly proveedores: ProveedorService,
    private readonly snack: MatSnackBar,
    @Optional() @Inject(MAT_DIALOG_DATA) data: ProveedorDialogData | null
  ) {
    const p = data?.proveedor;
    if (p) {
      this.editingId = p.id;
      this.form.patchValue({
        nombre: p.nombre,
        contacto: p.contacto ?? '',
        telefono: p.telefono ?? '',
        email: p.email ?? '',
        direccion: p.direccion ?? '',
        notas: p.notas ?? ''
      });
    }
  }

  get isEdit(): boolean {
    return this.editingId != null;
  }

  cancel(): void {
    this.dialogRef.close();
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const payload = this.form.getRawValue();
    this.saving = true;

    const request = this.editingId != null
      ? this.proveedores.update(this.editingId, payload)
      : this.proveedores.create(payload);

    request.subscribe({
      next: (row) => {
        this.saving = false;
        this.dialogRef.close(row);
      },
      error: (err) => {
        this.saving = false;
        const d = err?.error?.detail;
        this.snack.open(typeof d === 'string' ? d : 'No se pudo guardar el proveedor', 'Cerrar', { duration: 5000 });
      }
    });
  }
}
