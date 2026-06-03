// Kardex
import { AfterViewInit, Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormBuilder, FormControl } from '@angular/forms';
import { MatPaginator } from '@angular/material/paginator';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged, Subscription } from 'rxjs';
import { MovimientoLista, Producto } from '../../nucleo/modelos/modelos-api';
import { AuthService } from '../../nucleo/servicios/autenticacion.servicio';
import { ExportService } from '../../nucleo/servicios/exportacion.servicio';
import { MovimientoService } from '../../nucleo/servicios/movimiento.servicio';
import { ProductoService } from '../../nucleo/servicios/producto.servicio';

@Component({
  selector: 'app-kardex',
  templateUrl: './kardex.component.html',
  styleUrls: ['./kardex.component.scss'],
  standalone: false
})
export class KardexComponent implements OnInit, AfterViewInit, OnDestroy {
  displayedColumns = ['fecha_movimiento', 'producto', 'cliente', 'tipo', 'cantidad', 'stock', 'motivo', 'usuario_username'];
  dataSource = new MatTableDataSource<MovimientoLista>([]);
  searchCtrl = new FormControl<string>('', { nonNullable: true });
  productoSearchCtrl = new FormControl<string>('', { nonNullable: true });
  private rawData: MovimientoLista[] = [];
  loading = true;
  exporting = false;
  productos: Producto[] = [];
  productosFiltradosSelect: Producto[] = [];
  private readonly SELECT_LIMIT = 30;
  private readonly SELECT_LIMIT_SEARCH = 50;
  productoSearchActivo = false;

  filters = this.fb.nonNullable.group({
    producto_id: [null as number | null],
    tipo: [''],
    fecha_desde: [''],
    fecha_hasta: ['']
  });

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  private sub = new Subscription();

  constructor(
    private readonly fb: FormBuilder,
    private readonly movimientos: MovimientoService,
    private readonly productoService: ProductoService,
    private readonly auth: AuthService,
    private readonly exportSvc: ExportService,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly snack: MatSnackBar
  ) {}

  get isAdmin(): boolean {
    return this.auth.isAdmin();
  }

  get hasRows(): boolean {
    return this.dataSource.data.length > 0;
  }

  get totalMovimientos(): number {
    return this.dataSource.data.length;
  }

  get totalEntradas(): number {
    return this.dataSource.data.filter(r => r.tipo === 'entrada').length;
  }

  get totalSalidas(): number {
    return this.dataSource.data.filter(r => r.tipo === 'salida').length;
  }

  fechaDay(row: MovimientoLista): string {
    if (!row.fecha_movimiento) return '-';
    return new Date(row.fecha_movimiento).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  fechaTime(row: MovimientoLista): string {
    if (!row.fecha_movimiento) return '';
    return new Date(row.fecha_movimiento).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
  }

  rowClass(row: MovimientoLista): string {
    return `row-${row.tipo}`;
  }

  productCode(row: MovimientoLista): string {
    return row.producto_codigo ?? '-';
  }

  productName(row: MovimientoLista): string {
    return row.producto_nombre ?? '';
  }

  ngOnInit(): void {
    this.dataSource.filterPredicate = (row: MovimientoLista, filter: string) => {
      const q = filter.toLowerCase().trim();
      if (!q) return true;
      const code = (row.producto_codigo ?? '').toLowerCase();
      const name = (row.producto_nombre ?? '').toLowerCase();
      return code.includes(q) || name.includes(q);
    };

    this.sub.add(
      this.searchCtrl.valueChanges
        .pipe(debounceTime(250), distinctUntilChanged())
        .subscribe((val) => {
          this.dataSource.filter = val.trim();
          if (this.dataSource.paginator) {
            this.dataSource.paginator.firstPage();
          }
        })
    );

    this.productoService.list().subscribe({
      next: (p) => {
        this.productos = p;
        this.productosFiltradosSelect = p.slice(0, this.SELECT_LIMIT);
      },
      error: () => this.snack.open('No se pudieron cargar productos', 'Cerrar')
    });

    this.sub.add(
      this.productoSearchCtrl.valueChanges
        .pipe(debounceTime(150), distinctUntilChanged())
        .subscribe((q) => {
          const term = q.toLowerCase().trim();
          this.productoSearchActivo = term.length > 0;
          if (term) {
            this.productosFiltradosSelect = this.productos
              .filter(p => p.codigo.toLowerCase().includes(term) || p.nombre.toLowerCase().includes(term))
              .slice(0, this.SELECT_LIMIT_SEARCH);
          } else {
            this.productosFiltradosSelect = this.productos.slice(0, this.SELECT_LIMIT);
          }
        })
    );

    this.sub.add(
      this.route.queryParamMap.subscribe((q) => {
        const pid = q.get('producto_id');
        let productoId: number | null = null;
        if (pid != null && pid !== '') {
          const n = Number(pid);
          if (!Number.isNaN(n)) {
            productoId = n;
          }
        }
        this.filters.patchValue({
          producto_id: productoId,
          tipo: q.get('tipo') ?? '',
          fecha_desde: q.get('fecha_desde') ?? '',
          fecha_hasta: q.get('fecha_hasta') ?? ''
        });
        this.refresh();
      })
    );
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  applyFiltersToUrl(): void {
    const v = this.filters.getRawValue();
    const q: Record<string, string | number> = {};
    if (v.producto_id != null) {
      q['producto_id'] = v.producto_id;
    }
    if (v.fecha_desde?.trim()) {
      q['fecha_desde'] = v.fecha_desde.trim();
    }
    if (v.tipo?.trim()) {
      q['tipo'] = v.tipo.trim();
    }
    if (v.fecha_hasta?.trim()) {
      q['fecha_hasta'] = v.fecha_hasta.trim();
    }
    void this.router.navigate([], { relativeTo: this.route, queryParams: q, replaceUrl: true });
  }

  refresh(): void {
    this.loading = true;
    const v = this.filters.getRawValue();
    this.movimientos
      .list({
        producto_id: v.producto_id,
        tipo: (v.tipo?.trim() || null) as 'entrada' | 'salida' | 'ajuste' | null,
        fecha_desde: v.fecha_desde?.trim() || null,
        fecha_hasta: v.fecha_hasta?.trim() || null,
        limit: 2000
      })
      .subscribe({
        next: (rows) => {
          this.rawData = rows;
          this.dataSource.data = rows;
          this.dataSource.filter = this.searchCtrl.value.trim();
          this.loading = false;
        },
        error: () => {
          this.loading = false;
          this.snack.open('No se pudo cargar el Kardex', 'Cerrar');
        }
      });
  }

  buscar(): void {
    this.applyFiltersToUrl();
  }

  exportXlsx(): void {
    const v = this.filters.getRawValue();
    this.exporting = true;
    this.exportSvc
      .downloadMovimientosXlsx({
        producto_id: v.producto_id,
        fecha_desde: v.fecha_desde?.trim() || null,
        fecha_hasta: v.fecha_hasta?.trim() || null,
        limit: 5000
      })
      .subscribe({
        next: (blob) => {
          this.exporting = false;
          this.exportSvc.saveBlob(blob, 'movimientos.xlsx');
        },
        error: () => {
          this.exporting = false;
          this.snack.open('Error al exportar Excel', 'Cerrar');
        }
      });
  }

  exportPdf(): void {
    const v = this.filters.getRawValue();
    this.exporting = true;
    this.exportSvc
      .downloadMovimientosPdf({
        producto_id: v.producto_id,
        fecha_desde: v.fecha_desde?.trim() || null,
        fecha_hasta: v.fecha_hasta?.trim() || null,
        limit: 2000
      })
      .subscribe({
        next: (blob) => {
          this.exporting = false;
          this.exportSvc.saveBlob(blob, 'movimientos.pdf');
        },
        error: () => {
          this.exporting = false;
          this.snack.open('Error al exportar PDF', 'Cerrar');
        }
      });
  }

  productoLabel(row: MovimientoLista): string {
    const code = row.producto_codigo ?? '-';
    const name = row.producto_nombre ?? '';
    return name ? `${code} - ${name}` : code;
  }

  clienteLabel(row: MovimientoLista): string {
    return row.cliente_nombre || '-';
  }

  stockLabel(row: MovimientoLista): string {
    if (row.stock_anterior == null || row.stock_posterior == null) {
      return '-';
    }
    return `${row.stock_anterior} -> ${row.stock_posterior}`;
  }

  trackByFn(_index: number, row: MovimientoLista): number {
    return row.id;
  }
}
