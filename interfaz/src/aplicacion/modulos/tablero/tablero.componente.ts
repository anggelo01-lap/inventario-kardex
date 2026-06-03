// Tablero
import { Component, OnInit } from '@angular/core';
import { ChartConfiguration, ChartData } from 'chart.js';
import {
  DashboardMetric,
  DashboardMovimientoReciente,
  DashboardResumen,
  DashboardTopProducto
} from '../../nucleo/modelos/modelos-api';
import {
  DashboardAgrupacion,
  DashboardPeriodo,
  DashboardService
} from '../../nucleo/servicios/tablero.servicio';

interface DashboardPeriodOption {
  value: DashboardPeriodo;
  label: string;
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './tablero.componente.html',
  styleUrls: ['./tablero.componente.scss'],
  standalone: false
})
export class DashboardComponent implements OnInit {
  readonly periodOptions: DashboardPeriodOption[] = [
    { value: 'all', label: 'Todo' },
    { value: '7d', label: 'Ultimos 7 dias' },
    { value: '30d', label: 'Ultimos 30 dias' },
    { value: '12m', label: 'Ultimos 12 meses' },
    { value: 'today', label: 'Hoy' }
  ];

  loading = true;
  error: string | null = null;
  resumen: DashboardResumen | null = null;
  periodo: DashboardPeriodo = 'all';
  agrupacion: DashboardAgrupacion = 'auto';
  valorTotalInventario: number = 0;
  totalProductosInventario: number = 0;

  salesChartData: ChartData<'line'> = {
    labels: [],
    datasets: [
      {
        data: [],
        label: 'Salidas (unidades)',
        borderColor: '#c8102e',
        backgroundColor: 'rgba(200,16,46,0.07)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.42,
        pointRadius: 4,
        pointHoverRadius: 7,
        pointBackgroundColor: '#c8102e',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointHoverBackgroundColor: '#7e0a1b',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
      }
    ]
  };

  salesChartOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#94a3b8',
        bodyColor: '#f1f5f9',
        borderColor: 'rgba(148,163,184,0.15)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 12,
        displayColors: false,
        callbacks: {
          label: (ctx) => ` ${Math.round(ctx.parsed.y || 0)} unidades salidas`
        }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        border: { display: false },
        ticks: { color: '#94a3b8', font: { size: 12, family: "'Inter', sans-serif" } }
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(241,245,249,1)' },
        border: { display: false, dash: [4, 4] },
        ticks: {
          color: '#94a3b8',
          font: { size: 12, family: "'Inter', sans-serif" },
          callback: (value) => `${value} uds`
        }
      }
    }
  };

  constructor(private readonly dashboard: DashboardService) {}

  ngOnInit(): void {
    this.loadDashboard();
  }

  setPeriodo(periodo: DashboardPeriodo): void {
    if (this.periodo === periodo) {
      return;
    }
    this.periodo = periodo;
    this.loadDashboard();
  }

  toggleAgrupacion(): void {
    this.agrupacion = this.agrupacion === 'dia' ? 'mes' : 'dia';
    this.loadDashboard();
  }

  resetFiltros(): void {
    this.periodo = 'all';
    this.agrupacion = 'auto';
    this.loadDashboard();
  }

  get agrupacionLabel(): string {
    const actual = this.resumen?.agrupacion ?? (this.agrupacion === 'auto' ? 'mes' : this.agrupacion);
    return actual === 'dia' ? 'Por dia' : 'Por mes';
  }

  get periodLabel(): string {
    const current = this.resumen?.periodo ?? this.periodo;
    return this.periodOptions.find((item) => item.value === current)?.label ?? 'Periodo actual';
  }

  get chartHasData(): boolean {
    return !!this.resumen?.serie_ventas.length;
  }

  get topCantidad(): DashboardTopProducto[] {
    return this.resumen?.top_productos_cantidad ?? [];
  }

  get topMonto(): DashboardTopProducto[] {
    return this.resumen?.top_productos_monto ?? [];
  }

  get movimientos(): DashboardMovimientoReciente[] {
    return this.resumen?.movimientos_recientes ?? [];
  }

  comparisonText(metric: DashboardMetric): string {
    if (metric.variacion_pct == null) {
      return 'Sin base previa comparable';
    }
    const sign = metric.variacion_pct > 0 ? '+' : '';
    return `${sign}${metric.variacion_pct.toFixed(1)}% vs periodo anterior`;
  }

  comparisonClass(metric: DashboardMetric): string {
    if (metric.variacion_pct == null) {
      return 'is-neutral';
    }
    if (metric.variacion_pct > 0) {
      return 'is-up';
    }
    if (metric.variacion_pct < 0) {
      return 'is-down';
    }
    return 'is-neutral';
  }

  movementTypeLabel(tipo: string): string {
    if (tipo === 'entrada') {
      return 'Entrada';
    }
    if (tipo === 'salida') {
      return 'Salida';
    }
    return 'Ajuste';
  }

  movementTypeClass(tipo: string): string {
    if (tipo === 'entrada') {
      return 'type-chip type-chip--in';
    }
    if (tipo === 'salida') {
      return 'type-chip type-chip--out';
    }
    return 'type-chip type-chip--adjust';
  }

  formatCurrency(value: number | null | undefined): string {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value ?? 0);
  }

  formatCompact(value: number): string {
    return new Intl.NumberFormat('es-PE', {
      notation: value >= 1000 ? 'compact' : 'standard',
      maximumFractionDigits: 1
    }).format(value);
  }

  trackByProducto(_: number, item: DashboardTopProducto): number {
    return item.producto_id;
  }

  trackByMovimiento(_: number, item: DashboardMovimientoReciente): number {
    return item.id;
  }

  private loadDashboard(): void {
    this.loading = true;
    this.error = null;

    this.dashboard.resumen(this.periodo, this.agrupacion).subscribe({
      next: (resumen) => {
        this.resumen = resumen;
        if (this.periodo === 'all' || this.valorTotalInventario === 0) {
          this.valorTotalInventario = resumen.ventas_estimadas.valor;
          this.totalProductosInventario = resumen.total_productos;
        }
        this.salesChartData = {
          labels: resumen.serie_ventas.map((point) => point.etiqueta),
          datasets: [
            {
              ...this.salesChartData.datasets[0],
              data: resumen.serie_ventas.map((point) => point.valor)
            }
          ]
        };
        this.loading = false;
      },
      error: () => {
        this.error = 'No se pudo cargar el dashboard con informacion real del backend.';
        this.loading = false;
      }
    });
  }
}
