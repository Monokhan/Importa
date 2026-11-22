"""
pricing_multichannel.py — Pricing multicanal, margen limpio, mermas y calculadora inversa "Target 2.5x".

Canales:
- Mercado Libre: comisión de categoría (14–16%), envío gratis obligatorio desde $19.990 con costo de
  flete al vendedor (~$3.900), bonificación opcional Mercado Envíos Flex.
- Web / Instagram: pasarela Webpay Plus / Transbank 2,9% + IVA; flete plano o a cargo del cliente.
- B2B / Mayorista: sin comisión de plataforma.

Convención: precio de venta es BRUTO (con IVA). Comisiones y pasarela se cobran sobre el bruto y
traen IVA incluido, cuyo IVA es crédito fiscal recuperable → se descuentan netas en el margen limpio.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

IVA = 0.19
ML_UMBRAL_ENVIO_GRATIS = 19_990.0
ML_FLETE_VENDEDOR_CLP = 3_900.0
ML_COMISION_DEFAULT = 0.15
ML_BONUS_FLEX_CLP = 1_500.0
WEBPAY_PCT = 0.029  # + IVA
KIT_EMPAQUE_DEFAULT = 650.0
MERMA_DEFAULT = 0.04
TARGET_MULTIPLO = 2.5


@dataclass
class CanalParams:
    nombre: str
    comision_pct: float = 0.0  # sobre precio bruto (incluye IVA)
    pasarela_pct: float = 0.0  # sobre precio bruto, sin IVA (se agrega IVA)
    flete_fijo_clp: float = 0.0  # flete asumido por el vendedor siempre
    umbral_envio_gratis: float | None = None
    flete_vendedor_clp: float = 0.0  # se aplica si precio >= umbral
    bonus_flex_clp: float = 0.0
    mix_pct: float = 0.0  # participación del canal en las ventas (0-1)
    publicidad_pct: float = 0.0  # inversión publicitaria como % del precio bruto (Meta/Google/ML Ads)
    cac_clp: float = 0.0  # costo de adquisición fijo por venta (CLP), alternativa al %


def canales_default(ml_comision: float = ML_COMISION_DEFAULT, flex: bool = False, webpay_flete_clp: float = 0.0, mix: tuple[float, float, float] = (0.5, 0.3, 0.2), ads: tuple[float, float, float] = (0.0, 0.0, 0.0), cac: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> list[CanalParams]:
    """`ads` = % del precio invertido en publicidad por canal; `cac` = CLP fijo por venta."""
    return [
        CanalParams("Mercado Libre", comision_pct=ml_comision, umbral_envio_gratis=ML_UMBRAL_ENVIO_GRATIS, flete_vendedor_clp=ML_FLETE_VENDEDOR_CLP, bonus_flex_clp=ML_BONUS_FLEX_CLP if flex else 0.0, mix_pct=mix[0], publicidad_pct=ads[0], cac_clp=cac[0]),
        CanalParams("Web / Instagram", pasarela_pct=WEBPAY_PCT, flete_fijo_clp=webpay_flete_clp, mix_pct=mix[1], publicidad_pct=ads[1], cac_clp=cac[1]),
        CanalParams("B2B / Mayorista", mix_pct=mix[2], publicidad_pct=ads[2], cac_clp=cac[2]),
    ]


@dataclass
class ResultadoCanal:
    canal: str
    precio_bruto: float
    precio_neto: float
    iva_debito: float
    comision_bruta: float
    comision_neta: float
    pasarela_bruta: float
    pasarela_neta: float
    flete_vendedor: float
    envio_gratis_aplica: bool
    merma: float
    kit_empaque: float
    publicidad: float
    costo_unit: float
    margen_limpio: float
    margen_pct_sobre_neto: float
    cobro_neto_recibido: float  # lo que llega a la cuenta (bruto - comisión - pasarela - flete)
    mix_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calcular_canal(precio_bruto: float, costo_unit: float, canal: CanalParams, kit_clp: float = KIT_EMPAQUE_DEFAULT, merma_pct: float = MERMA_DEFAULT) -> ResultadoCanal:
    neto = precio_bruto / (1 + IVA)
    iva = precio_bruto - neto
    com_bruta = precio_bruto * canal.comision_pct
    com_neta = com_bruta / (1 + IVA)
    pas_neta = precio_bruto * canal.pasarela_pct
    pas_bruta = pas_neta * (1 + IVA)
    aplica = canal.umbral_envio_gratis is not None and precio_bruto >= canal.umbral_envio_gratis
    flete = canal.flete_fijo_clp + (max(0.0, canal.flete_vendedor_clp - canal.bonus_flex_clp) if aplica else 0.0)
    merma = precio_bruto * merma_pct
    # Publicidad: la factura de Meta/Google/ML Ads trae IVA recuperable → se descuenta neta
    publicidad = (precio_bruto * canal.publicidad_pct + canal.cac_clp) / (1 + IVA)
    margen = neto - com_neta - pas_neta - flete - merma - kit_clp - publicidad - costo_unit
    cobro = precio_bruto - com_bruta - pas_bruta - flete
    return ResultadoCanal(
        canal=canal.nombre,
        precio_bruto=round(precio_bruto),
        precio_neto=round(neto),
        iva_debito=round(iva),
        comision_bruta=round(com_bruta),
        comision_neta=round(com_neta),
        pasarela_bruta=round(pas_bruta),
        pasarela_neta=round(pas_neta),
        flete_vendedor=round(flete),
        envio_gratis_aplica=aplica,
        merma=round(merma),
        kit_empaque=round(kit_clp),
        publicidad=round(publicidad),
        costo_unit=round(costo_unit),
        margen_limpio=round(margen),
        margen_pct_sobre_neto=round(margen / neto * 100, 1) if neto else 0.0,
        cobro_neto_recibido=round(cobro),
        mix_pct=canal.mix_pct,
    )


@dataclass
class ResultadoMix:
    canales: list[ResultadoCanal]
    precio_ponderado: float
    margen_ponderado: float
    margen_pct_ponderado: float
    cobro_neto_ponderado: float
    mix_valido: bool


def calcular_mix(precios: dict[str, float], costo_unit: float, canales: list[CanalParams], kit_clp: float, merma_pct: float) -> ResultadoMix:
    res = [calcular_canal(precios[c.nombre], costo_unit, c, kit_clp, merma_pct) for c in canales]
    tot = sum(c.mix_pct for c in canales)
    valido = abs(tot - 1.0) < 0.005
    w = [c.mix_pct / tot if tot else 0 for c in canales]
    p = sum(r.precio_bruto * wi for r, wi in zip(res, w))
    m = sum(r.margen_limpio * wi for r, wi in zip(res, w))
    cobro = sum(r.cobro_neto_recibido * wi for r, wi in zip(res, w))
    pct = m / (p / (1 + IVA)) * 100 if p else 0.0
    return ResultadoMix(res, round(p), round(m), round(pct, 1), round(cobro), valido)


# ---------------------------------------------------------------------------
# Calculadora inversa Target 2.5x
# ---------------------------------------------------------------------------


@dataclass
class ResultadoTarget:
    capital_clp: float
    desembolso_unit_clp: float
    unidades_posibles: int
    capital_usado_clp: float
    meta_retorno_total_clp: float  # 2.5 × capital
    utilidad_neta_requerida_clp: float  # 1.5 × capital
    margen_unit_requerido_clp: float
    precio_unico_requerido: float  # mismo precio en todos los canales, ponderado por mix
    margen_pct_resultante: float
    viable: bool
    mensaje: str
    detalle_canales: list[ResultadoCanal] = field(default_factory=list)


def _margen_ponderado_a_precio(precio: float, costo_unit: float, canales: list[CanalParams], kit: float, merma: float) -> tuple[float, list[ResultadoCanal]]:
    tot = sum(c.mix_pct for c in canales) or 1.0
    res = [calcular_canal(precio, costo_unit, c, kit, merma) for c in canales]
    return sum(r.margen_limpio * c.mix_pct / tot for r, c in zip(res, canales)), res


def calcular_target(capital_clp: float, desembolso_unit_clp: float, landed_unit_clp: float, canales: list[CanalParams], kit_clp: float = KIT_EMPAQUE_DEFAULT, merma_pct: float = MERMA_DEFAULT, multiplo: float = TARGET_MULTIPLO) -> ResultadoTarget:
    """Dado el capital, ¿cuántas unidades compro y a qué precio vendo para retornar `multiplo` × capital?"""
    unidades = int(capital_clp // desembolso_unit_clp) if desembolso_unit_clp > 0 else 0
    if unidades <= 0:
        return ResultadoTarget(capital_clp, desembolso_unit_clp, 0, 0, 0, 0, 0, 0, 0, False, "El capital no alcanza ni para una unidad con este costo.", [])
    usado = unidades * desembolso_unit_clp
    meta_total = multiplo * capital_clp
    utilidad_req = meta_total - capital_clp
    margen_req = utilidad_req / unidades

    # Bisección sobre el precio (el margen es creciente con el precio, salvo el salto del umbral ML)
    lo, hi = landed_unit_clp, landed_unit_clp * 60 + 100_000
    for _ in range(80):
        mid = (lo + hi) / 2
        m, _ = _margen_ponderado_a_precio(mid, landed_unit_clp, canales, kit_clp, merma_pct)
        if m < margen_req:
            lo = mid
        else:
            hi = mid
    precio = round(hi / 10) * 10  # redondeo comercial a $10
    m, det = _margen_ponderado_a_precio(precio, landed_unit_clp, canales, kit_clp, merma_pct)
    pct = m / (precio / (1 + IVA)) * 100 if precio else 0
    ratio = precio / landed_unit_clp if landed_unit_clp else 0
    viable = ratio <= 4.0
    def _clp(v: float) -> str:
        return "$" + f"{v:,.0f}".replace(",", ".")

    def _dec(v: float) -> str:
        return f"{v:.1f}".replace(".", ",")

    msg = (
        f"Compra {unidades} unidades (usas {_clp(usado)}). Véndelas a un precio ponderado cercano a {_clp(precio)} con IVA: "
        f"te quedan {_clp(m)} limpios por unidad y recuperas {_dec(multiplo)} veces tu capital."
        if viable
        else f"Tendrías que vender a {_dec(ratio)} veces tu costo en bodega ({_clp(precio)}). Es poco realista: busca un producto con mejor factor o negocia el FOB."
    )
    return ResultadoTarget(capital_clp, desembolso_unit_clp, unidades, round(usado), round(meta_total), round(utilidad_req), round(margen_req), precio, round(pct, 1), viable, msg, det)


def semaforo_viabilidad(margen_pct: float, factor_internacion: float) -> tuple[str, str]:
    """Semáforo comercial para el modo Wizard."""
    if margen_pct >= 25 and factor_internacion <= 2.2:
        return "verde", "Negocio viable: margen limpio sano y costo de internación razonable."
    if margen_pct >= 10:
        return "ambar", "Viable con cuidado: margen ajustado o factor de internación alto. Revisa flete, cubicaje o TLC."
    return "rojo", "No recomendable: el margen limpio no cubre imprevistos. Sube precio, baja FOB o cambia de producto."


# ---------------------------------------------------------------------------
# Punto de equilibrio mensual con costos fijos
# ---------------------------------------------------------------------------


def punto_equilibrio_mensual(costos_fijos_clp: float, margen_unit_clp: float, precio_bruto_ponderado: float) -> dict[str, float]:
    """Unidades y venta bruta mensual necesarias para cubrir los costos fijos (arriendo, sueldos, software, publicidad fija)."""
    if margen_unit_clp <= 0:
        return {"unidades_mes": float("inf"), "unidades_dia": float("inf"), "venta_bruta_mes": float("inf"), "viable": False}
    u = costos_fijos_clp / margen_unit_clp
    return {"unidades_mes": round(u, 1), "unidades_dia": round(u / 30, 2), "venta_bruta_mes": round(u * precio_bruto_ponderado), "viable": True}


def roas_minimo(margen_sin_publicidad_clp: float, precio_bruto: float) -> float:
    """ROAS mínimo para no perder: ingresos por cada peso de publicidad tal que el margen quede en cero."""
    if margen_sin_publicidad_clp <= 0:
        return float("inf")
    return round(precio_bruto / margen_sin_publicidad_clp, 2)
