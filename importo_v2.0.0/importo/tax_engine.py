"""
tax_engine.py — Motor tributario chileno (IVA / F29 / PPM).

- IVA Crédito Fiscal: IVA pagado en aduana (y otras compras) — se acumula a favor.
- IVA Débito Fiscal: IVA contenido en boletas/facturas emitidas.
- PPM obligatorio: 1% (tasa de inicio) sobre ventas netas del mes.
- Semáforo preventivo del F29 (vence el día 20 del mes siguiente, día 20 vía Internet).
"""
from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

TASA_IVA = 0.19
TASA_PPM_DEFAULT = 0.00125  # Pro Pyme General 2026 (Ley 21.755); Transparente 0,2 %; régimen general 1 %
DIA_VENCIMIENTO_F29 = 20


def iva_desde_bruto(monto_bruto: float) -> float:
    """IVA contenido en un monto con IVA incluido (boleta)."""
    return monto_bruto - monto_bruto / (1 + TASA_IVA)


def neto_desde_bruto(monto_bruto: float) -> float:
    return monto_bruto / (1 + TASA_IVA)


def calcular_ppm(ventas_netas: float, tasa: float = TASA_PPM_DEFAULT) -> float:
    return max(0.0, ventas_netas) * tasa


def proximo_vencimiento_f29(hoy: date | None = None) -> date:
    """El F29 del mes M vence el día 20 de M+1 (si aún no pasó el 20 de este mes, es el de este mes)."""
    hoy = hoy or date.today()
    if hoy.day <= DIA_VENCIMIENTO_F29:
        return date(hoy.year, hoy.month, DIA_VENCIMIENTO_F29)
    y, m = (hoy.year + 1, 1) if hoy.month == 12 else (hoy.year, hoy.month + 1)
    return date(y, m, min(DIA_VENCIMIENTO_F29, calendar.monthrange(y, m)[1]))


@dataclass
class ResumenF29:
    credito_fiscal: float
    debito_fiscal: float
    remanente_anterior: float
    iva_neto: float  # (+) a pagar, (−) remanente a favor
    ppm: float
    total_a_pagar: float
    remanente_siguiente: float
    color: str  # verde | ambar | rojo
    mensaje: str
    vencimiento: str
    dias_para_vencer: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resumen_f29(
    credito_fiscal: float,
    debito_fiscal: float,
    ventas_netas: float,
    remanente_anterior: float = 0.0,
    tasa_ppm: float = TASA_PPM_DEFAULT,
    hoy: date | None = None,
) -> ResumenF29:
    hoy = hoy or date.today()
    credito_total = credito_fiscal + remanente_anterior
    iva_neto = debito_fiscal - credito_total
    ppm = calcular_ppm(ventas_netas, tasa_ppm)
    venc = proximo_vencimiento_f29(hoy)
    dias = (venc - hoy).days

    if iva_neto <= 0:
        remanente = -iva_neto
        total = ppm  # el PPM siempre se paga aunque haya remanente de IVA
        if ppm > 0:
            color = "ambar"
            msg = f"Colchón fiscal a favor: ${remanente:,.0f} CLP. Solo debes pagar PPM ${ppm:,.0f} el día {venc.day}."
        else:
            color = "verde"
            msg = f"Colchón fiscal a favor: ${remanente:,.0f} CLP. Sin pago previsto el día {venc.day}."
    else:
        remanente = 0.0
        total = iva_neto + ppm
        color = "rojo"
        msg = f"Previsión a pagar el día {venc.day}: ${total:,.0f} CLP (IVA neto ${iva_neto:,.0f} + PPM ${ppm:,.0f})."
    msg = msg.replace(",", ".")
    return ResumenF29(
        credito_fiscal=round(credito_fiscal),
        debito_fiscal=round(debito_fiscal),
        remanente_anterior=round(remanente_anterior),
        iva_neto=round(iva_neto),
        ppm=round(ppm),
        total_a_pagar=round(total),
        remanente_siguiente=round(remanente),
        color=color,
        mensaje=msg,
        vencimiento=venc.isoformat(),
        dias_para_vencer=dias,
    )


def proyeccion_iva_venta(precio_bruto: float, unidades: int) -> dict[str, float]:
    """Cuánto débito fiscal genera una venta dada (útil para simular impacto en F29)."""
    total = precio_bruto * unidades
    return {"bruto": total, "neto": neto_desde_bruto(total), "iva_debito": iva_desde_bruto(total)}


def f29_mensual(mes: str, debito: float, credito: float, remanente_anterior: float, ventas_netas: float, tasa_ppm: float = TASA_PPM_DEFAULT, hoy: date | None = None) -> dict[str, Any]:
    """F29 del período `mes` (AAAA-MM): IVA determinado + PPM. El remanente arrastrado debiera reajustarse por UTM;
    aquí se toma en pesos (conservador) y se indica para que el contador aplique el reajuste."""
    y, m = int(mes[:4]), int(mes[5:7])
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    venc = date(y2, m2, min(DIA_VENCIMIENTO_F29, calendar.monthrange(y2, m2)[1]))
    r = resumen_f29(credito, debito, ventas_netas, remanente_anterior, tasa_ppm, hoy)
    d = r.to_dict()
    d.update({"periodo": mes, "vencimiento": venc.isoformat(), "dias_para_vencer": (venc - (hoy or date.today())).days,
              "lineas": [
                  {"codigo": "538", "concepto": "Débito fiscal (IVA de boletas y facturas emitidas)", "monto": round(debito)},
                  {"codigo": "504", "concepto": "Remanente de crédito fiscal mes anterior (verificar reajuste UTM)", "monto": round(remanente_anterior)},
                  {"codigo": "520/525", "concepto": "Crédito fiscal (facturas de compra + IVA de importación DIN)", "monto": round(credito)},
                  {"codigo": "89", "concepto": "IVA determinado a pagar (o 77 remanente a favor)", "monto": round(max(0.0, debito - credito - remanente_anterior))},
                  {"codigo": "563", "concepto": "Base imponible PPM (ventas netas)", "monto": round(ventas_netas)},
                  {"codigo": "62", "concepto": f"PPM obligatorio ({tasa_ppm*100:.2f} %)", "monto": round(ventas_netas * tasa_ppm)},
                  {"codigo": "91", "concepto": "Total a pagar", "monto": round(max(0.0, debito - credito - remanente_anterior) + ventas_netas * tasa_ppm)},
              ]})
    return d
