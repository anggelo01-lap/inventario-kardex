import { Component, Inject, Optional } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Cliente } from '../../nucleo/modelos/modelos-api';
import { ClienteService } from '../../nucleo/servicios/cliente.servicio';

export interface ClienteDialogData {
  cliente?: Cliente;
}

@Component({
  selector: 'app-cliente-dialog',
  templateUrl: './cliente-dialog.component.html',
  styleUrls: ['./cliente-dialog.component.scss'],
  standalone: false
})
export class ClienteDialogComponent {
  saving = false;
  private editingId: number | null = null;

  form = this.fb.nonNullable.group({
    nombre: ['', Validators.required],
    documento: [''],
    telefono: [''],
    email: [''],
    direccion: [''],
    notas: ['']
  });

  constructor(
    private readonly fb: FormBuilder,
    private readonly dialogRef: MatDialogRef<ClienteDialogComponent, Cliente | undefined>,
    private readonly clientes: ClienteService,
    private readonly snack: MatSnackBar,
    @Optional() @Inject(MAT_DIALOG_DATA) data: ClienteDialogData | null
  ) {
    const c = data?.cliente;
    if (c) {
      this.editingId = c.id;
      this.form.patchValue({
        nombre: c.nombre,
        documento: c.documento ?? '',
        telefono: c.telefono ?? '',
        email: c.email ?? '',
        direccion: c.direccion ?? '',
        notas: c.notas ?? ''
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
      ? this.clientes.update(this.editingId, payload)
      : this.clientes.create(payload);

    request.subscribe({
      next: (row) => {
        this.saving = false;
        this.dialogRef.close(row);
      },
      error: (err) => {
        this.saving = false;
        const d = err?.error?.detail;
        this.snack.open(typeof d === 'string' ? d : 'No se pudo guardar el cliente', 'Cerrar', { duration: 5000 });
      }
    });
  }
}
