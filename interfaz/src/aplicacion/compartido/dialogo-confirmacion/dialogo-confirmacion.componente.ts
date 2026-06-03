import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmColor?: 'primary' | 'accent' | 'warn';
}

@Component({
  selector: 'app-confirm-dialog',
  templateUrl: './dialogo-confirmacion.componente.html',
  styleUrls: ['./dialogo-confirmacion.componente.scss'],
  standalone: false
})
export class DialogoConfirmacionComponente {
  constructor(
    public readonly dialogRef: MatDialogRef<DialogoConfirmacionComponente, boolean>,
    @Inject(MAT_DIALOG_DATA) public readonly data: ConfirmDialogData
  ) {}

  get confirmColor(): 'primary' | 'accent' | 'warn' {
    return this.data.confirmColor ?? 'warn';
  }
}
