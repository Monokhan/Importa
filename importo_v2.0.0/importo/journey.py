"""
journey.py — Recorrido del emprendedor: hitos que se desbloquean con hechos reales de la app.

Cada hito se evalúa contra los datos (no contra casillas marcadas a mano), se registra la primera vez
que se logra y alimenta el mapa visual de progreso por etapas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

import database as db

MODULOS = [
    {"clave": "aprende", "nombre": "Aprende", "emoji": "📚", "color": "#1E3A8A", "lema": "Entiende el negocio antes de gastar.",
     "paginas": ["Empieza aquí", "Guía del emprendedor", "Glosario", "Mi recorrido"], "hitos": ["plan_leido", "primer_producto"]},
    {"clave": "formaliza", "nombre": "Formaliza", "emoji": "🏛️", "color": "#064E3B", "lema": "Tu empresa, tus permisos y tus datos en regla.",
     "paginas": ["Requisitos Chile", "Cumplimiento (admin)"], "hitos": ["empresa_formalizada", "datos_responsable"]},
    {"clave": "importa", "nombre": "Importa", "emoji": "📦", "color": "#78350F", "lema": "Elige, cotiza el flete y tráelo sin sorpresas.",
     "paginas": ["Catálogo de productos", "Cotiza tu flete", "Costeo e internación", "Operación y stock"], "hitos": ["primer_flete", "primer_costeo", "primer_embarque", "mercaderia_en_bodega"]},
    {"clave": "vende", "nombre": "Vende", "emoji": "🛒", "color": "#5B21B6", "lema": "Precio con margen limpio y ventas registradas.",
     "paginas": ["Precios y márgenes", "Ventas y dossier"], "hitos": ["primera_venta", "multicanal", "diez_ventas"]},
    {"clave": "administra", "nombre": "Administra", "emoji": "📊", "color": "#7F1D1D", "lema": "Impuestos al día y decisiones con datos.",
     "paginas": ["Gastos y F29", "Panel de hoy", "Salud de tu empresa"], "hitos": ["primer_gasto", "primer_f29", "break_even"]},
    {"clave": "cuenta", "nombre": "Tu cuenta", "emoji": "👤", "color": "#334155", "lema": "Perfil, seguridad y tus datos personales.",
     "paginas": ["Mi cuenta", "Privacidad y mis datos"], "hitos": []},
]
MODULO_DE_PAGINA = {p: m for m in MODULOS for p in m["paginas"]}

MISIONES = {
    "plan_leido": "Completa las 4 tareas de la Etapa 0",
    "primer_producto": "Guarda tu primer producto en el catálogo",
    "empresa_formalizada": "Constituye tu empresa y actívala en el SII",
    "datos_responsable": "Carga la razón social y el RUT de tu empresa",
    "primer_flete": "Compara al menos dos cotizaciones de flete",
    "primer_costeo": "Calcula el costo real de tu producto en bodega",
    "primer_embarque": "Registra tu primer embarque con su ETA",
    "mercaderia_en_bodega": "Retira la mercadería del extraportuario",
    "primera_venta": "Registra tu primera venta",
    "multicanal": "Vende en un segundo canal",
    "diez_ventas": "Llega a 10 ventas registradas",
    "primer_gasto": "Registra un gasto con factura y recupera su IVA",
    "primer_f29": "Cierra un mes con débito y crédito fiscal",
    "break_even": "Recupera lo que invertiste",
}

MEDALLAS = {
    "plan_leido": "📘", "primer_producto": "📦", "empresa_formalizada": "🏛️", "datos_responsable": "🪪",
    "primer_flete": "🚢", "primer_costeo": "🧮", "primer_embarque": "🛬", "mercaderia_en_bodega": "🏬",
    "primera_venta": "💰", "multicanal": "🌐", "diez_ventas": "🔟", "primer_gasto": "🧾", "primer_f29": "📑", "break_even": "🏆",
}

ETAPAS_NOMBRE = {
    0: "Aprende y planifica",
    1: "Tu empresa en regla",
    2: "Elige y costea tu producto",
    3: "Trae la mercadería",
    4: "Vende",
    5: "Administra y crece",
}


@dataclass
class Hito:
    clave: str
    etapa: int
    titulo: str
    detalle: str
    pagina: str
    logrado: bool = False
    fecha: str = ""


def _estado() -> dict[str, Any]:
    ventas = db.list_ventas()
    cots = db.list_cotizaciones()
    embs = db.list_embarques()
    gastos = db.list_gastos()
    inv = db.list_inventario()
    mes = date.today().strftime("%Y-%m")
    rm = db.resumen_f29_mensual(mes)
    inversion = sum(c["desembolso_total_clp"] for c in cots)
    recuperado = sum(v["total_neto"] for v in ventas)
    plan_e0 = sum(1 for i in range(4) if db.get_config(f"plan_0_{i}", "0") == "1")
    plan_e1 = sum(1 for i in range(6) if db.get_config(f"plan_1_{i}", "0") == "1")
    return {
        "productos": len(db.list_productos()), "fletes": len(db.list_fletes()), "cotizaciones": len(cots),
        "embarques": embs, "en_bodega": [e for e in embs if e["estado"] == "En Bodega"], "inventario": inv,
        "ventas": ventas, "gastos": gastos, "f29": rm, "inversion": inversion, "recuperado": recuperado,
        "plan_e0": plan_e0, "plan_e1": plan_e1,
        "responsable": db.get_config("resp_rut", "") not in ("", "76.123.456-7"),
        "canales": {v["canal"] for v in ventas},
    }


DEFINICIONES: list[tuple[str, int, str, str, str, Callable[[dict[str, Any]], bool]]] = [
    ("plan_leido", 0, "Leíste el plan", "Completaste las 4 tareas de la Etapa 0: validaste tu idea antes de gastar.", "Guía del emprendedor", lambda e: e["plan_e0"] >= 4),
    ("primer_producto", 0, "Primer producto en el catálogo", "Guardaste la ficha de un producto con sus medidas y precio FOB.", "Catálogo de productos", lambda e: e["productos"] >= 1),
    ("empresa_formalizada", 1, "Empresa formalizada", "Marcaste las tareas de constitución y activación en el SII.", "Guía del emprendedor", lambda e: e["plan_e1"] >= 5),
    ("datos_responsable", 1, "Datos de tu empresa cargados", "Completaste razón social y RUT: tu política de privacidad y tu RAT ya son reales.", "Cumplimiento (admin)", lambda e: e["responsable"]),
    ("primer_flete", 2, "Comparaste medios de transporte", "Guardaste al menos dos cotizaciones de flete y viste cuál conviene.", "Cotiza tu flete", lambda e: e["fletes"] >= 2),
    ("primer_costeo", 2, "Primer costeo completo", "Calculaste el costo real de un producto puesto en tu bodega.", "Costeo e internación", lambda e: e["cotizaciones"] >= 1),
    ("primer_embarque", 3, "Primer embarque registrado", "Tu importación está en la app, con ETA y días libres bajo control.", "Operación y stock", lambda e: len(e["embarques"]) >= 1),
    ("mercaderia_en_bodega", 3, "Mercadería en bodega", "Retiraste del extraportuario sin pagar sobrestadía.", "Operación y stock", lambda e: len(e["en_bodega"]) >= 1),
    ("primera_venta", 4, "Primera venta", "Vendiste tu primera unidad y la registraste.", "Ventas y dossier", lambda e: len(e["ventas"]) >= 1),
    ("multicanal", 4, "Vendes en más de un canal", "Registraste ventas en dos o más canales distintos.", "Precios y márgenes", lambda e: len(e["canales"]) >= 2),
    ("diez_ventas", 4, "10 ventas registradas", "Ya tienes historial suficiente para medir tendencia y cobertura de stock.", "Ventas y dossier", lambda e: len(e["ventas"]) >= 10),
    ("primer_gasto", 5, "Primer gasto con factura", "Empezaste a recuperar el IVA de tus compras.", "Gastos y F29", lambda e: any(g["documento"] == "Factura" for g in e["gastos"])),
    ("primer_f29", 5, "F29 con movimiento", "Tu declaración mensual ya tiene débito y crédito reales.", "Gastos y F29", lambda e: e["f29"]["debito"] > 0 and e["f29"]["credito"] > 0),
    ("break_even", 5, "Recuperaste la inversión", "Tus cobros netos superan lo que desembolsaste: desde aquí, todo es ganancia.", "Salud de tu empresa", lambda e: e["inversion"] > 0 and e["recuperado"] >= e["inversion"]),
]


def evaluar() -> tuple[list[Hito], list[Hito]]:
    """Devuelve (todos los hitos, hitos recién desbloqueados en esta evaluación)."""
    est = _estado()
    logrados = db.hitos_logrados()
    hitos: list[Hito] = []
    nuevos: list[Hito] = []
    for clave, etapa, titulo, detalle, pagina, cond in DEFINICIONES:
        ok = False
        try:
            ok = bool(cond(est))
        except Exception:  # noqa: BLE001 — un hito nunca debe romper la app
            ok = False
        h = Hito(clave, etapa, titulo, detalle, pagina, ok, logrados.get(clave, ""))
        if ok and clave not in logrados:
            if db.marcar_hito(clave):
                h.fecha = date.today().isoformat()
                nuevos.append(h)
        hitos.append(h)
    return hitos, nuevos


def resumen(hitos: list[Hito]) -> dict[str, Any]:
    total = len(hitos)
    hechos = sum(1 for h in hitos if h.logrado)
    por_etapa: dict[int, dict[str, Any]] = {}
    for e in sorted(ETAPAS_NOMBRE):
        hs = [h for h in hitos if h.etapa == e]
        d = sum(1 for h in hs if h.logrado)
        por_etapa[e] = {"nombre": ETAPAS_NOMBRE[e], "hitos": hs, "hechos": d, "total": len(hs), "completa": d == len(hs), "abierta": True}
    # Una etapa está "en curso" si es la primera incompleta
    actual = next((e for e in sorted(por_etapa) if not por_etapa[e]["completa"]), max(por_etapa))
    siguiente = next((h for h in hitos if not h.logrado), None)
    return {"total": total, "hechos": hechos, "pct": hechos / total if total else 0, "por_etapa": por_etapa, "etapa_actual": actual, "siguiente": siguiente}


def nivel(hechos: int) -> tuple[str, str]:
    """Nivel del usuario según hitos logrados, de novato a experto."""
    if hechos >= 13:
        return "Experto", "Dominas el ciclo completo: costear, importar, vender y declarar."
    if hechos >= 10:
        return "Avanzado", "Ya operas con datos reales. Afina márgenes y financia la orden #2 con tus cobros."
    if hechos >= 7:
        return "Intermedio", "Tu mercadería está vendiendo. Ahora ordena la parte tributaria."
    if hechos >= 4:
        return "Aprendiz", "Tienes producto y costeo. Falta traerlo y venderlo."
    if hechos >= 1:
        return "Explorador", "Diste los primeros pasos. Sigue el plan por etapas."
    return "Novato", "Bienvenido. Empieza por la Etapa 0: aprende y valida tu producto."


# ---------------------------------------------------------------------------
# Racha: días seguidos con actividad registrada
# ---------------------------------------------------------------------------


def racha(hoy: date | None = None) -> dict[str, Any]:
    """Cuenta días consecutivos (hasta hoy o ayer) con al menos una venta o un gasto registrado."""
    hoy = hoy or date.today()
    dias = {v["fecha"][:10] for v in db.list_ventas()} | {g["fecha"][:10] for g in db.list_gastos()}
    if not dias:
        return {"dias": 0, "activo_hoy": False, "ultimos7": [False] * 7, "mensaje": "Registra una venta o un gasto para empezar tu racha."}
    activo_hoy = hoy.isoformat() in dias
    cursor = hoy if activo_hoy else hoy - timedelta(days=1)
    n = 0
    while cursor.isoformat() in dias:
        n += 1
        cursor -= timedelta(days=1)
    ultimos7 = [(hoy - timedelta(days=i)).isoformat() in dias for i in range(6, -1, -1)]
    plural = "día" if n == 1 else "días"
    if n == 0:
        msg = "Tu racha se cortó. Registra algo hoy para empezar de nuevo."
    elif activo_hoy:
        msg = f"Llevas {n} {plural} seguidos con movimiento registrado."
    else:
        msg = f"Racha de {n} {plural}. Registra algo hoy para no perderla."
    return {"dias": n, "activo_hoy": activo_hoy, "ultimos7": ultimos7, "mensaje": msg}


# ---------------------------------------------------------------------------
# Progreso por módulo temático
# ---------------------------------------------------------------------------


def progreso_modulos(hitos: list[Hito]) -> list[dict[str, Any]]:
    por_clave = {h.clave: h for h in hitos}
    out = []
    for m in MODULOS:
        hs = [por_clave[c] for c in m["hitos"] if c in por_clave]
        hechos = sum(1 for h in hs if h.logrado)
        out.append({**m, "lista": hs, "hechos": hechos, "total": len(hs), "completo": hechos == len(hs), "pct": hechos / len(hs) if hs else 1.0})
    return out


def modulo_actual(mods: list[dict[str, Any]]) -> str:
    for m in mods:
        if m["hitos"] and not m["completo"]:
            return m["clave"]
    return mods[-1]["clave"]


def mision_del_dia(hitos: list[Hito], hoy: date | None = None) -> dict[str, Any]:
    """Una sola cosa recomendada para hoy: el siguiente hito pendiente, con su módulo."""
    sig = next((h for h in hitos if not h.logrado), None)
    r = racha(hoy)
    if sig is None:
        return {"titulo": "Recorrido completo", "detalle": "Lograste los 14 hitos. Mantén la racha registrando ventas y gastos cada día.", "pagina": "Salud de tu empresa", "icono": "🏆", "racha": r}
    mod = next((m for m in MODULOS if sig.clave in m["hitos"]), MODULOS[0])
    return {"titulo": f"Misión de hoy: {MISIONES.get(sig.clave, sig.titulo)}", "detalle": f"{sig.detalle} Lo consigues en {sig.pagina}.", "pagina": sig.pagina, "icono": mod["emoji"], "modulo": mod["nombre"], "hito": sig, "racha": r}
