import { Component, Inject, Optional } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Categoria } from '../../nucleo/modelos/modelos-api';
import { CategoriaService } from '../../nucleo/servicios/categoria.servicio';

export interface CategoriaDialogData {
  categoria?: Categoria;
}

@Component({
  selector: 'app-categoria-dialog',
  templateUrl: './categoria-dialog.component.html',
  styleUrls: ['./categoria-dialog.component.scss'],
  standalone: false
})
export class CategoriaDialogComponent {
  saving = false;
  private readonly editingId: number | null = null;

  form = this.fb.nonNullable.group({
    nombre: ['', Validators.required],
    descripcion: ['']
  });

  constructor(
    private readonly fb: FormBuilder,
    private readonly categorias: CategoriaService,
    private readonly dialogRef: MatDialogRef<CategoriaDialogComponent, Categoria | undefined>,
    private readonly snack: MatSnackBar,
    @Optional() @Inject(MAT_DIALOG_DATA) data: CategoriaDialogData | null
  ) {
    const c = data?.categoria;
    if (c) {
      this.editingId = c.id;
      this.form.patchValue({
        nombre: c.nombre,
        descripcion: c.descripcion ?? ''
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
    const v = this.form.getRawValue();
    this.saving = true;

    if (this.editingId != null) {
      this.categorias
        .update(this.editingId, {
          nombre: v.nombre.trim(),
          descripcion: v.descripcion.trim() || null
        })
        .subscribe({
          next: (res) => {
            this.saving = false;
            this.dialogRef.close(res);
          },
          error: (err) => {
            this.saving = false;
            const d = err?.error?.detail;
            this.snack.open(typeof d === 'string' ? d : 'No se pudo actualizar la categoría', 'Cerrar', {
              duration: 5000
            });
          }
        });
      return;
    }

    this.categorias
      .create({
        nombre: v.nombre.trim(),
        descripcion: v.descripcion.trim() || null
      })
      .subscribe({
        next: (res) => {
          this.saving = false;
          this.dialogRef.close(res);
        },
        error: (err) => {
          this.saving = false;
          const d = err?.error?.detail;
          this.snack.open(typeof d === 'string' ? d : 'No se pudo crear la categoría', 'Cerrar', {
            duration: 5000
          });
        }
      });
  }
}
