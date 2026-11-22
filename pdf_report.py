"""
pdf_report.py — Dossier Ejecutivo en PDF (fpdf2).

Genera un informe formal con: resumen del costeo, liquidación aduanera paso a paso, estructura
multicanal y márgenes, semáforo F29 y proyección de flujo de caja. Devuelve `bytes` para
`st.download_button`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fpdf import FPDF

AZUL = (37, 99, 235)
VERDE = (16, 185, 129)
AMBAR = (245, 158, 11)
ROJO = (239, 68, 68)
GRIS = (100, 116, 139)
FONDO = (248, 250, 252)


def _s(txt: Any) -> str:
    """Helvetica core font soporta latin-1: reemplazamos lo que no cabe."""
    return str(txt).encode("latin-1", "replace").decode("latin-1")


def clp(v: float) -> str:
    return "$" + f"{v:,.0f}".replace(",", ".")


def usd(v: float) -> str:
    return f"US$ {v:,.2f}"


class Dossier(FPDF):
    def __init__(self, titulo: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.titulo = titulo
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 15, 15)

    def header(self) -> None:
        self.set_fill_color(*AZUL)
        self.rect(0, 0, 210, 14, "F")
        self.set_y(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, _s("Importa - Dossier Ejecutivo"), align="L")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 8, _s(datetime.now().strftime("%d-%m-%Y %H:%M")), align="R")
        self.ln(14)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRIS)
        self.cell(0, 6, _s(f"{self.titulo}  |  Página {self.page_no()}/{{nb}}"), align="C")

    # --- helpers de layout -------------------------------------------------
    def h1(self, txt: str) -> None:
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*AZUL)
        self.cell(0, 10, _s(txt), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def h2(self, txt: str) -> None:
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(*FONDO)
        self.cell(0, 8, _s("  " + txt), new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(1)

    def kv(self, k: str, v: str, color: tuple[int, int, int] | None = None) -> None:
        self.set_font("Helvetica", "", 10)
        self.cell(95, 6, _s(k))
        self.set_font("Helvetica", "B", 10)
        if color:
            self.set_text_color(*color)
        self.cell(0, 6, _s(v), new_x="LMARGIN", new_y="NEXT", align="R")
        self.set_text_color(0, 0, 0)

    def tabla(self, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*AZUL)
        self.set_text_color(255, 255, 255)
        for h, w in zip(headers, widths):
            self.cell(w, 7, _s(h), border=0, fill=True, align="C")
        self.ln()
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 9)
        fill = False
        for r in rows:
            self.set_fill_color(*(FONDO if fill else (255, 255, 255)))
            for i, (c, w) in enumerate(zip(r, widths)):
                self.cell(w, 6.5, _s(c), border=0, fill=True, align="L" if i == 0 else "R")
            self.ln()
            fill = not fill
        self.ln(2)

    def semaforo(self, color: str, texto: str) -> None:
        rgb = {"verde": VERDE, "ambar": AMBAR, "rojo": ROJO}.get(color, GRIS)
        self.set_fill_color(*rgb)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        self.multi_cell(0, 8, _s("  " + texto), fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def parrafo(self, txt: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, _s(txt))
        self.ln(1)


def generar_dossier(
    liq: dict[str, Any],
    cubicaje: dict[str, Any] | None,
    mix: dict[str, Any] | None,
    f29: dict[str, Any] | None,
    flujo: dict[str, Any] | None,
    viabilidad: tuple[str, str] | None = None,
    lineas: list[dict[str, Any]] | None = None,
) -> bytes:
    pdf = Dossier(titulo=liq.get("producto", "Costeo de importación"))
    pdf.alias_nb_pages()
    pdf.add_page()

    # 1. Resumen ejecutivo ----------------------------------------------------
    pdf.h1(f"Costeo de importación: {liq.get('producto','')}")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRIS)
    pdf.cell(0, 5, _s(f"Incoterm {liq.get('incoterm','FOB')}  |  TC USD {liq.get('tipo_cambio',0):,.2f} CLP  |  {liq.get('unidades',0)} unidades  |  TLC: {'Sí (0%)' if liq.get('tlc') else 'No (6%)'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    if viabilidad:
        pdf.semaforo(viabilidad[0], viabilidad[1])

    pdf.h2("1. Resumen ejecutivo")
    pdf.kv("Landed Cost total (sin IVA)", clp(liq["landed_clp"]))
    pdf.kv("Landed Cost unitario en bodega", clp(liq["landed_unit_clp"]), AZUL)
    pdf.kv("Desembolso total de caja (con IVA)", clp(liq["desembolso_total_clp"]))
    pdf.kv("Factor de internación (Landed / FOB)", f"{liq['factor_internacion']:.2f}x")
    pdf.kv("IVA de importación (Crédito Fiscal)", clp(liq["iva_clp"]), VERDE)

    # 2. Cubicaje -------------------------------------------------------------
    if cubicaje:
        pdf.h2("2. Cubicaje y regla W/M")
        pdf.kv("CBM total del lote", f"{cubicaje['cbm_total']:.3f} m3")
        pdf.kv("Peso bruto total", f"{cubicaje['peso_bruto_total_kg']:.1f} kg")
        pdf.kv("Peso volumétrico aéreo (÷5000)", f"{cubicaje['peso_volumetrico_aereo_kg']:.1f} kg")
        pdf.kv("Unidad de cobro marítimo LCL (W/M)", f"{cubicaje['wm_maritimo']:.3f} - cobra por {cubicaje['cobra_por']}")
        pdf.kv("m3 facturados / espacio libre", f"{cubicaje['m3_facturados']} m3 / {cubicaje['cbm_libre']:.3f} m3 libres")
        pdf.kv("Unidades extra sin costo de flete", f"{cubicaje['unidades_extra_sin_costo']} u ({cubicaje['cajas_extra_sin_costo']} cajas)")

    # 3. Liquidación aduanera --------------------------------------------------
    pdf.h2("3. Liquidación aduanera paso a paso")
    rows = [[p["paso"], usd(p["usd"]), clp(p["clp"])] for p in liq.get("pasos", [])]
    pdf.tabla(["Concepto", "USD", "CLP"], rows, [100, 40, 40])
    if liq.get("agente_obligatorio"):
        pdf.parrafo(f"Agente de aduanas obligatorio (CIF > US$3.000). Base de cálculo: {liq.get('agente_detalle','')}.")
    if liq.get("seguro_es_presunto"):
        pdf.parrafo("Seguro presunto del 2% sobre FOB aplicado por no acreditarse póliza real.")

    # 3b. Detalle por producto --------------------------------------------------
    if lineas and len(lineas) > 1:
        pdf.h2("3b. Costo por producto (costos comunes prorrateados)")
        rows = [[l["producto"][:34], str(l["unidades"]), f"{l['cbm']:.3f}", f"{l['participacion']*100:.0f}%", f"{l.get('tasa_advalorem', 0.0 if l.get('tlc', 1) else 0.06)*100:.0f}%", clp(l["landed_unit_clp"]), f"{l['factor_internacion']:.2f}x"] for l in lineas]
        pdf.tabla(["Producto", "Unid.", "m3", "Reparto", "Arancel", "Landed u.", "Factor"], rows, [66, 18, 20, 20, 20, 28, 18])

    # 4. Multicanal -------------------------------------------------------------
    if mix and mix.get("canales"):
        pdf.add_page()
        pdf.h2("4. Estructura multicanal y margen limpio")
        rows = []
        for c in mix["canales"]:
            rows.append([f"{c['canal']} ({c['mix_pct']*100:.0f}%)", clp(c["precio_bruto"]), clp(c["comision_neta"] + c["pasarela_neta"]), clp(c["flete_vendedor"]), clp(c["merma"] + c["kit_empaque"]), clp(c["margen_limpio"]), f"{c['margen_pct_sobre_neto']:.1f}%"])
        pdf.tabla(["Canal (mix)", "Precio", "Comisión", "Flete", "Merma+Kit", "Margen", "%"], rows, [46, 24, 24, 20, 24, 24, 18])
        pdf.kv("Precio bruto ponderado", clp(mix["precio_ponderado"]))
        pdf.kv("Margen limpio ponderado por unidad", clp(mix["margen_ponderado"]), VERDE if mix["margen_ponderado"] > 0 else ROJO)
        pdf.kv("Margen % sobre precio neto", f"{mix['margen_pct_ponderado']:.1f}%")
        pdf.kv("Cobro neto que llega a cuenta (ponderado)", clp(mix["cobro_neto_ponderado"]))
        if mix.get("target"):
            t = mix["target"]
            pdf.h2("4b. Calculadora inversa Target 2.5x")
            pdf.kv("Capital disponible", clp(t["capital_clp"]))
            pdf.kv("Unidades financiables", f"{t['unidades_posibles']} u")
            pdf.kv("Precio bruto requerido (ponderado)", clp(t["precio_unico_requerido"]), AZUL)
            pdf.kv("Utilidad neta objetivo", clp(t["utilidad_neta_requerida_clp"]))
            pdf.parrafo(t["mensaje"])

    # 5. F29 ---------------------------------------------------------------------
    if f29:
        pdf.h2("5. Semáforo preventivo F29 (SII)")
        pdf.semaforo(f29["color"], f29["mensaje"])
        pdf.kv("IVA Crédito Fiscal acumulado", clp(f29["credito_fiscal"]))
        pdf.kv("IVA Débito Fiscal acumulado", clp(f29["debito_fiscal"]))
        pdf.kv("PPM (1% ventas netas)", clp(f29["ppm"]))
        pdf.kv("Próximo vencimiento", f"{f29['vencimiento']} ({f29['dias_para_vencer']} días)")

    # 6. Flujo -------------------------------------------------------------------
    if flujo:
        pdf.h2("6. Proyección de flujo de caja")
        pdf.kv("Inversión inicial (desembolso)", clp(flujo.get("inversion", 0)))
        pdf.kv("Venta diaria estimada", f"{flujo.get('venta_diaria', 0):.1f} u/día")
        be = flujo.get("break_even_dia")
        pdf.kv("Punto de equilibrio (break-even)", f"Día {be}" if be is not None else "No alcanzado en el horizonte", VERDE if be is not None else ROJO)
        if flujo.get("cash_to_cash"):
            pdf.parrafo("Cash-to-Cash: " + flujo["cash_to_cash"])

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(0, 4.5, _s("Este informe es una herramienta de gestión interna. Las tasas aduaneras (Ad-valorem 6%, IVA 19%), umbrales y comisiones de plataformas pueden cambiar; verifique con su agente de aduanas y contador antes de tomar decisiones."))
    return bytes(pdf.output())
