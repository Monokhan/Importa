"""
customs_engine.py — Motor de valoración aduanera chilena.

Incluye:
- Cubicaje (CBM), peso volumétrico aéreo (divisor 5000) y regla marítima W/M (1 m³ = 1 ton).
- Liquidación paso a paso: FOB → Flete (+DG) → Seguro (real o presunto) → CIF → Ad-valorem
  (6% general / 0% TLC) → IVA 19% → Honorarios agente (obligatorio si CIF > US$3.000) →
  Gastos locales → Landed Cost y Factor de Internación.
- Ajuste por Incoterm 2020 (EXW / FOB / CIF / DDP).
- Pagos escalonados (30/70) con doble tipo de cambio.
- Auditoría de DIN (declarado vs calculado).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

TASA_ADVALOREM_GENERAL = 0.06
TASA_IVA = 0.19
SEGURO_PRESUNTO_PCT = 0.02
UMBRAL_AGENTE_USD = 3000.0
DIVISOR_VOLUMETRICO_AEREO = 5000.0
INCOTERMS = ["EXW", "FOB", "CIF", "DDP"]


# ---------------------------------------------------------------------------
# Cubicaje
# ---------------------------------------------------------------------------


@dataclass
class CubicajeInput:
    largo_cm: float
    ancho_cm: float
    alto_cm: float
    peso_kg: float  # peso bruto por master carton
    unidades_por_caja: int
    cajas: int


@dataclass
class CubicajeResult:
    cbm_caja: float
    cbm_total: float
    peso_bruto_total_kg: float
    peso_volumetrico_aereo_kg: float
    peso_cobrable_aereo_kg: float
    toneladas_maritimo: float
    wm_maritimo: float  # unidad de cobro LCL (mayor entre m³ y ton)
    cobra_por: str
    unidades_totales: int
    cbm_por_unidad: float
    m3_facturados: int
    cbm_libre: float
    unidades_extra_sin_costo: int
    cajas_extra_sin_costo: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calcular_cubicaje(c: CubicajeInput) -> CubicajeResult:
    cbm_caja = (c.largo_cm * c.ancho_cm * c.alto_cm) / 1_000_000
    cbm_total = cbm_caja * c.cajas
    peso_bruto = c.peso_kg * c.cajas
    vol_aereo = (c.largo_cm * c.ancho_cm * c.alto_cm / DIVISOR_VOLUMETRICO_AEREO) * c.cajas
    ton = peso_bruto / 1000
    wm = max(cbm_total, ton)
    cobra_por = "Volumen (m³)" if cbm_total >= ton else "Peso (ton)"
    unidades = c.unidades_por_caja * c.cajas
    cbm_unit = cbm_caja / c.unidades_por_caja if c.unidades_por_caja else 0.0
    # Los forwarders LCL suelen facturar el m³ redondeado hacia arriba (mínimo 1 m³)
    m3_fact = max(1, math.ceil(cbm_total - 1e-9))
    libre = max(0.0, m3_fact - cbm_total)
    cajas_extra = int(libre // cbm_caja) if cbm_caja > 0 else 0
    unidades_extra = cajas_extra * c.unidades_por_caja
    return CubicajeResult(
        cbm_caja=round(cbm_caja, 4),
        cbm_total=round(cbm_total, 4),
        peso_bruto_total_kg=round(peso_bruto, 2),
        peso_volumetrico_aereo_kg=round(vol_aereo, 2),
        peso_cobrable_aereo_kg=round(max(vol_aereo, peso_bruto), 2),
        toneladas_maritimo=round(ton, 4),
        wm_maritimo=round(wm, 4),
        cobra_por=cobra_por,
        unidades_totales=unidades,
        cbm_por_unidad=round(cbm_unit, 6),
        m3_facturados=m3_fact,
        cbm_libre=round(libre, 4),
        unidades_extra_sin_costo=unidades_extra,
        cajas_extra_sin_costo=cajas_extra,
    )


# ---------------------------------------------------------------------------
# Honorarios agente de aduanas
# ---------------------------------------------------------------------------


def honorarios_agente(cif_usd: float, tarifa_base_usd: float = 150.0, forzar: bool = False) -> tuple[float, bool, str]:
    """Devuelve (honorario_usd, obligatorio, detalle). Tarifa escalonada sobre CIF con mínimo base."""
    obligatorio = cif_usd > UMBRAL_AGENTE_USD
    if not obligatorio and not forzar:
        return 0.0, False, "CIF ≤ US$3.000: puede tramitarse vía courier/simplificado sin agente."
    if cif_usd <= 10_000:
        pct = 0.010
    elif cif_usd <= 50_000:
        pct = 0.0075
    else:
        pct = 0.005
    honorario = max(tarifa_base_usd, cif_usd * pct)
    detalle = f"max(base US${tarifa_base_usd:,.0f}; {pct*100:.2f}% × CIF)"
    return round(honorario, 2), obligatorio, detalle


# ---------------------------------------------------------------------------
# Liquidación
# ---------------------------------------------------------------------------


@dataclass
class LiquidacionInput:
    producto: str
    unidades: int
    fob_unit_usd: float
    flete_usd: float
    tipo_cambio: float
    incoterm: str = "FOB"
    tlc: bool = False
    recargo_dg_pct: float = 0.0  # % adicional sobre flete por IMO Clase 9 / baterías litio
    seguro_usd: float | None = None  # None → presunto 2% sobre FOB
    costos_origen_usd: float = 0.0  # EXW: transporte interno + despacho exportación en origen
    tarifa_agente_base_usd: float = 150.0
    forzar_agente: bool = False
    desconsolidacion_clp: float = 0.0
    almacenaje_clp: float = 0.0
    transporte_clp: float = 0.0
    otros_clp: float = 0.0
    psi_usd: float = 0.0  # inspección pre-embarque
    cbm_total: float = 0.0


@dataclass
class LiquidacionResult:
    producto: str
    incoterm: str
    unidades: int
    tipo_cambio: float
    tlc: bool
    fob_unit_usd: float
    fob_total_usd: float
    costos_origen_usd: float
    flete_base_usd: float
    recargo_dg_usd: float
    flete_usd: float
    seguro_usd: float
    seguro_es_presunto: bool
    cif_usd: float
    cif_clp: float
    tasa_advalorem: float
    advalorem_usd: float
    advalorem_clp: float
    base_iva_usd: float
    iva_usd: float
    iva_clp: float
    honorarios_usd: float
    honorarios_clp: float
    agente_obligatorio: bool
    agente_detalle: str
    psi_usd: float
    psi_clp: float
    gastos_locales_clp: float
    landed_clp: float  # sin IVA (el IVA es crédito fiscal recuperable)
    landed_usd: float
    landed_unit_clp: float
    landed_unit_usd: float
    desembolso_total_clp: float  # caja necesaria = landed + IVA
    desembolso_unit_clp: float
    factor_internacion: float
    pasos: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def liquidar(inp: LiquidacionInput) -> LiquidacionResult:
    tc = inp.tipo_cambio
    fob_total = inp.fob_unit_usd * inp.unidades
    pasos: list[dict[str, Any]] = []

    # Incoterm: qué incluye el precio del proveedor
    incoterm = inp.incoterm.upper()
    costos_origen = inp.costos_origen_usd if incoterm == "EXW" else 0.0
    fob_valorado = fob_total + costos_origen  # Aduana valora sobre FOB efectivo

    if incoterm in ("CIF", "DDP"):
        # El precio ya incluye flete y seguro: los declaramos igual para valoración
        flete_base = inp.flete_usd
        recargo = flete_base * inp.recargo_dg_pct
        flete = flete_base + recargo
        seguro = inp.seguro_usd if inp.seguro_usd is not None else fob_valorado * SEGURO_PRESUNTO_PCT
        seguro_presunto = inp.seguro_usd is None
        cif = fob_valorado  # el valor pagado ya es CIF; el desglose es informativo
        fob_valorado = cif - flete - seguro
    else:
        flete_base = inp.flete_usd
        recargo = flete_base * inp.recargo_dg_pct
        flete = flete_base + recargo
        if inp.seguro_usd is None or inp.seguro_usd <= 0:
            seguro = fob_valorado * SEGURO_PRESUNTO_PCT
            seguro_presunto = True
        else:
            seguro = inp.seguro_usd
            seguro_presunto = False
        cif = fob_valorado + flete + seguro

    pasos.append({"paso": "FOB total", "usd": fob_valorado, "clp": fob_valorado * tc})
    pasos.append({"paso": "Flete internacional" + (" (+DG)" if recargo else ""), "usd": flete, "clp": flete * tc})
    pasos.append({"paso": "Seguro " + ("presunto 2%" if seguro_presunto else "real"), "usd": seguro, "clp": seguro * tc})
    pasos.append({"paso": "= CIF", "usd": cif, "clp": cif * tc})

    tasa_adv = 0.0 if inp.tlc else TASA_ADVALOREM_GENERAL
    advalorem = 0.0 if incoterm == "DDP" else cif * tasa_adv
    base_iva = cif + advalorem
    iva = 0.0 if incoterm == "DDP" else base_iva * TASA_IVA
    pasos.append({"paso": f"Ad-valorem {tasa_adv*100:.0f}%" + (" (TLC)" if inp.tlc else ""), "usd": advalorem, "clp": advalorem * tc})
    pasos.append({"paso": "IVA 19% sobre (CIF + Ad-valorem)", "usd": iva, "clp": iva * tc})

    if incoterm == "DDP":
        honor, oblig, det = 0.0, False, "DDP: el vendedor asume despacho e impuestos."
    else:
        honor, oblig, det = honorarios_agente(cif, inp.tarifa_agente_base_usd, inp.forzar_agente)
    pasos.append({"paso": "Honorarios agente de aduana", "usd": honor, "clp": honor * tc})

    psi_clp = inp.psi_usd * tc
    pasos.append({"paso": "Inspección pre-embarque (PSI)", "usd": inp.psi_usd, "clp": psi_clp})

    gastos_locales = inp.desconsolidacion_clp + inp.almacenaje_clp + inp.transporte_clp + inp.otros_clp
    pasos.append({"paso": "Gastos locales (desconsolidación, almacenaje, transporte)", "usd": gastos_locales / tc, "clp": gastos_locales})

    landed_clp = (cif + advalorem + honor + inp.psi_usd) * tc + gastos_locales
    desembolso = landed_clp + iva * tc
    landed_usd = landed_clp / tc
    pasos.append({"paso": "= LANDED COST (sin IVA)", "usd": landed_usd, "clp": landed_clp})
    pasos.append({"paso": "= Desembolso total de caja (con IVA)", "usd": desembolso / tc, "clp": desembolso})

    fob_ref = fob_total if fob_total > 0 else 1.0
    return LiquidacionResult(
        producto=inp.producto,
        incoterm=incoterm,
        unidades=inp.unidades,
        tipo_cambio=tc,
        tlc=inp.tlc,
        fob_unit_usd=inp.fob_unit_usd,
        fob_total_usd=round(fob_valorado, 2),
        costos_origen_usd=round(costos_origen, 2),
        flete_base_usd=round(flete_base, 2),
        recargo_dg_usd=round(recargo, 2),
        flete_usd=round(flete, 2),
        seguro_usd=round(seguro, 2),
        seguro_es_presunto=seguro_presunto,
        cif_usd=round(cif, 2),
        cif_clp=round(cif * tc),
        tasa_advalorem=tasa_adv,
        advalorem_usd=round(advalorem, 2),
        advalorem_clp=round(advalorem * tc),
        base_iva_usd=round(base_iva, 2),
        iva_usd=round(iva, 2),
        iva_clp=round(iva * tc),
        honorarios_usd=honor,
        honorarios_clp=round(honor * tc),
        agente_obligatorio=oblig,
        agente_detalle=det,
        psi_usd=inp.psi_usd,
        psi_clp=round(psi_clp),
        gastos_locales_clp=round(gastos_locales),
        landed_clp=round(landed_clp),
        landed_usd=round(landed_usd, 2),
        landed_unit_clp=round(landed_clp / max(inp.unidades, 1)),
        landed_unit_usd=round(landed_usd / max(inp.unidades, 1), 2),
        desembolso_total_clp=round(desembolso),
        desembolso_unit_clp=round(desembolso / max(inp.unidades, 1)),
        factor_internacion=round(landed_usd / fob_ref, 3),
        pasos=pasos,
    )


# ---------------------------------------------------------------------------
# Pagos escalonados con doble tipo de cambio
# ---------------------------------------------------------------------------


@dataclass
class PagoEscalonado:
    fob_total_usd: float
    pct_anticipo: float  # ej. 0.30
    tc_anticipo: float
    tc_liquidacion: float


def calcular_pago_escalonado(p: PagoEscalonado) -> dict[str, float]:
    anticipo_usd = p.fob_total_usd * p.pct_anticipo
    saldo_usd = p.fob_total_usd - anticipo_usd
    anticipo_clp = anticipo_usd * p.tc_anticipo
    saldo_clp = saldo_usd * p.tc_liquidacion
    total_clp = anticipo_clp + saldo_clp
    tc_efectivo = total_clp / p.fob_total_usd if p.fob_total_usd else 0.0
    ref_clp = p.fob_total_usd * p.tc_anticipo
    return {
        "anticipo_usd": round(anticipo_usd, 2),
        "saldo_usd": round(saldo_usd, 2),
        "anticipo_clp": round(anticipo_clp),
        "saldo_clp": round(saldo_clp),
        "total_clp": round(total_clp),
        "tc_efectivo": round(tc_efectivo, 2),
        "diferencia_cambiaria_clp": round(total_clp - ref_clp),  # (+) perdió, (−) ganó vs pagar todo al TC inicial
    }


# ---------------------------------------------------------------------------
# Auditoría DIN
# ---------------------------------------------------------------------------


def auditar_din(declarado: dict[str, float], calc: LiquidacionResult, tolerancia_pct: float = 2.0) -> list[dict[str, Any]]:
    """Compara valores de la Declaración de Ingreso contra el cálculo interno."""
    campos = {
        "FOB (USD)": ("fob_total_usd", calc.fob_total_usd),
        "Flete (USD)": ("flete_usd", calc.flete_usd),
        "Seguro (USD)": ("seguro_usd", calc.seguro_usd),
        "CIF (USD)": ("cif_usd", calc.cif_usd),
        "Ad-valorem (USD)": ("advalorem_usd", calc.advalorem_usd),
        "IVA (USD)": ("iva_usd", calc.iva_usd),
    }
    hallazgos: list[dict[str, Any]] = []
    for etiqueta, (clave, esperado) in campos.items():
        decl = float(declarado.get(clave, 0.0) or 0.0)
        diff = decl - esperado
        pct = (abs(diff) / esperado * 100) if esperado else (100.0 if decl else 0.0)
        estado = "OK" if pct <= tolerancia_pct else "REVISAR"
        hallazgos.append({"campo": etiqueta, "declarado": round(decl, 2), "calculado": round(esperado, 2), "diferencia": round(diff, 2), "desvio_pct": round(pct, 2), "estado": estado})
    return hallazgos


# ---------------------------------------------------------------------------
# Liquidación de LOTE multiproducto con prorrateo de costos comunes
# ---------------------------------------------------------------------------

CRITERIOS_PRORRATEO = {"cbm": "Por volumen (m³, W/M)", "peso": "Por peso (kg)", "fob": "Por valor FOB"}


@dataclass
class LineaInput:
    producto: str
    cajas: int
    unidades_por_caja: int
    fob_unit_usd: float
    largo_cm: float
    ancho_cm: float
    alto_cm: float
    peso_kg: float  # por caja
    tlc: bool = True
    dg: bool = False
    producto_id: int | None = None


@dataclass
class LineaResult:
    producto: str
    producto_id: int | None
    cajas: int
    unidades_por_caja: int
    unidades: int
    fob_unit_usd: float
    fob_total_usd: float
    cbm: float
    peso_kg: float
    tlc: bool
    dg: bool
    participacion: float
    flete_usd: float
    seguro_usd: float
    cif_usd: float
    tasa_advalorem: float
    advalorem_usd: float
    iva_usd: float
    iva_clp: float
    agente_usd: float
    psi_usd: float
    locales_clp: float
    comunes_clp: float
    landed_clp: float
    landed_unit_clp: float
    desembolso_unit_clp: float
    factor_internacion: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LoteResult:
    lineas: list[LineaResult]
    cubicaje: CubicajeResult
    total: LiquidacionResult  # totales consolidados (misma estructura que una liquidación simple)
    criterio: str
    hay_dg: bool

    def to_dict(self) -> dict[str, Any]:
        return {"lineas": [l.to_dict() for l in self.lineas], "cubicaje": self.cubicaje.to_dict(), "total": self.total.to_dict(), "criterio": self.criterio, "hay_dg": self.hay_dg}


def cubicaje_lote(lineas: list[LineaInput]) -> CubicajeResult:
    """Cubicaje consolidado: suma de CBM y pesos; el optimizador usa la caja más pequeña del lote."""
    cbm_total = sum(l.largo_cm * l.ancho_cm * l.alto_cm / 1e6 * l.cajas for l in lineas)
    peso = sum(l.peso_kg * l.cajas for l in lineas)
    vol_aereo = sum(l.largo_cm * l.ancho_cm * l.alto_cm / DIVISOR_VOLUMETRICO_AEREO * l.cajas for l in lineas)
    unidades = sum(l.cajas * l.unidades_por_caja for l in lineas)
    ton = peso / 1000
    m3_fact = max(1, math.ceil(cbm_total - 1e-9))
    libre = max(0.0, m3_fact - cbm_total)
    caja_min = min((l for l in lineas), key=lambda l: l.largo_cm * l.ancho_cm * l.alto_cm) if lineas else None
    cbm_caja_min = caja_min.largo_cm * caja_min.ancho_cm * caja_min.alto_cm / 1e6 if caja_min else 0.0
    cajas_extra = int(libre // cbm_caja_min) if cbm_caja_min > 0 else 0
    return CubicajeResult(
        cbm_caja=round(cbm_caja_min, 4), cbm_total=round(cbm_total, 4), peso_bruto_total_kg=round(peso, 2),
        peso_volumetrico_aereo_kg=round(vol_aereo, 2), peso_cobrable_aereo_kg=round(max(vol_aereo, peso), 2),
        toneladas_maritimo=round(ton, 4), wm_maritimo=round(max(cbm_total, ton), 4),
        cobra_por="Volumen (m³)" if cbm_total >= ton else "Peso (ton)", unidades_totales=unidades,
        cbm_por_unidad=round(cbm_total / unidades, 6) if unidades else 0.0, m3_facturados=m3_fact, cbm_libre=round(libre, 4),
        unidades_extra_sin_costo=cajas_extra * (caja_min.unidades_por_caja if caja_min else 0), cajas_extra_sin_costo=cajas_extra,
    )


def liquidar_lote(lineas: list[LineaInput], comunes: LiquidacionInput, criterio: str = "cbm") -> LoteResult:
    """Liquida un embarque con N productos. `comunes` aporta flete, seguro, agente, PSI, gastos locales, TC e Incoterm."""
    if not lineas:
        raise ValueError("El embarque necesita al menos un producto")
    tc = comunes.tipo_cambio
    incoterm = comunes.incoterm.upper()
    cb = cubicaje_lote(lineas)
    hay_dg = any(l.dg for l in lineas)

    fobs = [l.fob_unit_usd * l.cajas * l.unidades_por_caja for l in lineas]
    cbms = [l.largo_cm * l.ancho_cm * l.alto_cm / 1e6 * l.cajas for l in lineas]
    pesos = [l.peso_kg * l.cajas for l in lineas]
    base = {"cbm": cbms, "peso": pesos, "fob": fobs}.get(criterio, cbms)
    tot_base = sum(base) or 1.0
    shares = [b / tot_base for b in base]

    flete_base = comunes.flete_usd
    recargo = flete_base * comunes.recargo_dg_pct if hay_dg else 0.0
    flete_total = flete_base + recargo
    fob_total = sum(fobs)
    costos_origen = comunes.costos_origen_usd if incoterm == "EXW" else 0.0

    if comunes.seguro_usd is None or comunes.seguro_usd <= 0:
        seguro_total = (fob_total + costos_origen) * SEGURO_PRESUNTO_PCT
        seguro_presunto = True
    else:
        seguro_total = comunes.seguro_usd
        seguro_presunto = False

    if incoterm in ("CIF", "DDP"):
        cif_total = fob_total  # el precio pagado ya es CIF
    else:
        cif_total = fob_total + costos_origen + flete_total + seguro_total

    if incoterm == "DDP":
        agente_total, agente_oblig, agente_det = 0.0, False, "DDP: el vendedor asume despacho e impuestos."
    else:
        agente_total, agente_oblig, agente_det = honorarios_agente(cif_total, comunes.tarifa_agente_base_usd, comunes.forzar_agente)
    locales_total = comunes.desconsolidacion_clp + comunes.almacenaje_clp + comunes.transporte_clp + comunes.otros_clp

    out: list[LineaResult] = []
    for l, fob_i, cbm_i, peso_i, s in zip(lineas, fobs, cbms, pesos, shares):
        unidades = l.cajas * l.unidades_por_caja
        flete_i = flete_total * s
        seguro_i = seguro_total * s
        if incoterm in ("CIF", "DDP"):
            cif_i = fob_i
        else:
            cif_i = fob_i + costos_origen * (fob_i / fob_total if fob_total else 0) + flete_i + seguro_i
        tasa = 0.0 if l.tlc else TASA_ADVALOREM_GENERAL
        adv_i = 0.0 if incoterm == "DDP" else cif_i * tasa
        iva_i = 0.0 if incoterm == "DDP" else (cif_i + adv_i) * TASA_IVA
        agente_i = agente_total * s
        psi_i = comunes.psi_usd * s
        locales_i = locales_total * s
        comunes_i = (flete_i + seguro_i + agente_i + psi_i) * tc + locales_i
        landed_i = (cif_i + adv_i + agente_i + psi_i) * tc + locales_i
        out.append(
            LineaResult(
                producto=l.producto, producto_id=l.producto_id, cajas=l.cajas, unidades_por_caja=l.unidades_por_caja, unidades=unidades,
                fob_unit_usd=l.fob_unit_usd, fob_total_usd=round(fob_i, 2), cbm=round(cbm_i, 4), peso_kg=round(peso_i, 2), tlc=l.tlc, dg=l.dg,
                participacion=round(s, 4), flete_usd=round(flete_i, 2), seguro_usd=round(seguro_i, 2), cif_usd=round(cif_i, 2),
                tasa_advalorem=tasa, advalorem_usd=round(adv_i, 2), iva_usd=round(iva_i, 2), iva_clp=round(iva_i * tc),
                agente_usd=round(agente_i, 2), psi_usd=round(psi_i, 2), locales_clp=round(locales_i), comunes_clp=round(comunes_i),
                landed_clp=round(landed_i), landed_unit_clp=round(landed_i / max(unidades, 1)),
                desembolso_unit_clp=round((landed_i + iva_i * tc) / max(unidades, 1)),
                factor_internacion=round(landed_i / tc / fob_i, 3) if fob_i else 0.0,
            )
        )

    adv_total = sum(x.advalorem_usd for x in out)
    iva_total = sum(x.iva_usd for x in out)
    landed_total = sum(x.landed_clp for x in out)
    desembolso = landed_total + iva_total * tc
    unidades_tot = sum(x.unidades for x in out)
    pasos = [
        {"paso": f"FOB total ({len(out)} SKU, {unidades_tot} u)", "usd": fob_total + costos_origen, "clp": (fob_total + costos_origen) * tc},
        {"paso": "Flete internacional" + (" (+DG)" if recargo else ""), "usd": flete_total, "clp": flete_total * tc},
        {"paso": "Seguro " + ("presunto 2%" if seguro_presunto else "real"), "usd": seguro_total, "clp": seguro_total * tc},
        {"paso": "= CIF", "usd": cif_total, "clp": cif_total * tc},
        {"paso": "Ad-valorem (según TLC por producto)", "usd": adv_total, "clp": adv_total * tc},
        {"paso": "IVA 19% sobre (CIF + Ad-valorem)", "usd": iva_total, "clp": iva_total * tc},
        {"paso": "Honorarios agente de aduana", "usd": agente_total, "clp": agente_total * tc},
        {"paso": "Inspección pre-embarque (PSI)", "usd": comunes.psi_usd, "clp": comunes.psi_usd * tc},
        {"paso": "Gastos locales (desconsolidación, almacenaje, transporte)", "usd": locales_total / tc, "clp": locales_total},
        {"paso": "= LANDED COST (sin IVA)", "usd": landed_total / tc, "clp": landed_total},
        {"paso": "= Desembolso total de caja (con IVA)", "usd": desembolso / tc, "clp": desembolso},
    ]
    nombre = out[0].producto if len(out) == 1 else f"Embarque de {len(out)} productos"
    total = LiquidacionResult(
        producto=nombre, incoterm=incoterm, unidades=unidades_tot, tipo_cambio=tc, tlc=all(l.tlc for l in lineas),
        fob_unit_usd=round(fob_total / max(unidades_tot, 1), 4), fob_total_usd=round(fob_total + costos_origen, 2), costos_origen_usd=round(costos_origen, 2),
        flete_base_usd=round(flete_base, 2), recargo_dg_usd=round(recargo, 2), flete_usd=round(flete_total, 2), seguro_usd=round(seguro_total, 2),
        seguro_es_presunto=seguro_presunto, cif_usd=round(cif_total, 2), cif_clp=round(cif_total * tc), tasa_advalorem=adv_total / cif_total if cif_total else 0,
        advalorem_usd=round(adv_total, 2), advalorem_clp=round(adv_total * tc), base_iva_usd=round(cif_total + adv_total, 2), iva_usd=round(iva_total, 2),
        iva_clp=round(iva_total * tc), honorarios_usd=agente_total, honorarios_clp=round(agente_total * tc), agente_obligatorio=agente_oblig,
        agente_detalle=agente_det, psi_usd=comunes.psi_usd, psi_clp=round(comunes.psi_usd * tc), gastos_locales_clp=round(locales_total),
        landed_clp=round(landed_total), landed_usd=round(landed_total / tc, 2), landed_unit_clp=round(landed_total / max(unidades_tot, 1)),
        landed_unit_usd=round(landed_total / tc / max(unidades_tot, 1), 2), desembolso_total_clp=round(desembolso),
        desembolso_unit_clp=round(desembolso / max(unidades_tot, 1)), factor_internacion=round(landed_total / tc / fob_total, 3) if fob_total else 0.0, pasos=pasos,
    )
    return LoteResult(out, cb, total, criterio, hay_dg)


# ---------------------------------------------------------------------------
# Comparador de medios de transporte
# ---------------------------------------------------------------------------

MODOS_FLETE = {
    "Marítimo LCL": {"unidad": "USD por m³ (regla W/M)", "dias": 40, "ayuda": "Carga consolidada con otros importadores. Conviene entre ~1 y 15 m³. Se cobra por el mayor entre m³ y toneladas."},
    "Marítimo FCL 20'": {"unidad": "USD por contenedor", "dias": 35, "ayuda": "Contenedor completo de ~28 m³ útiles. Conviene desde ~15 m³: el costo por m³ cae fuerte."},
    "Marítimo FCL 40'": {"unidad": "USD por contenedor", "dias": 35, "ayuda": "Contenedor de ~58 m³ útiles (76 m³ en High Cube). Para volúmenes grandes."},
    "Aéreo": {"unidad": "USD por kg cobrable", "dias": 8, "ayuda": "Se cobra el mayor entre peso real y volumétrico (largo×ancho×alto÷5000). Rápido y caro: para reposiciones urgentes o productos livianos de alto valor."},
    "Courier (DHL/FedEx)": {"unidad": "USD por kg cobrable", "dias": 6, "ayuda": "Puerta a puerta con despacho incluido hasta US$3.000 FOB. El más simple para muestras y primeros lotes pequeños."},
}
CAPACIDAD_FCL = {"Marítimo FCL 20'": 28.0, "Marítimo FCL 40'": 58.0}


@dataclass
class OpcionFlete:
    nombre: str
    modo: str
    proveedor: str
    dias_transito: int
    unidades_cobradas: float
    unidad_texto: str
    flete_base_usd: float
    recargo_dg_usd: float
    flete_usd: float
    seguro_usd: float
    locales_clp: float
    cif_usd: float
    advalorem_usd: float
    iva_usd: float
    agente_usd: float
    landed_clp: float
    landed_unit_clp: float
    desembolso_clp: float
    costo_flete_unit_clp: float
    factor_internacion: float
    capacidad_ok: bool
    aviso: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def cotizar_flete(f: dict[str, Any], cbm: float, peso_kg: float, fob_usd: float, unidades: int, tc: float, tlc: bool = True, hay_dg: bool = False, tarifa_agente: float = 150.0) -> OpcionFlete:
    """Calcula el costo total y el landed cost de un lote bajo una cotización de flete concreta."""
    modo = f["modo"]
    ton = peso_kg / 1000
    aviso = ""
    capacidad_ok = True
    if modo == "Marítimo LCL":
        unidades_cobradas = max(cbm, ton)
        unidad_txt = f"{unidades_cobradas:.2f} W/M"
        base = unidades_cobradas * f["tarifa"]
    elif modo.startswith("Marítimo FCL"):
        cap = CAPACIDAD_FCL.get(modo, 28.0)
        n = max(1, math.ceil(cbm / cap - 1e-9))
        unidades_cobradas = float(n)
        unidad_txt = f"{n} contenedor(es)"
        base = n * f["tarifa"]
        uso = cbm / (cap * n) * 100
        if uso < 60:
            aviso = f"Solo ocuparías el {uso:.0f} % del contenedor: con este volumen suele convenir LCL."
    else:  # Aéreo / Courier
        volumetrico = cbm * 1_000_000 / DIVISOR_VOLUMETRICO_AEREO
        unidades_cobradas = max(peso_kg, volumetrico)
        unidad_txt = f"{unidades_cobradas:.0f} kg cobrables"
        base = unidades_cobradas * f["tarifa"]
        if volumetrico > peso_kg:
            aviso = f"Pagas por peso volumétrico ({volumetrico:.0f} kg) y no por el real ({peso_kg:.0f} kg)."
    base = max(base, f.get("minimo_usd", 0.0)) + f.get("recargos_usd", 0.0)
    recargo = base * (f.get("dg_pct", 0.0) / 100) if hay_dg else 0.0
    flete = base + recargo
    seguro = fob_usd * (f["seguro_pct"] / 100 if f.get("seguro_pct") else SEGURO_PRESUNTO_PCT)
    cif = fob_usd + flete + seguro
    adv = 0.0 if tlc else cif * TASA_ADVALOREM_GENERAL
    iva = (cif + adv) * TASA_IVA
    if modo == "Courier (DHL/FedEx)" and cif <= UMBRAL_AGENTE_USD:
        agente, aviso_ag = 0.0, "Courier tramita el despacho: sin agente de aduana bajo US$3.000."
        aviso = (aviso + " " + aviso_ag).strip()
    else:
        agente, _, _ = honorarios_agente(cif, tarifa_agente, False)
    locales = f.get("locales_clp", 0.0)
    landed = (cif + adv + agente) * tc + locales
    desembolso = landed + iva * tc
    return OpcionFlete(
        nombre=f.get("nombre", modo), modo=modo, proveedor=f.get("proveedor", ""), dias_transito=int(f.get("dias_transito") or MODOS_FLETE.get(modo, {}).get("dias", 30)),
        unidades_cobradas=round(unidades_cobradas, 2), unidad_texto=unidad_txt, flete_base_usd=round(base - f.get("recargos_usd", 0.0), 2), recargo_dg_usd=round(recargo, 2), flete_usd=round(flete, 2),
        seguro_usd=round(seguro, 2), locales_clp=round(locales), cif_usd=round(cif, 2), advalorem_usd=round(adv, 2), iva_usd=round(iva, 2), agente_usd=round(agente, 2),
        landed_clp=round(landed), landed_unit_clp=round(landed / max(unidades, 1)), desembolso_clp=round(desembolso),
        costo_flete_unit_clp=round((flete * tc + locales) / max(unidades, 1)), factor_internacion=round(landed / tc / fob_usd, 3) if fob_usd else 0.0,
        capacidad_ok=capacidad_ok, aviso=aviso,
    )


def comparar_fletes(fletes: list[dict[str, Any]], cbm: float, peso_kg: float, fob_usd: float, unidades: int, tc: float, tlc: bool = True, hay_dg: bool = False, tarifa_agente: float = 150.0) -> list[OpcionFlete]:
    ops = [cotizar_flete(f, cbm, peso_kg, fob_usd, unidades, tc, tlc, hay_dg, tarifa_agente) for f in fletes]
    return sorted(ops, key=lambda o: o.landed_unit_clp)
