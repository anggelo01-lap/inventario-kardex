// Movimientos
import { AfterViewInit, Component, OnInit, ViewChild } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { MatPaginator } from '@angular/material/paginator';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute } from '@angular/router';
import { Cliente, MovimientoLista, Producto, Proveedor } from '../../nucleo/modelos/modelos-api';
import { ClienteService } from '../../nucleo/servicios/cliente.servicio';
import { MovimientoService } from '../../nucleo/servicios/movimiento.servicio';
import { ProductoService } from '../../nucleo/servicios/producto.servicio';
import { ProveedorService } from '../../nucleo/servicios/proveedor.servicio';

@Component({
  selector: 'app-movimientos',
  templateUrl: './movimientos.component.html',
  styleUrls: ['./movimientos.component.scss'],
  standalone: false
})
export class MovimientosComponent implements OnInit, AfterViewInit {
  displayedColumns = ['fecha_movimiento', 'producto', 'cliente', 'tipo', 'cantidad', 'stock', 'usuario_username'];
  dataSource = new MatTableDataSource<MovimientoLista>([]);
  loading = true;
  saving = false;
  productos: Producto[] = [];
  clientes: Cliente[] = [];
  proveedores: Proveedor[] = [];

  form = this.fb.nonNullable.group({
    producto_id: [null as number | null, Validators.required],
    cliente_id: [null as number | null],
    proveedor_id: [null as number | null],
    tipo: ['entrada' as 'entrada' | 'salida' | 'ajuste', Validators.required],
    cantidad: [1, [Validators.required, Validators.min(1)]],
    costo_unitario: [null as number | null],
    referencia: [''],
    motivo: [''],
    observacion: ['']
  });

  @ViewChild(MatPaginator) paginator!: MatPaginator;

  constructor(
    private readonly fb: FormBuilder,
    private readonly movimientos: MovimientoService,
    private readonly productoService: ProductoService,
    private readonly clienteService: ClienteService,
    private readonly proveedorService: ProveedorService,
    private readonly route: ActivatedRoute,
    private readonly snack: MatSnackBar
  ) {}

  get hasRows(): boolean {
    return this.dataSource.data.length > 0;
  }

  get hasProductos(): boolean {
    return this.productos.length > 0;
  }

  get tipoSeleccionado(): 'entrada' | 'salida' | 'ajuste' {
    return this.form.get('tipo')!.value;
  }

  get usaClientes(): boolean {
    return this.tipoSeleccionado === 'salida';
  }

  get usaProveedores(): boolean {
    return this.tipoSeleccionado === 'entrada';
  }

  get tercerosDisponibles(): Array<{ id: number; nombre: string }> {
    return this.usaClientes ? this.clientes : this.proveedores;
  }

  ngOnInit(): void {
    this.prefillFromQuery();

    this.form.get('producto_id')!.valueChanges.subscribe((id) => {
      const producto = this.productos.find(p => p.id === id);
      if (producto) {
        this.form.patchValue({ costo_unitario: producto.precio }, { emitEvent: false });
      }
    });
    this.form.get('tipo')!.valueChanges.subscribe((tipo) => {
      if (tipo === 'salida') {
        this.form.patchValue({ proveedor_id: null }, { emitEvent: false });
        return;
      }
      if (tipo === 'entrada') {
        this.form.patchValue({ cliente_id: null }, { emitEvent: false });
        return;
      }
      this.form.patchValue({ cliente_id: null, proveedor_id: null }, { emitEvent: false });
    });

    this.productoService.list().subscribe({
      next: (p) => {
        this.productos = p;
        const currentId = this.form.get('producto_id')!.value;
        if (currentId) {
          const prod = p.find(x => x.id === currentId);
          if (prod) this.form.patchValue({ costo_unitario: prod.precio }, { emitEvent: false });
        }
      },
      error: () => this.snack.open('No se pudieron cargar productos para el formulario', 'Cerrar')
    });
    this.clienteService.list().subscribe({
      next: (c) => (this.clientes = c),
      error: () => this.snack.open('No se pudieron cargar clientes para el formulario', 'Cerrar')
    });
    this.proveedorService.list().subscribe({
      next: (p) => (this.proveedores = p),
      error: () => this.snack.open('No se pudieron cargar proveedores para el formulario', 'Cerrar')
    });
    this.refresh();
  }

  prefillFromQuery(): void {
    const qp = this.route.snapshot.queryParamMap;
    const productoId = Number(qp.get('producto_id'));
    const tipo = qp.get('tipo');

    this.form.patchValue({
      producto_id: Number.isFinite(productoId) && productoId > 0 ? productoId : null,
      tipo: tipo === 'entrada' || tipo === 'salida' || tipo === 'ajuste' ? tipo : 'entrada'
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
  }

  refresh(): void {
    this.loading = true;
    this.movimientos.list({ limit: 500 }).subscribe({
      next: (rows) => {
        this.dataSource.data = rows;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.snack.open('No se pudieron cargar los movimientos', 'Cerrar');
      }
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    if (v.producto_id == null) {
      return;
    }
    this.saving = true;
    this.movimientos
      .create({
        producto_id: v.producto_id,
        cliente_id: this.usaClientes ? v.cliente_id : null,
        proveedor_id: this.usaProveedores ? v.proveedor_id : null,
        tipo: v.tipo,
        cantidad: v.cantidad,
        costo_unitario: v.costo_unitario,
        referencia: v.referencia?.trim() || null,
        motivo: v.motivo?.trim() || null,
        observacion: v.observacion?.trim() || null
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.snack.open('Movimiento registrado', 'OK', { duration: 3000 });
          this.form.patchValue({
            producto_id: v.producto_id,
            cliente_id: this.usaClientes ? v.cliente_id : null,
            proveedor_id: this.usaProveedores ? v.proveedor_id : null,
            tipo: v.tipo,
            cantidad: 1,
            costo_unitario: this.productos.find(p => p.id === v.producto_id)?.precio ?? null,
            referencia: '',
            motivo: '',
            observacion: ''
          });
          this.refresh();
        },
        error: (err) => {
          this.saving = false;
          const d = err?.error?.detail;
          this.snack.open(typeof d === 'string' ? d : 'Error al registrar', 'Cerrar', { duration: 5000 });
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
}
