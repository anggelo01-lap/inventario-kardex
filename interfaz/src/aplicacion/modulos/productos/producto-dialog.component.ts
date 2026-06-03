import { Component, Inject, OnDestroy, Optional } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable, of } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { Categoria, Producto, ProductoCreate, ProductoUpdate, Proveedor } from '../../nucleo/modelos/modelos-api';
import { CategoriaService } from '../../nucleo/servicios/categoria.servicio';
import { ProductoService } from '../../nucleo/servicios/producto.servicio';
import { ProveedorService } from '../../nucleo/servicios/proveedor.servicio';

export interface ProductoDialogData {
  producto?: Producto;
}

@Component({
  selector: 'app-producto-dialog',
  templateUrl: './producto-dialog.component.html',
  styleUrls: ['./producto-dialog.component.scss'],
  standalone: false
})
export class ProductoDialogComponent implements OnDestroy {
  saving = false;
  uploadingImage = false;
  private editingId: number | null = null;
  private selectedImageFile: File | null = null;
  private localPreviewUrl: string | null = null;
  categorias: Categoria[] = [];
  proveedores: Proveedor[] = [];
  readonly tipos = [
    { value: 'repuesto', label: 'Repuesto' },
    { value: 'producto', label: 'Producto' },
    { value: 'insumo', label: 'Insumo' }
  ] as const;

  form = this.fb.nonNullable.group({
    codigo: ['', Validators.required],
    nombre: ['', Validators.required],
    descripcion: [''],
    categoria_id: [null as number | null, Validators.required],
    proveedor_id: [null as number | null],
    tipo: ['producto' as 'repuesto' | 'producto' | 'insumo', Validators.required],
    image_url: [''],
    precio: [0, [Validators.required, Validators.min(0)]],
    stock_minimo: [0, [Validators.required, Validators.min(0)]],
    stock_inicial: [0, [Validators.required, Validators.min(0)]]
  });

  constructor(
    private readonly fb: FormBuilder,
    private readonly dialogRef: MatDialogRef<ProductoDialogComponent, Producto | undefined>,
    private readonly productos: ProductoService,
    private readonly categoriasService: CategoriaService,
    private readonly proveedoresService: ProveedorService,
    private readonly snack: MatSnackBar,
    @Optional() @Inject(MAT_DIALOG_DATA) data: ProductoDialogData | null
  ) {
    this.categoriasService.list().subscribe({
      next: (rows) => (this.categorias = rows),
      error: () => this.snack.open('No se pudieron cargar las categorias', 'Cerrar', { duration: 4000 })
    });
    this.proveedoresService.list().subscribe({
      next: (rows) => (this.proveedores = rows),
      error: () => this.snack.open('No se pudieron cargar los proveedores', 'Cerrar', { duration: 4000 })
    });

    const producto = data?.producto;
    if (producto) {
      this.editingId = producto.id;
      this.form.patchValue({
        codigo: producto.codigo,
        nombre: producto.nombre,
        descripcion: producto.descripcion ?? '',
        categoria_id: producto.categoria_id,
        proveedor_id: producto.proveedor_id,
        tipo: producto.tipo,
        image_url: producto.image_url ?? '',
        precio: producto.precio ?? 0,
        stock_minimo: producto.stock_minimo ?? 0
      });
      this.form.get('stock_inicial')?.disable();
    }
  }

  get isEdit(): boolean {
    return this.editingId != null;
  }

  get previewUrl(): string | null {
    if (this.localPreviewUrl) {
      return this.localPreviewUrl;
    }
    return this.productos.resolveImageUrl(this.form.controls.image_url.value);
  }

  get selectedImageName(): string | null {
    return this.selectedImageFile?.name ?? null;
  }

  ngOnDestroy(): void {
    this.revokeLocalPreview();
  }

  cancel(): void {
    this.dialogRef.close();
  }

  onImageSelected(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.[0] ?? null;
    if (!file) {
      return;
    }
    if (!file.type.startsWith('image/')) {
      this.snack.open('Selecciona un archivo de imagen valido', 'Cerrar', { duration: 4000 });
      if (input) {
        input.value = '';
      }
      return;
    }

    this.selectedImageFile = file;
    this.form.controls.image_url.setValue('');
    this.revokeLocalPreview();
    this.localPreviewUrl = URL.createObjectURL(file);
    if (input) {
      input.value = '';
    }
  }

  clearImage(): void {
    this.selectedImageFile = null;
    this.form.controls.image_url.setValue('');
    this.revokeLocalPreview();
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving = true;
    this.runImageUploadIfNeeded()
      .pipe(switchMap((imageUrl) => this.persistProducto(imageUrl)))
      .subscribe({
        next: (producto) => {
          this.saving = false;
          this.dialogRef.close(producto);
        },
        error: (err) => {
          this.saving = false;
          this.uploadingImage = false;
          const detail = err?.error?.detail;
          this.snack.open(typeof detail === 'string' ? detail : this.defaultErrorMessage(), 'Cerrar', {
            duration: 5000
          });
        }
      });
  }

  private runImageUploadIfNeeded(): Observable<string | null> {
    if (!this.selectedImageFile) {
      return of(this.form.controls.image_url.value?.trim() || null);
    }

    this.uploadingImage = true;
    return this.productos.uploadImage(this.selectedImageFile).pipe(
      switchMap((response) => {
        this.uploadingImage = false;
        return of(response.image_url);
      })
    );
  }

  private persistProducto(imageUrl: string | null): Observable<Producto> {
    const value = this.form.getRawValue();

    if (this.editingId != null) {
      const payload: ProductoUpdate = {
        codigo: value.codigo.trim(),
        nombre: value.nombre.trim(),
        descripcion: value.descripcion?.trim() || null,
        categoria_id: value.categoria_id ?? undefined,
        proveedor_id: value.proveedor_id,
        tipo: value.tipo,
        image_url: imageUrl,
        precio: value.precio,
        stock_minimo: value.stock_minimo
      };
      return this.productos.update(this.editingId, payload);
    }

    const payload: ProductoCreate = {
      codigo: value.codigo.trim(),
      nombre: value.nombre.trim(),
      descripcion: value.descripcion?.trim() || null,
      categoria_id: value.categoria_id!,
      proveedor_id: value.proveedor_id,
      tipo: value.tipo,
      image_url: imageUrl,
      precio: value.precio,
      stock_minimo: value.stock_minimo,
      stock_inicial: value.stock_inicial
    };
    return this.productos.create(payload);
  }

  private defaultErrorMessage(): string {
    return this.isEdit ? 'No se pudo actualizar el producto' : 'No se pudo crear el producto';
  }

  private revokeLocalPreview(): void {
    if (this.localPreviewUrl) {
      URL.revokeObjectURL(this.localPreviewUrl);
      this.localPreviewUrl = null;
    }
  }
}
