"""
operations_engine.py — Costos ocultos, almacenaje extraportuario, salud de inventario y Cash-to-Cash.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

KIT_EMPAQUE_DEFAULT_CLP = 650.0


# ---------------------------------------------------------------------------
# Costos hormiga
# ---------------------------------------------------------------------------


def costo_empaque(unidades: int, kit_clp: float = KIT_EMPAQUE_DEFAULT_CLP) -> float:
    return unidades * kit_clp


# ---------------------------------------------------------------------------
# Días libres / Demurrage
# ---------------------------------------------------------------------------


@dataclass
class EstadoDiasLibres:
    fecha_eta: str
    fecha_limite: str
    dias_libres: int
    dias_transcurridos: int
    dias_restantes: int
    color: str  # verde | ambar | rojo | gris
    mensaje: str
    sobrestadia_estimada_usd: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def estado_dias_libres(fecha_eta: date, dias_libres: int, hoy: date | None = None, tarifa_dia_usd: float = 35.0, estado_embarque: str = "En Aduana") -> EstadoDiasLibres:
    hoy = hoy or date.today()
    limite = fecha_eta + timedelta(days=dias_libres)
    transcurridos = (hoy - fecha_eta).days
    restantes = (limite - hoy).days
    if estado_embarque == "En Bodega":
        return EstadoDiasLibres(fecha_eta.isoformat(), limite.isoformat(), dias_libres, transcurridos, restantes, "gris", "Retirado. Sin riesgo de sobrestadía.", 0.0)
    if hoy < fecha_eta:
        color, msg, cargo = "verde", f"Arriba en {(fecha_eta - hoy).days} días. Reloj de días libres aún no inicia.", 0.0
    elif restantes >= 3:
        color, msg, cargo = "verde", f"Quedan {restantes} días libres (hasta {limite.strftime('%d-%m-%Y')}).", 0.0
    elif restantes >= 0:
        color, msg, cargo = "ambar", (f"¡Atención! Queda {restantes} día libre." if restantes == 1 else (f"¡Atención! Quedan {restantes} días libres." if restantes > 1 else "¡Atención! Hoy es el último día libre.")) + f" Retira antes del {limite.strftime('%d-%m-%Y')}.", 0.0
    else:
        cargo = abs(restantes) * tarifa_dia_usd
        color, msg = "rojo", f"SOBRESTADÍA: {abs(restantes)} {'día vencido' if abs(restantes) == 1 else 'días vencidos'}. Cargo estimado US$ {cargo:,.0f} y creciendo.".replace(",", ".")
    return EstadoDiasLibres(fecha_eta.isoformat(), limite.isoformat(), dias_libres, transcurridos, restantes, color, msg, round(cargo, 2))


# ---------------------------------------------------------------------------
# Cobertura de stock y punto de reorden
# ---------------------------------------------------------------------------


@dataclass
class CoberturaStock:
    stock: int
    venta_diaria: float
    dias_cobertura: float
    lead_time_dias: int
    fecha_quiebre: str
    fecha_maxima_orden: str
    dias_para_ordenar: int
    color: str
    mensaje: str
    unidades_reorden_sugeridas: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def cobertura_stock(stock: int, venta_diaria: float, lead_time_dias: int, hoy: date | None = None, stock_seguridad_dias: int = 7) -> CoberturaStock:
    hoy = hoy or date.today()
    if venta_diaria <= 0:
        return CoberturaStock(stock, venta_diaria, math.inf, lead_time_dias, "-", "-", 999, "gris", "Sin historial de ventas: ingresa una venta promedio diaria para proyectar.", 0)
    dias = stock / venta_diaria
    quiebre = hoy + timedelta(days=int(dias))
    fecha_orden = quiebre - timedelta(days=lead_time_dias + stock_seguridad_dias)
    dias_para_ordenar = (fecha_orden - hoy).days
    sugeridas = int(math.ceil(venta_diaria * (lead_time_dias + 30)))  # cubre lead time + 1 mes de venta
    if dias_para_ordenar < 0:
        color = "rojo"
        msg = f"CRÍTICO: cobertura {dias:.0f} días < lead time {lead_time_dias} días. Quiebre estimado el {quiebre.strftime('%d-%m-%Y')}. Debiste ordenar hace {abs(dias_para_ordenar)} días."
    elif dias_para_ordenar <= 14:
        color = "ambar"
        msg = f"Ordena antes del {fecha_orden.strftime('%d-%m-%Y')} ({dias_para_ordenar} días) para no quebrar stock el {quiebre.strftime('%d-%m-%Y')}."
    else:
        color = "verde"
        msg = f"Cobertura {dias:.0f} días. Fecha máxima de orden: {fecha_orden.strftime('%d-%m-%Y')}."
    return CoberturaStock(stock, venta_diaria, round(dias, 1), lead_time_dias, quiebre.isoformat(), fecha_orden.isoformat(), dias_para_ordenar, color, msg, sugeridas)


# ---------------------------------------------------------------------------
# Cash-to-Cash
# ---------------------------------------------------------------------------


@dataclass
class CashToCash:
    dia_autofinanciamiento: int | None
    fecha_autofinanciamiento: str
    costo_orden_2_clp: float
    cobro_neto_diario_clp: float
    dias_retencion_pasarela: int
    mensaje: str
    curva: pd.DataFrame

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("curva", None)
        return d


def ciclo_cash_to_cash(venta_diaria_unid: float, cobro_neto_unit_clp: float, costo_orden_2_clp: float, dias_retencion: int = 14, horizonte_dias: int = 180, hoy: date | None = None) -> CashToCash:
    """Día en que los cobros acumulados (liberados) financian la orden #2 sin capital nuevo."""
    hoy = hoy or date.today()
    cobro_diario = venta_diaria_unid * cobro_neto_unit_clp
    filas = []
    dia_ok: int | None = None
    for d in range(horizonte_dias + 1):
        liberado = max(0, d - dias_retencion) * cobro_diario
        filas.append({"dia": d, "fecha": hoy + timedelta(days=d), "cobrado_acumulado": liberado, "meta_orden_2": costo_orden_2_clp})
        if dia_ok is None and liberado >= costo_orden_2_clp and costo_orden_2_clp > 0:
            dia_ok = d
    curva = pd.DataFrame(filas)
    if dia_ok is None:
        msg = f"Con esta venta diaria no alcanzas a autofinanciar la orden #2 dentro de {horizonte_dias} días."
        fecha = "-"
    else:
        fecha = (hoy + timedelta(days=dia_ok)).isoformat()
        msg = f"Puedes emitir la orden #2 el día {dia_ok} ({(hoy + timedelta(days=dia_ok)).strftime('%d-%m-%Y')}) solo con cobros ya liberados."
    return CashToCash(dia_ok, fecha, costo_orden_2_clp, round(cobro_diario), dias_retencion, msg, curva)


# ---------------------------------------------------------------------------
# Flujo de caja acumulado y break-even
# ---------------------------------------------------------------------------


def flujo_caja_acumulado(inversion_clp: float, ventas: list[dict[str, Any]], hoy: date | None = None) -> tuple[pd.DataFrame, str | None]:
    """Curva real de recuperación con las ventas registradas. Devuelve (df, fecha_break_even)."""
    hoy = hoy or date.today()
    if not ventas:
        df = pd.DataFrame({"fecha": [hoy], "flujo_acumulado": [-inversion_clp]})
        return df, None
    df = pd.DataFrame(ventas)
    df["fecha"] = pd.to_datetime(df["fecha"])
    diario = df.groupby("fecha")["total_neto"].sum().sort_index()
    inicio = min(diario.index.min(), pd.Timestamp(hoy)) - pd.Timedelta(days=1)
    serie = pd.concat([pd.Series({inicio: 0.0}), diario]).cumsum() - inversion_clp
    out = pd.DataFrame({"fecha": serie.index, "flujo_acumulado": serie.values})
    be = out.loc[out["flujo_acumulado"] >= 0, "fecha"]
    return out, (be.iloc[0].date().isoformat() if not be.empty else None)


def proyeccion_flujo(inversion_clp: float, venta_diaria_unid: float, margen_unit_clp: float, cobro_neto_unit_clp: float, dias_retencion: int, horizonte: int = 180, hoy: date | None = None) -> tuple[pd.DataFrame, int | None]:
    """Proyección teórica: caja acumulada considerando retención de pasarela. Devuelve (df, dia_break_even)."""
    hoy = hoy or date.today()
    filas, be = [], None
    for d in range(horizonte + 1):
        liberado = max(0, d - dias_retencion) * venta_diaria_unid * cobro_neto_unit_clp
        caja = -inversion_clp + liberado
        filas.append({"dia": d, "fecha": hoy + timedelta(days=d), "flujo_acumulado": caja})
        if be is None and caja >= 0:
            be = d
    return pd.DataFrame(filas), be
