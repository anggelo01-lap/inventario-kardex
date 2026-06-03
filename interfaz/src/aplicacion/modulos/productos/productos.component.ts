// Productos / Inventario
import { Component, OnInit } from '@angular/core';
import { FormControl } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { PageEvent } from '@angular/material/paginator';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { MovimientoLista, Producto } from '../../nucleo/modelos/modelos-api';
import { AuthService } from '../../nucleo/servicios/autenticacion.servicio';
import { ExportService } from '../../nucleo/servicios/exportacion.servicio';
import { MovimientoService } from '../../nucleo/servicios/movimiento.servicio';
import { ProductoService } from '../../nucleo/servicios/producto.servicio';
import { DialogoConfirmacionComponente } from '../../compartido/dialogo-confirmacion/dialogo-confirmacion.componente';
import { ProductoDialogComponent } from './producto-dialog.component';

type EstadoFiltro = 'all' | 'ok' | 'low' | 'out';
type TipoFiltro = 'all' | 'producto' | 'repuesto' | 'insumo';
type VistaInventario = 'grid' | 'dense';

@Component({
  selector: 'app-productos',
  templateUrl: './productos.component.html',
  styleUrls: ['./productos.component.scss'],
  standalone: false
})
export class ProductosComponent implements OnInit {
  loading = true;
  exporting = false;
  detailLoading = false;
  searchCtrl = new FormControl<string>('', { nonNullable: true });

  productosBase: Producto[] = [];
  productosFiltrados: Producto[] = [];
  movimientosDetalle: MovimientoLista[] = [];
  productoSeleccionado: Producto | null = null;
  pageSize = 12;
  pageIndex = 0;
  readonly pageSizeOptions = [8, 12, 24, 36];

  estadoFilter: EstadoFiltro = 'all';
  tipoFilter: TipoFiltro = 'all';
  categoriaFilter = 'all';
  proveedorFilter = 'all';
  vista: VistaInventario = 'grid';

  constructor(
    private readonly productos: ProductoService,
    private readonly movimientos: MovimientoService,
    private readonly dialog: MatDialog,
    private readonly snack: MatSnackBar,
    private readonly auth: AuthService,
    private readonly router: Router,
    private readonly exportSvc: ExportService
  ) {}

  get isAdmin(): boolean {
    return this.auth.isAdmin();
  }

  get hasRows(): boolean {
    return this.productosFiltrados.length > 0;
  }

  get productosPagina(): Producto[] {
    const start = this.pageIndex * this.pageSize;
    return this.productosFiltrados.slice(start, start + this.pageSize);
  }

  get categoriasDisponibles(): string[] {
    return [...new Set(this.productosBase.map((row) => row.categoria?.nombre).filter((row): row is string => !!row))].sort(
      (a, b) => a.localeCompare(b)
    );
  }

  get proveedoresDisponibles(): string[] {
    return [...new Set(this.productosBase.map((row) => row.proveedor?.nombre).filter((row): row is string => !!row))].sort(
      (a, b) => a.localeCompare(b)
    );
  }

  get totalProductos(): number {
    return this.productosFiltrados.length;
  }

  get productosBajoStock(): number {
    return this.productosFiltrados.filter((row) => this.stockStatus(row) === 'low').length;
  }

  get productosSinStock(): number {
    return this.productosFiltrados.filter((row) => this.stockStatus(row) === 'out').length;
  }

  get valorInventario(): number {
    return this.productosFiltrados.reduce((acc, row) => acc + row.stock_actual * row.precio, 0);
  }

  ngOnInit(): void {
    this.searchCtrl.valueChanges.pipe(debounceTime(300), distinctUntilChanged()).subscribe(() => {
      this.refresh();
    });
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    const q = this.searchCtrl.value?.trim() || undefined;
    const selectedId = this.productoSeleccionado?.id ?? null;
    this.productos.list(q).subscribe({
      next: (rows) => {
        this.productosBase = rows;
        this.loading = false;
        this.applyFilters();

        if (selectedId != null) {
          const sameProduct = this.productosBase.find((row) => row.id === selectedId) ?? null;
          if (sameProduct) {
            this.selectProduct(sameProduct);
            return;
          }
        }

        if (this.productosFiltrados.length > 0) {
          this.selectProduct(this.productosFiltrados[0]);
        } else {
          this.productoSeleccionado = null;
          this.movimientosDetalle = [];
        }
      },
      error: () => {
        this.loading = false;
        this.snack.open('No se pudieron cargar los productos', 'Cerrar');
      }
    });
  }

  applyFilters(): void {
    this.productosFiltrados = this.productosBase.filter((row) => {
      if (this.estadoFilter !== 'all' && this.stockStatus(row) !== this.estadoFilter) {
        return false;
      }
      if (this.tipoFilter !== 'all' && row.tipo !== this.tipoFilter) {
        return false;
      }
      if (this.categoriaFilter !== 'all' && row.categoria?.nombre !== this.categoriaFilter) {
        return false;
      }
      if (this.proveedorFilter !== 'all' && row.proveedor?.nombre !== this.proveedorFilter) {
        return false;
      }
      return true;
    });

    const maxPageIndex = Math.max(0, Math.ceil(this.productosFiltrados.length / this.pageSize) - 1);
    this.pageIndex = Math.min(this.pageIndex, maxPageIndex);

    if (this.productoSeleccionado && !this.productosFiltrados.some((row) => row.id === this.productoSeleccionado?.id)) {
      this.productoSeleccionado = null;
      this.movimientosDetalle = [];
    }

    if (!this.productoSeleccionado && this.productosFiltrados.length > 0) {
      this.selectProduct(this.productosFiltrados[0]);
    }
  }

  setEstadoFilter(value: EstadoFiltro): void {
    this.estadoFilter = value;
    this.applyFilters();
  }

  setVista(value: VistaInventario): void {
    this.vista = value;
  }

  clearFilters(): void {
    this.estadoFilter = 'all';
    this.tipoFilter = 'all';
    this.categoriaFilter = 'all';
    this.proveedorFilter = 'all';
    this.applyFilters();
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;

    if (this.productosPagina.length > 0 && !this.productosPagina.some((row) => row.id === this.productoSeleccionado?.id)) {
      this.selectProduct(this.productosPagina[0]);
    }
  }

  nuevo(): void {
    const ref = this.dialog.open(ProductoDialogComponent, { width: '520px', data: {} });
    ref.afterClosed().subscribe((saved) => {
      if (saved) {
        this.snack.open('Producto creado', 'OK', { duration: 3000 });
        this.refresh();
      }
    });
  }

  editar(row: Producto): void {
    const ref = this.dialog.open(ProductoDialogComponent, {
      width: '520px',
      data: { producto: row }
    });
    ref.afterClosed().subscribe((saved) => {
      if (saved) {
        this.snack.open('Producto actualizado', 'OK', { duration: 3000 });
        this.refresh();
      }
    });
  }

  selectProduct(row: Producto): void {
    this.productoSeleccionado = row;
    this.loadRecentMovements(row.id);
  }

  loadRecentMovements(productoId: number): void {
    this.detailLoading = true;
    this.movimientos.list({ producto_id: productoId, limit: 6 }).subscribe({
      next: (rows) => {
        this.movimientosDetalle = rows;
        this.detailLoading = false;
      },
      error: () => {
        this.movimientosDetalle = [];
        this.detailLoading = false;
        this.snack.open('No se pudo cargar el historial del producto', 'Cerrar', { duration: 4000 });
      }
    });
  }

  verKardex(row: Producto): void {
    void this.router.navigate(['/kardex'], { queryParams: { producto_id: row.id } });
  }

  registrarMovimiento(row: Producto, tipo: 'entrada' | 'salida'): void {
    void this.router.navigate(['/movimientos'], {
      queryParams: { producto_id: row.id, tipo }
    });
  }

  exportarCatalogo(): void {
    this.exporting = true;
    this.exportSvc.downloadProductosXlsx().subscribe({
      next: (blob) => {
        this.exporting = false;
        this.exportSvc.saveBlob(blob, 'productos.xlsx');
      },
      error: () => {
        this.exporting = false;
        this.snack.open('Error al exportar el catalogo', 'Cerrar');
      }
    });
  }

  eliminar(row: Producto): void {
    const ref = this.dialog.open(DialogoConfirmacionComponente, {
      width: '400px',
      data: {
        title: 'Eliminar producto',
        message: `Eliminar "${row.nombre}" (${row.codigo})? No debe tener movimientos en el Kardex.`,
        confirmLabel: 'Eliminar',
        confirmColor: 'warn' as const
      }
    });
    ref.afterClosed().subscribe((ok) => {
      if (!ok) {
        return;
      }
      this.productos.delete(row.id).subscribe({
        next: () => {
          this.snack.open('Producto eliminado', 'OK', { duration: 3000 });
          this.refresh();
        },
        error: (err) => {
          const d = err?.error?.detail;
          this.snack.open(typeof d === 'string' ? d : 'No se pudo eliminar', 'Cerrar', { duration: 5000 });
        }
      });
    });
  }

  imageLabel(row: Producto): string {
    return row.image_url ? `Imagen de ${row.nombre}` : 'Sin imagen';
  }

  imageSrc(row: Producto): string | null {
    return this.productos.resolveImageUrl(row.image_url);
  }

  stockStatus(row: Producto): 'ok' | 'low' | 'out' {
    if (row.stock_actual <= 0) {
      return 'out';
    }
    if (row.stock_minimo > 0 && row.stock_actual <= row.stock_minimo) {
      return 'low';
    }
    return 'ok';
  }

  stockStatusLabel(row: Producto): string {
    const status = this.stockStatus(row);
    if (status === 'out') {
      return 'Sin stock';
    }
    if (status === 'low') {
      return 'Bajo stock';
    }
    return 'Stock saludable';
  }

  stockStatusIcon(row: Producto): string {
    const status = this.stockStatus(row);
    if (status === 'out') {
      return 'dangerous';
    }
    if (status === 'low') {
      return 'warning';
    }
    return 'verified';
  }

  stockProgress(row: Producto): number {
    if (row.stock_actual <= 0) {
      return 0;
    }
    const referencia = row.stock_minimo > 0 ? row.stock_minimo * 2 : Math.max(row.stock_actual, 1);
    return Math.max(6, Math.min(100, Math.round((row.stock_actual / referencia) * 100)));
  }

  productValue(row: Producto): number {
    return row.stock_actual * row.precio;
  }

  formatInventoryValue(value: number): string {
    if (value >= 1_000_000) {
      return `PEN ${(value / 1_000_000).toFixed(1)}M`;
    }
    if (value >= 1_000) {
      return `PEN ${(value / 1_000).toFixed(1)}K`;
    }
    return `PEN ${value.toFixed(0)}`;
  }

  tipoLabel(row: Producto): string {
    if (row.tipo === 'repuesto') {
      return 'Repuesto';
    }
    if (row.tipo === 'insumo') {
      return 'Insumo';
    }
    return 'Producto';
  }

  recentMovementTitle(row: MovimientoLista): string {
    const base = `${row.tipo} x${row.cantidad}`;
    if (row.cliente_nombre) {
      return `${base} · ${row.cliente_nombre}`;
    }
    return base;
  }

  recentMovementStock(row: MovimientoLista): string {
    if (row.stock_anterior == null || row.stock_posterior == null) {
      return 'Sin detalle de stock';
    }
    return `${row.stock_anterior} -> ${row.stock_posterior}`;
  }
}
