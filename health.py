"""
health.py — Salud de la empresa en simple: seis dimensiones, un puntaje 0–100 y una acción por dimensión.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import database as db
from operations_engine import cobertura_stock, estado_dias_libres
from tax_engine import resumen_f29

PUNTOS = {"verde": 100, "ambar": 50, "rojo": 0, "gris": 50}


@dataclass
class Dimension:
    nombre: str
    color: str
    valor: str
    accion: str


@dataclass
class Salud:
    puntaje: int
    color: str
    resumen: str
    dimensiones: list[Dimension] = field(default_factory=list)


def _tendencia_ventas(ventas: list[dict[str, Any]], hoy: date) -> tuple[float, float]:
    h30, h60 = hoy - timedelta(days=30), hoy - timedelta(days=60)
    ult = sum(v["total_neto"] for v in ventas if date.fromisoformat(v["fecha"]) > h30)
    ant = sum(v["total_neto"] for v in ventas if h60 < date.fromisoformat(v["fecha"]) <= h30)
    return ult, ant


def salud_empresa(lead_time: int, tasa_ppm: float, checklist_hecho: int, checklist_total: int, hoy: date | None = None) -> Salud:
    hoy = hoy or date.today()
    dims: list[Dimension] = []
    ventas = db.list_ventas()
    caja = db.resumen_caja()
    fijos = db.costos_fijos_mensuales()

    # 1. Liquidez: meses de costos fijos cubiertos con la caja en cuenta
    if fijos > 0:
        meses = caja["en_cuenta"] / fijos
        color = "verde" if meses >= 3 else "ambar" if meses >= 1 else "rojo"
        dims.append(Dimension("Liquidez", color, f"{meses:.1f} meses de costos fijos en caja", "Mantén al menos 3 meses de costos fijos; libera cobros retenidos y evita nuevas órdenes hasta lograrlo." if color != "verde" else "Caja sana: puedes financiar la próxima orden con cobros propios."))
    else:
        color = "verde" if caja["en_cuenta"] > 0 else "gris"
        dims.append(Dimension("Liquidez", color, f"Caja en cuenta {caja['en_cuenta']:,.0f}".replace(",", "."), "Registra tus costos fijos en Gastos y F29 para medir cuántos meses de operación cubres."))

    # 2. Rentabilidad: margen bruto de los últimos 30 días
    ult30 = [v for v in ventas if date.fromisoformat(v["fecha"]) > hoy - timedelta(days=30)]
    if ult30:
        bruto = sum(v["total_bruto"] for v in ult30)
        neto_sin_iva = bruto / 1.19
        utilidad = sum(v["total_neto"] - (v["total_bruto"] - v["total_bruto"] / 1.19) - v["cantidad"] * v["costo_unitario_clp"] for v in ult30)
        pct = utilidad / neto_sin_iva * 100 if neto_sin_iva else 0
        color = "verde" if pct >= 25 else "ambar" if pct >= 10 else "rojo"
        dims.append(Dimension("Rentabilidad", color, f"Margen bruto {pct:.1f} % en 30 días", "Sube precio, negocia FOB o reduce comisiones de canal: bajo 10 % no cubres imprevistos." if color == "rojo" else "Revisa mix de canales: mueve ventas al canal con mejor margen." if color == "ambar" else "Margen sano. Cuida que la publicidad no lo erosione (ROAS mínimo en Precios)."))
    else:
        dims.append(Dimension("Rentabilidad", "gris", "Sin ventas en 30 días", "Registra tus ventas para medir el margen real."))

    # 3. Ventas: tendencia
    ult, ant = _tendencia_ventas(ventas, hoy)
    if ant > 0:
        var = (ult - ant) / ant * 100
        color = "verde" if var >= 0 else "ambar" if var >= -20 else "rojo"
        dims.append(Dimension("Ventas", color, f"{var:+.0f} % vs 30 días anteriores", "Ventas cayendo: revisa precio frente al benchmark y activa publicidad con ROAS controlado." if color != "verde" else "Ventas creciendo: anticipa la orden #2 para no quebrar stock."))
    elif ult > 0:
        dims.append(Dimension("Ventas", "verde", f"{ult:,.0f} netos en 30 días".replace(",", "."), "Primer mes con ventas: registra todo para tener tendencia el próximo mes."))
    else:
        dims.append(Dimension("Ventas", "gris", "Sin historial", "Registra ventas para medir tendencia."))

    # 4. Tributario
    mes = hoy.strftime("%Y-%m")
    rm = db.resumen_f29_mensual(mes)
    f29 = resumen_f29(rm["credito"], rm["debito"], rm["ventas_netas"], rm["remanente_anterior"], tasa_ppm, hoy)
    color = "verde" if f29.color != "rojo" else ("ambar" if f29.total_a_pagar <= caja["en_cuenta"] else "rojo")
    dims.append(Dimension("Tributario", color, f"F29: {f29.total_a_pagar:,.0f} a pagar el {f29.vencimiento[8:]}-{f29.vencimiento[5:7]}".replace(",", "."), "Reserva el IVA de cada venta: no es tuyo. Si no alcanza la caja, prioriza cobros y evita gastos." if color == "rojo" else "Registra todas las facturas de gastos: cada una reduce el IVA a pagar." if color == "ambar" else "Colchón fiscal: puedes usar el crédito para financiar más stock."))

    # 5. Operación: demurrage y cobertura
    rojo = ambar = 0
    for e in db.list_embarques():
        if e["estado"] != "En Bodega":
            c = estado_dias_libres(date.fromisoformat(e["fecha_eta"]), e["dias_libres"], estado_embarque=e["estado"]).color
            rojo += c == "rojo"
            ambar += c == "ambar"
    for inv in db.list_inventario():
        vs = [v for v in ventas if v["producto_id"] == inv["id"]]
        if vs:
            dias_hist = max(1, (hoy - min(date.fromisoformat(v["fecha"]) for v in vs)).days + 1)
            c = cobertura_stock(inv["unidades_disponibles"], sum(v["cantidad"] for v in vs) / dias_hist, lead_time, hoy).color
            rojo += c == "rojo"
            ambar += c == "ambar"
    color = "rojo" if rojo else "ambar" if ambar else "verde"
    dims.append(Dimension("Operación", color, f"{rojo} {'alerta crítica' if rojo == 1 else 'alertas críticas'}, {ambar} por vencer", "Atiende hoy las alertas rojas en Operación y stock: cada día cuesta dólares o ventas perdidas." if rojo else "Programa esta semana lo que está por vencer." if ambar else "Sin alertas de almacenaje ni de stock."))

    # 6. Cumplimiento
    pct = checklist_hecho / checklist_total * 100 if checklist_total else 0
    color = "verde" if pct >= 80 else "ambar" if pct >= 40 else "rojo"
    dims.append(Dimension("Cumplimiento", color, f"{checklist_hecho} de {checklist_total} obligaciones cubiertas", "Completa el checklist en Cumplimiento (admin): la Ley 21.719 rige desde el 1-12-2026." if color != "verde" else "Cumplimiento al día. Revisa el RAT cuando cambies un proveedor."))

    puntaje = round(sum(PUNTOS[d.color] for d in dims) / len(dims))
    color_g = "verde" if puntaje >= 75 else "ambar" if puntaje >= 45 else "rojo"
    peor = [d for d in dims if d.color == "rojo"] or [d for d in dims if d.color == "ambar"]
    resumen = "Tu empresa está sana. Sigue registrando ventas y gastos para mantener la foto real." if not peor else f"Prioridad: {peor[0].nombre.lower()}. {peor[0].accion}"
    return Salud(puntaje, color_g, resumen, dims)
