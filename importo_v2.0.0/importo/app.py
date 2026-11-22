"""
app.py — Importo
Tu costo real, puesto en bodega.
Costeo de importaciones multiproducto, inteligencia tributaria (F29/SII), logística y caja.

Ejecutar:  streamlit run app.py
"""
from __future__ import annotations

from dataclasses import asdict
from html import escape as html_escape
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import auth
import database as db
import guide
import journey
import privacy
import tooltips
from health import salud_empresa
from currency import fetch_indicadores, get_rates
from customs_engine import (
    MODOS_FLETE,
    comparar_fletes,
    CRITERIOS_PRORRATEO,
    INCOTERMS,
    LineaInput,
    LiquidacionInput,
    LoteResult,
    PagoEscalonado,
    auditar_din,
    calcular_pago_escalonado,
    liquidar_lote,
)
from market_intel import buscar_mercadolibre, items_a_df, resumen_manual, resumir_precios
from operations_engine import ciclo_cash_to_cash, cobertura_stock, estado_dias_libres, flujo_caja_acumulado, proyeccion_flujo
from pdf_report import generar_dossier
from pricing_multichannel import IVA, calcular_mix, calcular_target, canales_default, punto_equilibrio_mensual, roas_minimo, semaforo_viabilidad
from tax_engine import f29_mensual, resumen_f29

__version__ = "2.0.0"

tooltips.instalar()
_ICONO = Path(__file__).with_name("assets") / "favicon.png"
st.set_page_config(page_title="Importo", page_icon=str(_ICONO) if _ICONO.exists() else "📦", layout="wide", initial_sidebar_state="auto")
db.init_db()

# =============================================================================
# Sistema de diseño
# =============================================================================
LIGHT = dict(canvas="#F3F5F9", card="#FFFFFF", ink="#0F172A", ink2="#334155", mute="#64748B", line="#E2E8F0", field="#FAFBFD", green2="#D1FAE5", greent="#065F46", amber2="#FEF3C7", ambert="#92400E", red2="#FEE2E2", redt="#991B1B", blue2="#DBEAFE", bluet="#1E40AF")
DARK = dict(canvas="#0F172A", card="#162036", ink="#F1F5F9", ink2="#CBD5E1", mute="#94A3B8", line="#233049", field="#0F172A", green2="#064E3B", greent="#A7F3D0", amber2="#78350F", ambert="#FDE68A", red2="#7F1D1D", redt="#FECACA", blue2="#1E3A8A", bluet="#BFDBFE")
BASE = dict(navy="#0F172A", navy2="#111C34", blue="#2563EB", green="#10B981", amber="#F59E0B", red="#EF4444")
SEM = {"verde": "green", "ambar": "amber", "rojo": "red", "gris": "mute"}


def inject_css(oscuro: bool, celular: bool) -> None:
    t = {**BASE, **(DARK if oscuro else LIGHT)}
    fs = "17px" if celular else "15px"
    st.markdown(
        f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=IBM+Plex+Mono:wght@400;600&display=swap');
:root{{--canvas:{t['canvas']};--card:{t['card']};--ink:{t['ink']};--ink2:{t['ink2']};--mute:{t['mute']};--line:{t['line']};--field:{t['field']};
--blue:{t['blue']};--green:{t['green']};--amber:{t['amber']};--red:{t['red']};--green2:{t['green2']};--greent:{t['greent']};--amber2:{t['amber2']};--ambert:{t['ambert']};--red2:{t['red2']};--redt:{t['redt']};--blue2:{t['blue2']};--bluet:{t['bluet']};
--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace;--sans:'Manrope',system-ui,sans-serif}}
html,body,.stApp,[data-testid="stAppViewContainer"]{{background:var(--canvas)!important;color:var(--ink);font-family:var(--sans);font-size:{fs}}}
[data-testid="stHeader"]{{background:transparent}}
h1,h2,h3,h4,h5,p,li,label,span,div{{font-family:var(--sans)}}
h1{{font-weight:800!important;letter-spacing:-.02em;font-size:{'1.55rem' if celular else '1.75rem'}!important;color:var(--ink)!important;margin-bottom:.15rem!important}}
h2,h3{{color:var(--ink)!important;font-weight:800!important;letter-spacing:-.01em;font-size:1.15rem!important;margin-top:.6rem!important}}
.sub{{color:var(--mute);font-size:.9rem;margin:0 0 1.2rem}}
section[data-testid="stSidebar"]{{background:{t['navy']}!important;border-right:0}}
section[data-testid="stSidebar"] *{{color:#CBD5E1}}
section[data-testid="stSidebar"] .brand{{display:flex;align-items:center;gap:12px;color:#fff;font-weight:800;font-size:17px;margin:4px 0 18px}}
section[data-testid="stSidebar"] .brand svg{{flex:none}}
section[data-testid="stSidebar"] .brand span{{letter-spacing:-.02em}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button{{justify-content:flex-start;text-align:left;background:transparent!important;border:0!important;color:#94A3B8!important;padding:8px 12px;border-radius:10px;font-weight:600;font-size:14px;box-shadow:none}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button p{{color:inherit!important;font-size:14px}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button:hover{{background:{t['navy2']}!important;color:#fff!important}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid*="primary"]{{background:{t['navy2']}!important;color:#fff!important;box-shadow:inset 3px 0 0 var(--blue)}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid*="primary"] p{{color:#fff!important}}
section[data-testid="stSidebar"] [class*="st-key-nav_"]{{margin-bottom:-6px}}
section[data-testid="stSidebar"] .stButton>button{{justify-content:flex-start;text-align:left;background:transparent!important;border:none!important;color:#94A3B8!important;font-weight:600;font-size:14px;padding:9px 12px;border-radius:10px;line-height:1.35}}
section[data-testid="stSidebar"] .stButton>button:hover{{background:{t['navy2']}!important;color:#fff!important}}
section[data-testid="stSidebar"] .stButton>button[kind="primary"]{{background:{t['navy2']}!important;color:#fff!important;box-shadow:inset 3px 0 0 var(--blue)}}
section[data-testid="stSidebar"] .stButton>button>div,section[data-testid="stSidebar"] .stButton>button>div>span,section[data-testid="stSidebar"] .stButton>button [data-testid="stMarkdownContainer"]{{width:100%;justify-content:flex-start;text-align:left;display:block}}
section[data-testid="stSidebar"] .stButton>button p{{text-align:left;width:100%;margin:0}}
.ruta{{display:flex;flex-direction:column;gap:0}}
.ruta .et{{display:flex;gap:16px}}
.ruta .col{{display:flex;flex-direction:column;align-items:center;width:52px;flex:none}}
.ruta .bola{{width:44px;height:44px;border-radius:50%;display:grid;place-items:center;font-family:var(--mono);font-weight:600;font-size:15px;border:3px solid var(--line);background:var(--card);color:var(--mute)}}
.ruta .bola.ok{{background:var(--green);border-color:var(--green);color:#fff}}
.ruta .bola.now{{background:var(--card);border-color:var(--blue);color:var(--blue);box-shadow:0 0 0 5px var(--blue2)}}
.ruta .linea{{width:3px;flex:1;min-height:18px;background:var(--line);margin:4px 0}}
.ruta .linea.ok{{background:var(--green)}}
.ruta .cuerpo{{flex:1;padding-bottom:18px}}
.ruta h5{{margin:10px 0 8px;font-size:15px;font-weight:800;color:var(--ink)}}
.ruta h5 small{{font-weight:600;color:var(--mute);font-size:12px;margin-left:8px}}
.hito{{display:flex;align-items:flex-start;gap:10px;padding:9px 12px;border-radius:10px;border:1px solid var(--line);margin-bottom:6px;background:var(--card)}}
.hito.ok{{background:var(--green2);border-color:transparent}}
.hito .chk{{width:20px;height:20px;border-radius:50%;flex:none;display:grid;place-items:center;font-size:12px;border:2px solid var(--line);color:transparent;margin-top:1px}}
.hito.ok .chk{{background:var(--green);border-color:var(--green);color:#fff}}
.hito b{{font-size:13.5px;color:var(--ink)}}.hito.ok b{{color:var(--greent)}}
.hito p{{margin:2px 0 0;font-size:12.5px;color:var(--mute)}}.hito.ok p{{color:var(--greent);opacity:.85}}
.nivel{{display:inline-flex;align-items:center;gap:10px;padding:8px 16px;border-radius:99px;background:var(--blue2);color:var(--bluet);font-weight:700;font-size:14px}}

.player{{background:{t['navy2']};border-radius:14px;padding:12px 13px;margin:2px 0 12px}}
.player .ptop{{display:flex;align-items:center;gap:10px}}
.player .ring{{width:44px;height:44px;flex:none;border-radius:50%;display:grid;place-items:center}}
.player .ring span{{width:34px;height:34px;border-radius:50%;background:{t['navy2']};display:grid;place-items:center;font-family:var(--mono);font-size:11px;color:#fff;font-weight:600}}
.player b{{color:#fff;font-size:13.5px;display:block;line-height:1.2}}
.player small{{color:#94A3B8;font-size:11.5px}}
.player .streak{{display:flex;gap:5px;margin-top:10px}}
.player .streak i{{flex:1;height:5px;border-radius:99px;background:#243044}}
.player .streak i.on{{background:var(--amber)}}
.player .rtxt{{display:block;margin-top:6px;color:#94A3B8;font-size:11px;line-height:1.35}}
.ghead{{display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:11px;font-weight:700;font-size:13.5px;color:#E2E8F0;margin-top:2px}}
.ghead.open{{background:{t['navy2']}}}
.ghead .gicon{{width:26px;height:26px;border-radius:8px;flex:none;display:grid;place-items:center;font-size:13px}}
.ghead .gname{{flex:1}}
.ghead .pill{{font-family:var(--mono);font-size:10.5px;padding:2px 7px;border-radius:99px;background:#243044;color:#94A3B8}}
.ghead .pill.ok{{background:#064E3B;color:#6EE7B7}}
.ghead .pill.now{{background:#1E3A8A;color:#BFDBFE}}
.ghead .gbadge{{font-family:var(--mono);font-size:10px;background:var(--red);color:#fff;padding:1px 6px;border-radius:99px}}
.ghead .chev{{color:#64748B;font-size:10px}}
/* el botón que abre y cierra el módulo se superpone al encabezado */
section[data-testid="stSidebar"] [class*="st-key-tog_"]{{margin-top:-46px;margin-bottom:2px;height:44px;opacity:0}}
section[data-testid="stSidebar"] [class*="st-key-tog_"] button{{height:44px}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button{{padding-left:26px;font-weight:600}}
.mision{{background:linear-gradient(135deg,#2563EB,#7C3AED);color:#fff;border-radius:18px;padding:18px 22px;display:flex;align-items:center;gap:18px;margin-bottom:18px}}
.mision .ico{{width:52px;height:52px;border-radius:15px;background:rgba(255,255,255,.18);display:grid;place-items:center;font-size:24px;flex:none}}
.mision h3{{margin:0 0 3px;font-size:17px;font-weight:800;color:#fff}}
.mision p{{margin:0;font-size:13.5px;opacity:.93;color:#fff}}
.mapa{{display:flex;gap:12px;flex-wrap:wrap}}
.mundo{{flex:1;min-width:130px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;text-align:center}}
.mundo.done{{border-color:transparent;background:var(--green2)}}
.mundo.now{{border-color:var(--blue);box-shadow:0 0 0 4px var(--blue2)}}
.mundo .em{{font-size:24px}}
.mundo b{{display:block;font-size:13px;margin:6px 0 3px;color:var(--ink)}}
.mundo small{{font-size:11.5px;color:var(--mute)}}
.mundo .bar{{height:5px;border-radius:99px;background:var(--line);margin-top:8px;overflow:hidden}}
.mundo .bar i{{display:block;height:100%;background:var(--green)}}
.mundo.done b{{color:var(--greent)}}.mundo.done small{{color:var(--greent)}}
.logros{{display:flex;gap:10px;flex-wrap:wrap}}
.logro{{width:78px;text-align:center;font-size:10.5px;color:var(--mute);line-height:1.25}}
.logro .med{{width:52px;height:52px;border-radius:50%;margin:0 auto 5px;display:grid;place-items:center;font-size:22px;background:var(--line);filter:grayscale(1);opacity:.45}}
.logro.ok .med{{background:var(--amber2);filter:none;opacity:1;box-shadow:0 0 0 3px #FDE68A}}
.logro.ok{{color:var(--ink2);font-weight:600}}
.navgrp{{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#64748B;font-weight:700;margin:14px 0 4px 12px}}
.etapa{{display:inline-flex;align-items:center;gap:8px;padding:5px 12px;border-radius:99px;background:var(--blue2);color:var(--bluet);font-size:12px;font-weight:700;margin-bottom:10px}}
.journey{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
.jcard{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px}}
.jcard .n{{font-family:var(--mono);font-size:12px;color:var(--mute)}}.jcard h5{{margin:4px 0 6px;font-size:15px;color:var(--ink)}}.jcard p{{margin:0;font-size:13px;color:var(--ink2);line-height:1.5}}
section[data-testid="stSidebar"] label[data-selected="true"] p{{color:#fff}}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,section[data-testid="stSidebar"] label p{{color:#CBD5E1!important;background:transparent!important}}
section[data-testid="stSidebar"] hr{{border-color:#1E293B}}
section[data-testid="stSidebar"] [data-testid="stMetricValue"]{{font-family:var(--mono);font-size:1.05rem;color:#fff}}
section[data-testid="stSidebar"] [data-testid="stMetricLabel"] p{{color:#94A3B8;font-size:.8rem}}
section[data-testid="stSidebar"] input{{background:{t['navy2']}!important;color:#fff!important;border-color:#1E293B!important}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px 22px;margin-bottom:16px}}
.card h4{{margin:0 0 10px;font-size:13px;font-weight:600;color:var(--mute)}}
.card p{{margin:0;font-size:14px;color:var(--ink2);line-height:1.55}}
.num{{font-family:var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
.big{{font-size:{'34px' if celular else '42px'};font-weight:600;line-height:1;letter-spacing:-.03em;color:var(--ink)}}
.mid{{font-size:28px;font-weight:600;line-height:1;letter-spacing:-.02em;color:var(--ink)}}
.subrow{{margin-top:14px;display:flex;gap:26px;flex-wrap:wrap;font-size:13px;color:var(--mute)}}
.subrow b{{display:block;font-weight:600;color:var(--ink);font-size:15px;margin-top:2px}}
.bar{{height:8px;border-radius:99px;background:var(--line);overflow:hidden;margin-top:14px}}.bar i{{display:block;height:100%;background:var(--green)}}
.hint{{color:var(--mute);font-size:12px;margin-top:8px}}
.status{{display:flex;align-items:center;gap:8px;font-weight:700;font-size:15px;margin-bottom:6px;color:var(--ink)}}
.dot{{width:10px;height:10px;border-radius:50%;flex:none;display:inline-block}}
.tag{{display:inline-block;margin-top:12px;font-size:12px;font-weight:600;padding:5px 10px;border-radius:8px;font-family:var(--mono)}}
.tag.amber{{background:var(--amber2);color:var(--ambert)}}.tag.green{{background:var(--green2);color:var(--greent)}}.tag.red{{background:var(--red2);color:var(--redt)}}.tag.blue{{background:var(--blue2);color:var(--bluet)}}
.acts{{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:10px}}
.acts li{{display:flex;gap:10px;font-size:13.5px;line-height:1.45;color:var(--ink2)}}.acts li span{{flex:none;width:6px;border-radius:3px;margin-top:3px}}.acts li b{{color:var(--ink)}}
.sem{{display:flex;align-items:center;gap:16px;padding:16px 20px;border-radius:14px;margin-bottom:16px}}
.sem .lamp{{width:42px;height:42px;border-radius:50%;flex:none}}.sem b{{display:block;font-size:15px;margin-bottom:2px}}.sem p{{margin:0;font-size:14px;line-height:1.5}}
.sem.green{{background:var(--green2);color:var(--greent)}}.sem.green .lamp{{background:var(--green)}}.sem.green b,.sem.green p{{color:var(--greent)}}
.sem.amber{{background:var(--amber2);color:var(--ambert)}}.sem.amber .lamp{{background:var(--amber)}}.sem.amber b,.sem.amber p{{color:var(--ambert)}}
.sem.red{{background:var(--red2);color:var(--redt)}}.sem.red .lamp{{background:var(--red)}}.sem.red b,.sem.red p{{color:var(--redt)}}
.sem.mute{{background:var(--line);color:var(--ink2)}}.sem.mute .lamp{{background:var(--mute)}}.sem.mute b,.sem.mute p{{color:var(--ink2)}}
.steps{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}}
.st{{padding:10px 12px;border-radius:10px;border:1px solid var(--line);font-size:12.5px;color:var(--mute)}}.st b{{display:block;font-size:13.5px;color:inherit;margin-bottom:2px}}
.st.done{{background:var(--green2);border-color:transparent;color:var(--greent)}}.st.now{{background:var(--amber2);border-color:transparent;color:var(--ambert)}}
.pill{{display:inline-flex;align-items:center;gap:8px;padding:7px 13px;border-radius:99px;background:var(--card);border:1px solid var(--line);font-size:13px;font-weight:600;color:var(--ink2)}}
.prog{{display:flex;gap:8px;margin:6px 0 18px}}.prog i{{flex:1;height:4px;border-radius:99px;background:var(--line)}}.prog i.d{{background:var(--blue)}}
div[data-testid="stMetric"]{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px}}
div[data-testid="stMetric"] label p{{color:var(--mute)!important;font-size:.8rem}}
div[data-testid="stMetricValue"]{{font-family:var(--mono)!important;font-weight:600;color:var(--ink)!important;font-size:1.5rem!important}}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{{border-radius:10px;font-weight:700;font-family:var(--sans);border:1px solid var(--line);background:var(--card);color:var(--ink2)}}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"],button[data-testid*="primary"],button[data-testid*="primary"] *{{background:var(--blue)!important;border:none;color:#fff!important}}
[data-testid="stWidgetLabel"] p,[data-testid="stWidgetLabel"] label,label[data-testid="stWidgetLabel"]{{color:var(--ink2)!important;font-weight:600;font-size:.85rem}}
[data-testid="stTextInput"] div[data-baseweb="input"],[data-testid="stNumberInput"] div[data-baseweb="input"],[data-testid="stTextArea"] div[data-baseweb="textarea"],[data-testid="stSelectbox"] div[data-baseweb="select"]>div,[data-testid="stDateInput"] div[data-baseweb="input"],div[data-baseweb="base-input"]{{background:var(--field)!important;border-radius:10px!important;border-color:var(--line)!important;color:var(--ink)!important}}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stDateInput"] input,[data-testid="stSelectbox"] div[data-baseweb="select"] *,[data-testid="stTextArea"] textarea{{color:var(--ink)!important;font-family:var(--mono)!important;-webkit-text-fill-color:var(--ink)}}
[data-testid="stTextInput"] div[data-baseweb="input"] *,[data-testid="stNumberInput"] div[data-baseweb="input"] *,[data-testid="stSelectbox"] div[data-baseweb="select"]>div *,[data-testid="stDateInput"] div[data-baseweb="input"] *,[data-testid="stTextArea"] div[data-baseweb="textarea"] *{{background-color:var(--field)!important}}
[data-testid="stNumberInput"] button{{background:var(--field)!important;color:var(--mute)!important;border-color:var(--line)!important}}
[data-testid="stSelectbox"] div[role="group"],[data-testid="stTextInput"] div[role="group"],[data-testid="stNumberInput"] div[role="group"],[data-testid="stDateInput"] div[role="group"],[data-testid="stTextArea"] div[role="group"],[data-testid="stMultiSelect"] div[role="group"]{{background:var(--field)!important;border:1px solid var(--line)!important;border-radius:10px!important;color:var(--ink)!important}}
[data-testid="stSelectbox"] div[role="group"] *,[data-testid="stTextInput"] div[role="group"] *,[data-testid="stNumberInput"] div[role="group"] *,[data-testid="stDateInput"] div[role="group"] *,[data-testid="stTextArea"] div[role="group"] *{{background:transparent!important;color:var(--ink)!important;-webkit-text-fill-color:var(--ink)}}
[data-testid="stSelectbox"] div[role="group"] svg,[data-testid="stNumberInput"] div[role="group"] svg,[data-testid="stDateInput"] div[role="group"] svg{{fill:var(--mute)!important;color:var(--mute)!important}}
section[data-testid="stSidebar"] div[role="group"]{{background:{t['navy2']}!important;border-color:#1E293B!important}}
section[data-testid="stSidebar"] div[role="group"] *{{color:#fff!important;-webkit-text-fill-color:#fff}}
div[role="listbox"],div[role="listbox"] *{{background:var(--card)!important;color:var(--ink)!important}}
[data-testid="stTextInput"] [data-testid$="RootElement"],[data-testid="stNumberInput"] [data-testid$="RootElement"],[data-testid="stNumberInput"] [data-testid="stNumberInputContainer"],[data-testid="stSelectbox"] [data-testid$="RootElement"],[data-testid="stDateInput"] [data-testid$="RootElement"],[data-testid="stDateInput"] [data-testid="stDateInputContainer"],[data-testid="stTextArea"] [data-testid$="RootElement"],[data-testid="stMultiSelect"] [data-testid$="RootElement"]{{background:var(--field)!important;border:1px solid var(--line)!important;border-radius:10px!important;color:var(--ink)!important}}
[data-testid="stNumberInput"] [data-testid="stNumberInputContainer"] button,[data-testid="stNumberInput"] [data-testid$="RootElement"] button{{background:transparent!important;color:var(--mute)!important;border-left:1px solid var(--line)!important}}
section[data-testid="stSidebar"] [data-testid$="RootElement"],section[data-testid="stSidebar"] [data-testid="stNumberInputContainer"]{{background:{t['navy2']}!important;border-color:#1E293B!important}}
section[data-testid="stSidebar"] [data-testid$="RootElement"] *,section[data-testid="stSidebar"] [data-testid="stNumberInputContainer"] *{{color:#fff!important;-webkit-text-fill-color:#fff}}


section[data-testid="stSidebar"] [data-testid="stNumberInput"] div[data-baseweb="input"] *,section[data-testid="stSidebar"] [data-testid="stNumberInput"] input{{background-color:{t['navy2']}!important;color:#fff!important;-webkit-text-fill-color:#fff}}
[data-testid="stSelectbox"] svg{{fill:var(--mute)}}
ul[data-testid="stSelectboxVirtualDropdown"],div[data-baseweb="popover"] ul{{background:var(--card)!important}}div[data-baseweb="popover"] li{{color:var(--ink)!important}}
.stCheckbox p,.stToggle p,.stSlider label p,[data-testid="stMarkdownContainer"] p{{color:var(--ink)}}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{{color:#CBD5E1}}
[data-testid="stExpander"] summary p,[data-testid="stExpander"] summary span{{color:var(--ink)!important}}
[data-testid="stCheckbox"] label>span:first-child{{background:var(--field);border-color:var(--line)}}
[data-testid="stTooltipHoverTarget"],[data-testid="stTooltipHoverTarget"] *{{background:transparent!important}}
[data-testid="stExpander"]{{background:var(--card);border:1px solid var(--line);border-radius:14px}}
[data-testid="stDataFrame"],[data-testid="stDataEditor"]{{border-radius:12px;overflow:hidden}}
.stProgress>div>div>div{{background:var(--blue)}}
.stAlert{{border-radius:12px}}
div[data-testid="stCaptionContainer"] p{{color:var(--mute)}}
</style>""",
        unsafe_allow_html=True,
    )


def clp(v: float) -> str:
    return "$" + f"{v:,.0f}".replace(",", ".")


def usd(v: float) -> str:
    return f"US$ {v:,.2f}"


import json as _json


def autosave(clave: str, datos) -> None:
    """Guarda en la base solo cuando el contenido cambia; muestra la hora del último guardado."""
    raw = _json.dumps(datos, ensure_ascii=False, sort_keys=True, default=str)
    if st.session_state.get(f"_as_{clave}") != raw:
        db.guardar_borrador(clave, datos)
        st.session_state[f"_as_{clave}"] = raw
        st.session_state[f"_as_hora_{clave}"] = datetime.now().strftime("%H:%M:%S")
    hora = st.session_state.get(f"_as_hora_{clave}")
    if hora:
        st.caption(f"Guardado automáticamente · {hora}")


def E(valor) -> str:
    """Escapa datos que escribió una persona antes de inyectarlos en HTML.

    Todo lo que se guarda en la base (nombres de producto, proveedores, descripciones de
    solicitudes o de brechas) puede contener etiquetas. Sin esto, un usuario podría guardar
    <script> en un campo y ejecutarlo en la pantalla del administrador.
    """
    return html_escape("" if valor is None else str(valor), quote=True)


def isotipo(px: int = 34, fondo: str = "#2563EB", trazo: str = "#ffffff") -> str:
    """Isotipo de Importo: flecha que entra y se detiene sobre la línea de tu bodega."""
    return (
        f'<svg width="{px}" height="{px}" viewBox="0 0 64 64" role="img" aria-label="Importo" style="display:block">'
        f'<rect x="4" y="4" width="56" height="56" rx="16" fill="{fondo}"></rect>'
        f'<path d="M32 16 V36" stroke="{trazo}" stroke-width="5.5" stroke-linecap="round" fill="none"></path>'
        f'<path d="M23 29 L32 38 L41 29" stroke="{trazo}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" fill="none"></path>'
        f'<path d="M20 47 H44" stroke="{trazo}" stroke-width="5.5" stroke-linecap="round" fill="none"></path>'
        "</svg>"
    )


def mision_banner(cta: bool = True) -> None:
    """Banda con la única acción recomendada para hoy."""
    m = journey.mision_del_dia(_hitos)
    html(f'<div class="mision"><div class="ico">{m["icono"]}</div><div><h3>{E(m["titulo"])}</h3><p>{E(m["detalle"])}</p></div></div>')
    if cta and m.get("hito") and m["pagina"] != st.session_state.get("page"):
        if st.button(f'Ir a {m["pagina"]} →', type="primary", key=f'mision_{m["pagina"]}'):
            st.session_state["page"] = m["pagina"]
            st.rerun()


def esc(s: str) -> str:
    """Evita que Streamlit interprete $...$ como LaTeX en texto markdown."""
    return s.replace("$", "\\$")


def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def sem(color: str, titulo: str, texto: str) -> None:
    html(f'<div class="sem {SEM.get(color, "mute")}"><div class="lamp"></div><div><b>{titulo}</b><p>{texto}</p></div></div>')


def title(t: str, sub: str = "", ayuda: str = "") -> None:
    et = st.session_state.get("_etapa_actual")
    if et:
        html(f'<span class="etapa">{et}</span>')
    st.markdown(f"# {t}")
    if sub:
        html(f'<p class="sub">{sub}</p>')
    if ayuda:
        with st.expander("¿Para qué sirve esta sección y cómo se usa?"):
            st.markdown(ayuda)


def ss(key: str, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


# =============================================================================
# Puerta de acceso: cada usuario entra con su correo y solo ve sus datos
# =============================================================================
usuario = auth.usuario_actual()
if usuario is None:
    inject_css(False, False)
    st.markdown("<style>section[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 1.1, 1])
    with centro:
        html('<div style="text-align:center;margin:40px 0 18px"><div style="display:flex;justify-content:center">' + isotipo(54) + '</div><h1 style="margin:14px 0 2px;letter-spacing:-.03em">Importo</h1><p class="sub" style="margin:0">Tu costo real, puesto en bodega</p></div>')
        t_login, t_reg = st.tabs(["Iniciar sesión", "Crear cuenta"])
        with t_login:
            with st.form("login"):
                email = st.text_input("Correo electrónico", autocomplete="email", help="El correo con el que creaste tu cuenta.")
                pw = st.text_input("Contraseña", type="password", autocomplete="current-password", help="Si la olvidaste, pide al administrador que te cree una cuenta nueva o restablezca el acceso.")
                if st.form_submit_button("Entrar", type="primary", width="stretch"):
                    u, msg = auth.login(email, pw)
                    if u:
                        auth.iniciar_sesion(u)
                        st.rerun()
                    st.error(msg)
        with t_reg:
            with st.form("registro"):
                email_r = st.text_input("Correo electrónico personal", autocomplete="email", help="Será tu usuario y el contacto para ejercer tus derechos sobre tus datos. Usa uno que revises.")
                nombre_r = st.text_input("Tu nombre", help="Cómo quieres que la app te salude. Puedes cambiarlo después en Mi cuenta.")
                pw_r = st.text_input("Contraseña (mín. 8, letras y números)", type="password", autocomplete="new-password", help="Mínimo 8 caracteres con al menos una letra y un número. No la compartas.")
                pw_r2 = st.text_input("Repite la contraseña", type="password", autocomplete="new-password", help="Debe coincidir exactamente con la anterior.")
                with st.expander("Leer la Política de Privacidad (Ley 19.628 / 21.719)"):
                    st.markdown(privacy.politica_privacidad())
                acepta = st.checkbox("He leído y acepto la Política de Privacidad y el tratamiento de mis datos para usar el servicio")
                comunica = st.checkbox("Acepto recibir avisos y novedades por correo (opcional, puedes retirarlo cuando quieras)")
                if st.form_submit_button("Crear cuenta", type="primary", width="stretch"):
                    if pw_r != pw_r2:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        ok, msg = auth.registrar(email_r, nombre_r, pw_r, acepta, comunica, privacy.VERSION_POLITICA)
                        (st.success if ok else st.error)(msg)
        st.caption("Tus datos quedan asociados a tu correo y no son visibles para otros usuarios. La sesión expira tras 8 horas sin actividad.")
    st.stop()

db.set_usuario_actual(usuario.id, usuario.rol)

# Si la política cambió desde la última aceptación, pedir aceptación de la nueva versión
_ult = db.ultimo_consentimiento(usuario.id, "politica_privacidad")
if not _ult or _ult["version"] != privacy.VERSION_POLITICA or not _ult["aceptado"]:
    inject_css(False, False)
    st.markdown("<style>section[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 1.4, 1])
    with centro:
        title("Actualizamos la Política de Privacidad", f"Versión {privacy.VERSION_POLITICA}. Necesitamos que la aceptes para seguir usando tu cuenta.")
        with st.container(height=380):
            st.markdown(privacy.politica_privacidad())
        a, b = st.columns(2)
        if a.button("Acepto la nueva versión", type="primary", width="stretch"):
            db.registrar_consentimiento(usuario.id, "politica_privacidad", privacy.VERSION_POLITICA, True, "Aceptada al iniciar sesión")
            db.auditar("consentimiento", f"política v{privacy.VERSION_POLITICA} aceptada")
            st.rerun()
        if b.button("No acepto · cerrar sesión", width="stretch"):
            auth.cerrar_sesion()
            st.rerun()
    st.stop()


# =============================================================================
# Estado global y alertas (para badges de navegación)
# =============================================================================
liberadas = db.liberar_ventas_vencidas()
lead_time = int(db.get_config_float("lead_time_dias", 58))


def calcular_alertas() -> list[tuple[str, str, str]]:
    """[(color, título, detalle)] para dashboard y badges."""
    out: list[tuple[str, str, str]] = []
    for e in db.list_embarques():
        if e["estado"] != "En Bodega":
            est = estado_dias_libres(date.fromisoformat(e["fecha_eta"]), e["dias_libres"], estado_embarque=e["estado"])
            if est.color == "rojo":
                out.append(("rojo", f"Retirar {e['producto']}", est.mensaje))
            elif est.color == "ambar":
                out.append(("ambar", f"Retirar {e['producto']} del extraportuario", est.mensaje))
    ventas_all = db.list_ventas()
    for inv in db.list_inventario():
        vs = [v for v in ventas_all if v["producto_id"] == inv["id"]]
        if vs:
            dias_hist = max(1, (date.today() - min(date.fromisoformat(v["fecha"]) for v in vs)).days + 1)
            cs = cobertura_stock(inv["unidades_disponibles"], sum(v["cantidad"] for v in vs) / dias_hist, lead_time)
            if cs.color == "rojo":
                out.append(("rojo", f"Reponer {inv['producto']} ya", cs.mensaje))
            elif cs.color == "ambar":
                out.append(("ambar", f"Emitir orden de {inv['producto']}", cs.mensaje))
    return sorted(out, key=lambda a: 0 if a[0] == "rojo" else 1)


_hitos, _nuevos_hitos = journey.evaluar()
_ruta = journey.resumen(_hitos)
alertas = calcular_alertas()
n_ret = sum(1 for v in db.list_ventas() if v["estado_liquidacion"] == "Retenido")

# =============================================================================
# Sidebar: marca, navegación, ajustes
# =============================================================================
with st.sidebar:
    html('<div class="brand">' + isotipo(32, fondo="#ffffff", trazo="#2563EB") + '<span>Importo</span></div>')
    _mods = journey.progreso_modulos(_hitos)
    _mod_actual = journey.modulo_actual(_mods)
    ETAPA_DE = {p: m["nombre"] for m in _mods for p in m["paginas"]}
    badges = {}
    if alertas:
        badges["Operación y stock"] = str(len(alertas))
    if n_ret:
        badges["Ventas y dossier"] = str(n_ret)
    if usuario.rol == "admin":
        _est = db.estadisticas_tratamiento()
        _pend = _est["solicitudes_pendientes"] + _est["incidentes_abiertos"]
        if _pend:
            badges["Cumplimiento (admin)"] = str(_pend)
    if "page" not in st.session_state:
        st.session_state["page"] = "Empieza aquí" if db.get_config("onboarding_visto", "0") != "1" else "Panel de hoy"
    page = st.session_state["page"]
    _mod_pagina = journey.MODULO_DE_PAGINA.get(page, {}).get("clave", "aprende")

    # --- Tarjeta del jugador: nivel, progreso y racha ---
    _niv, _ = journey.nivel(_ruta["hechos"])
    _r = journey.racha()
    _grados = int(_ruta["pct"] * 360)
    _chispas = "".join('<i class="on"></i>' if d else "<i></i>" for d in _r["ultimos7"])
    _anillo = f'conic-gradient(#10B981 0 {_grados}deg,#243044 {_grados}deg 360deg)'
    html(
        '<div class="player"><div class="ptop">'
        f'<div class="ring" style="background:{_anillo}"><span>{_ruta["pct"]*100:.0f}%</span></div>'
        f'<div><b>Nivel {_niv}</b><small>{_ruta["hechos"]} de {_ruta["total"]} logros</small></div></div>'
        f'<div class="streak">{_chispas}</div>'
        f'<small class="rtxt">{_r["mensaje"]}</small></div>'
    )

    # --- Módulos plegables ---
    for _m in _mods:
        _abierto_def = _m["clave"] in (_mod_pagina, _mod_actual)
        _k = f"grp_{_m['clave']}"
        if _k not in st.session_state:
            st.session_state[_k] = _abierto_def
        if _m["clave"] == _mod_pagina and not st.session_state[_k]:
            st.session_state[_k] = True
        _abierto = st.session_state[_k]
        _pill = "ok" if _m["completo"] and _m["total"] else ("now" if _m["clave"] == _mod_actual else "")
        _cont = f'{_m["hechos"]}/{_m["total"]}' if _m["total"] else ""
        _alerta = sum(int(badges[p]) for p in _m["paginas"] if p in badges and badges[p].isdigit())
        html(
            f'<div class="ghead {"open" if _abierto else ""}">'
            f'<span class="gicon" style="background:{_m["color"]}">{_m["emoji"]}</span>'
            f'<span class="gname">{_m["nombre"]}</span>'
            + (f'<span class="gbadge">{_alerta}</span>' if _alerta else "")
            + (f'<span class="pill {_pill}">{_cont}</span>' if _cont else "")
            + f'<span class="chev">{"▾" if _abierto else "▸"}</span></div>'
        )
        if st.button(("Cerrar " if _abierto else "Abrir ") + _m["nombre"], key=f"tog_{_m['clave']}", width="stretch"):
            st.session_state[_k] = not _abierto
            st.rerun()
        if _abierto:
            _hmap = {h.clave: h for h in _m["lista"]}
            for _p in _m["paginas"]:
                if _p == "Cumplimiento (admin)" and usuario.rol != "admin":
                    continue
                _hp = next((h for h in _m["lista"] if h.pagina == _p and h.logrado), None)
                _marca = "✓ " if _hp else ""
                _lbl = f'{_marca}{_p}' + (f"  ·  {badges[_p]}" if _p in badges else "")
                if st.button(_lbl, key=f"nav_{_p}", type="primary" if _p == page else "secondary", width="stretch"):
                    st.session_state["page"] = _p
                    st.rerun()
    st.divider()
    html(f'<div style="font-size:12px;color:#94A3B8;margin-bottom:6px">Sesión de <b style="color:#fff">{E(usuario.nombre)}</b><br>{E(usuario.email)}<br><span style="color:#64748B">Importo v{__version__}</span></div>')
    if st.button("Cerrar sesión", width="stretch"):
        auth.cerrar_sesion()
        st.rerun()
    st.divider()
    modo = st.radio("Modo de costeo", ["Guiado", "Profesional"], horizontal=True, help="Guiado: paso a paso. Profesional: Incoterms, pagos 30/70, auditoría DIN.")
    oscuro = st.toggle("Tema oscuro", value=False, help="Fondo oscuro, más cómodo de noche o en pantallas brillantes.")
    celular = st.toggle("Modo celular", value=False, help="Una columna y letra más grande.")
    st.divider()
    api = fetch_indicadores()
    manual = st.toggle("Dólar manual", value=not api["ok"], key="tc_manual", help="Actívalo si la app no logra consultar mindicador.cl o si quieres simular con otro tipo de cambio.")
    if manual:
        st.number_input("USD observado (CLP)", 1.0, 5000.0, float(st.session_state.get("tc_usd_manual", api["dolar"] or db.get_config_float("tc_usd", 950.0))), 1.0, key="tc_usd_manual", help="Cuántos pesos vale un dólar. Se usa para convertir FOB, flete y aranceles a pesos.")
        st.number_input("UF (CLP)", 1.0, 100000.0, float(st.session_state.get("tc_uf_manual", api["uf"] or db.get_config_float("tc_uf", 39500.0))), 10.0, key="tc_uf_manual", help="Valor de la Unidad de Fomento. Sirve de referencia para umbrales tributarios.")
    rates = get_rates()
    fuente = ("mindicador.cl · " + rates["fecha"]) if rates["api_ok"] and not manual else "valor manual / local"
    html(f'<div style="font-size:12px;color:#94A3B8;line-height:1.8">Dólar observado <span class="num" style="color:#fff;font-size:15px">{clp(rates["usd"])}</span><br>UF <span class="num" style="color:#fff;font-size:15px">{clp(rates["uf"])}</span><br>{fuente}</div>')
    with st.expander("Parámetros"):
        kit_empaque = st.number_input("Kit de empaque por despacho (CLP)", 0.0, 10000.0, db.get_config_float("kit_empaque_clp", 650.0), 50.0, help="Lo que gastas por cada pedido en caja o bolsa, cinta y etiqueta térmica. Parece poco, pero se come el margen.")
        merma_pct = st.slider("Merma y garantía (%)", 0.0, 10.0, db.get_config_float("merma_pct", 4.0), 0.5, help="Porcentaje de la venta que reservas para productos fallados, devoluciones y logística inversa. Lo normal es 3–5 %.") / 100
        lead_time = int(st.number_input("Lead time fabricación + tránsito (días)", 10, 180, lead_time, help="Días desde que emites la orden hasta que el producto está en tu bodega. Marítimo desde China: 50–70 días."))
        # Se guardan solos cuando cambian
        for k, v in (("kit_empaque_clp", kit_empaque), ("merma_pct", merma_pct * 100), ("lead_time_dias", lead_time)):
            if db.get_config_float(k) != float(v):
                db.set_config(k, v)
        if manual:
            for k, v in (("tc_usd", st.session_state["tc_usd_manual"]), ("tc_uf", st.session_state["tc_uf_manual"])):
                if db.get_config_float(k) != float(v):
                    db.set_config(k, v, global_=True)
        st.caption("Se guardan automáticamente.")

TC = rates["usd"]
_m_pag = journey.MODULO_DE_PAGINA.get(page)
st.session_state["_etapa_actual"] = (f'{_m_pag["emoji"]} {_m_pag["nombre"]}' if _m_pag else "")
for _h in _nuevos_hitos:
    st.toast(f"¡Hito logrado! {_h.titulo}", icon="🎉")
if _nuevos_hitos:
    st.balloons()
inject_css(oscuro, celular)
cols = (lambda n, **k: [st.container() for _ in range(n)]) if celular else st.columns
tpl = "plotly_dark" if oscuro else "plotly_white"


def fig_layout(fig: go.Figure, h: int = 340) -> go.Figure:
    fig.update_layout(height=h, margin=dict(l=8, r=8, t=44, b=8), template=tpl, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Manrope, system-ui", color=DARK["ink2"] if oscuro else LIGHT["ink2"]), legend=dict(orientation="h", y=1.12, x=0), title_font=dict(size=15, color=DARK["ink"] if oscuro else LIGHT["ink"]))
    return fig


# =============================================================================
# PÁGINA: Empieza aquí
# =============================================================================
if page == "Empieza aquí":
    db.set_config("onboarding_visto", "1")
    title(f"Hola, {usuario.nombre.split()[0]}. Vamos de cero a tu primera venta.", "La app está ordenada como un camino: cada módulo del menú te deja listo para el siguiente. No necesitas saber de importaciones ni de impuestos para empezar.")
    mision_banner()
    total = sum(len(e["tareas"]) for e in guide.ETAPAS)
    hechas = sum(1 for e in guide.ETAPAS for i in range(len(e["tareas"])) if db.get_config(f"plan_{e['n']}_{i}", "0") == "1")
    siguiente = next(((e, t) for e in guide.ETAPAS for i, t in enumerate(e["tareas"]) if db.get_config(f"plan_{e['n']}_{i}", "0") != "1"), None)
    a, b = st.columns([2, 1]) if not celular else (st.container(), st.container())
    with a:
        st.progress(hechas / total, text=f"Plan del emprendedor: {hechas} de {total} tareas completadas")
        if siguiente:
            st.caption(f"Siguiente tarea del plan · Etapa {siguiente[0]['n']}: {siguiente[1]}")
    with b:
        if st.button("Ir a mi plan por etapas", type="primary", width="stretch"):
            st.session_state["page"] = "Guía del emprendedor"
            st.rerun()
        if st.button("Ver el estado de mi empresa", width="stretch"):
            st.session_state["page"] = "Salud de tu empresa"
            st.rerun()
    st.markdown("### Tus cinco módulos")
    tarjetas = []
    for m in _mods:
        if not m["total"]:
            continue
        estado = "done" if m["completo"] else ("now" if m["clave"] == _mod_actual else "")
        color = "var(--green)" if m["completo"] else ("var(--blue)" if m["clave"] == _mod_actual else "var(--line)")
        etq = "completo" if m["completo"] else ("estás aquí" if m["clave"] == _mod_actual else f'{m["hechos"]} de {m["total"]}')
        tarjetas.append(f'<div class="mundo {estado}"><div class="em">{m["emoji"]}</div><b>{m["nombre"]}</b><small>{etq}</small><p style="font-size:12px;color:var(--mute);margin-top:6px">{m["lema"]}</p><div class="bar"><i style="width:{m["pct"]*100:.0f}%;background:{color}"></i></div></div>')
    html(f'<div class="mapa">{"".join(tarjetas)}</div>')
    if st.button("Ver mi recorrido completo", width="stretch" if celular else "content"):
        st.session_state["page"] = "Mi recorrido"
        st.rerun()

    st.markdown("### Tres cosas que conviene saber desde el día uno")
    html('<div class="card"><p>1. <b>El IVA de la importación no es un costo</b>: lo recuperas en tu F29. Por eso la app separa el landed cost (sin IVA) del desembolso de caja (con IVA).<br>2. <b>El dinero de Mercado Pago tarda hasta 14 días en llegar</b>: la app distingue caja disponible de plata retenida para que no gastes lo que aún no tienes.<br>3. <b>Cada campo tiene un globo de ayuda</b>: pasa el cursor sobre el ícono ⓘ junto a cualquier dato y te explica qué significa y de dónde sacarlo.</p></div>')

# =============================================================================
# PÁGINA: Panel de hoy
# =============================================================================
elif page == "Panel de hoy":
    caja = db.resumen_caja()
    _mes = date.today().strftime("%Y-%m")
    _rm = db.resumen_f29_mensual(_mes)
    f29 = resumen_f29(_rm["credito"], _rm["debito"], _rm["ventas_netas"], _rm["remanente_anterior"], float(db.get_config("tasa_ppm", str(guide.REGIMENES[guide.REGIMEN_DEFAULT]["ppm"] * 100))) / 100)
    embs = db.list_embarques()
    activos = [e for e in embs if e["estado"] != "En Bodega"]
    hoy = date.today()
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    a, b = st.columns([3, 1]) if not celular else (st.container(), st.container())
    with a:
        title(f"Hola, {usuario.nombre.split()[0]}", f"{dias_es[hoy.weekday()]} {hoy.day} de {meses_es[hoy.month-1]} · {len(activos)} embarque(s) activo(s)" + (f" · {liberadas} venta(s) liberadas hoy" if liberadas else ""))
    with b:
        html(f'<div style="text-align:right;margin-top:6px"><span class="pill"><span class="dot" style="background:var(--{SEM[f29.color]})"></span>F29 vence en {f29.dias_para_vencer} días</span></div>')

    total_cobros = caja["en_cuenta"] + caja["retenido"]
    pct = caja["en_cuenta"] / total_cobros * 100 if total_cobros else 0
    prox = [v for v in db.list_ventas() if v["estado_liquidacion"] == "Retenido" and v["fecha_liberacion"]]
    prox_txt = "Sin cobros pendientes"
    if prox:
        f = min(v["fecha_liberacion"] for v in prox)
        prox_txt = f"{date.fromisoformat(f).strftime('%d-%m')} · {clp(sum(v['total_neto'] for v in prox if v['fecha_liberacion'] == f))}"
    c1, c2, c3 = cols(3) if not celular else cols(3)
    with c1:
        html(f'''<div class="card"><h4>Caja disponible hoy</h4><div class="big num">{clp(caja["en_cuenta"])}</div>
        <div class="subrow"><div>Retenido en pasarelas<b class="num">{clp(caja["retenido"])}</b></div><div>Próxima liberación<b>{prox_txt}</b></div></div>
        <div class="bar"><i style="width:{pct:.0f}%"></i></div><div class="hint">{pct:.0f} % de tus cobros ya están en cuenta</div></div>''')
    with c2:
        estado_txt = {"verde": "Tienes colchón fiscal", "ambar": "Colchón fiscal, PPM por pagar", "rojo": "Vas a pagar IVA"}[f29.color]
        tag = f'<span class="tag {SEM[f29.color]}">Pagar el {date.fromisoformat(f29.vencimiento).strftime("%d-%m")} · {clp(f29.total_a_pagar)}</span>' if f29.total_a_pagar else '<span class="tag green">Sin pago previsto</span>'
        html(f'''<div class="card"><h4>IVA y PPM (F29)</h4><div class="status"><span class="dot" style="background:var(--{SEM[f29.color]})"></span>{estado_txt}</div>
        <p>Mes {_mes}: crédito <b class="num">{clp(f29.credito_fiscal)}</b> + remanente <b class="num">{clp(f29.remanente_anterior)}</b> vs débito <b class="num">{clp(f29.debito_fiscal)}</b>.</p>{tag}</div>''')
    with c3:
        if alertas:
            items = "".join(f'<li><span style="background:var(--{SEM[c]})"></span><div><b>{E(t)}</b><br>{E(d)}</div></li>' for c, t, d in alertas[:3])
            html(f'<div class="card"><h4>Requiere tu acción</h4><ul class="acts">{items}</ul></div>')
        else:
            html('<div class="card"><h4>Requiere tu acción</h4><div class="status"><span class="dot" style="background:var(--green)"></span>Todo en orden</div><p>Stock y almacenaje bajo control.</p></div>')

    mision_banner()
    g1, g2 = st.columns([1.6, 1]) if not celular else (st.container(), st.container())
    with g1:
        ventas_all = db.list_ventas()
        inversion = sum(c["desembolso_total_clp"] for c in db.list_cotizaciones())
        if ventas_all:
            df_fc, be_fecha = flujo_caja_acumulado(inversion, ventas_all)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_fc["fecha"], y=df_fc["flujo_acumulado"], mode="lines", name="Caja acumulada", line=dict(color=BASE["blue"], width=3), fill="tozeroy", fillcolor="rgba(37,99,235,.08)"))
            fig.add_hline(y=0, line=dict(color=BASE["green"], dash="dash", width=1.5), annotation_text="Punto de equilibrio", annotation_position="top left")
            fig.update_layout(title="Recuperación de la inversión", yaxis_title="CLP")
            st.plotly_chart(fig_layout(fig, 360), width="stretch")
            st.caption(esc(f"Inversión registrada {clp(inversion)} · " + (f"equilibrio alcanzado el {be_fecha}" if be_fecha else f"faltan {clp(-df_fc['flujo_acumulado'].iloc[-1])} para el equilibrio")))
        else:
            html('<div class="card"><h4>Recuperación de la inversión</h4><p>Registra un embarque y tus primeras ventas para ver la curva real hacia el punto de equilibrio.</p></div>')
    with g2:
        if activos:
            e = activos[0]
            est = estado_dias_libres(date.fromisoformat(e["fecha_eta"]), e["dias_libres"], estado_embarque=e["estado"])
            eta = date.fromisoformat(e["fecha_eta"])
            transito = "done" if hoy >= eta else "now"
            extra = "now" if hoy >= eta else ""
            its = db.list_items(e["cotizacion_id"])
            detalle = (" · ".join(f"{E(i['producto'])} {i['unidades']} u" for i in its) + "<br>") if len(its) > 1 else ""
            html(f'''<div class="card"><h4>Embarque en curso</h4><div class="status"><span class="dot" style="background:var(--{SEM[est.color]})"></span>{E(e["producto"])} · {e["unidades"]} u</div>
            <p>{detalle}{E(est.mensaje)}{(" · " + E(e["forwarder"])) if e["forwarder"] else ""}</p>
            <div class="steps"><div class="st {transito}"><b>Tránsito</b>ETA {eta.strftime("%d-%m")}</div><div class="st {extra}"><b>Extraportuario</b>{max(0, est.dias_transcurridos)} de {e["dias_libres"]} días</div><div class="st"><b>Bodega</b>pendiente</div></div></div>''')
            if st.button("Marcar como retirado a bodega", key="dash_retirar"):
                db.update_embarque_estado(e["id"], "En Bodega")
                st.rerun()
        else:
            html('<div class="card"><h4>Embarque en curso</h4><p>No hay embarques en tránsito. Cotiza uno nuevo en Costeo e internación.</p></div>')

# =============================================================================
# PÁGINA: Costeo e internación (multiproducto)
# =============================================================================
elif page == "Costeo e internación":
    COLS = ["producto", "cajas", "unidades_por_caja", "fob_unit_usd", "largo_cm", "ancho_cm", "alto_cm", "peso_kg", "tlc", "dg", "precio_esperado", "producto_id"]

    def df_default() -> pd.DataFrame:
        return pd.DataFrame([{"producto": "Power bank 20.000 mAh", "cajas": 10, "unidades_por_caja": 50, "fob_unit_usd": 8.5, "largo_cm": 50.0, "ancho_cm": 40.0, "alto_cm": 40.0, "peso_kg": 12.0, "tlc": True, "dg": True, "precio_esperado": 24990.0, "producto_id": None}], columns=COLS)

    if "lineas_df" not in st.session_state:
        bor = db.cargar_borrador("costeo") or {}
        st.session_state["lineas_df"] = pd.DataFrame(bor["lineas"], columns=COLS) if bor.get("lineas") else df_default()
        # Los costos comunes se conservan aunque aún no haya productos (por ejemplo, al llegar desde Cotiza tu flete)
        st.session_state["comunes"] = {**bor.get("comunes", {}), **st.session_state.get("comunes", {})}
    ss("comunes", {})
    C = st.session_state["comunes"]

    def guardar_costeo() -> None:
        autosave("costeo", {"lineas": st.session_state["lineas_df"].to_dict("records"), "comunes": C})

    def editor_lineas() -> pd.DataFrame:
        cat = db.list_productos()
        a, b = st.columns([3, 1]) if not celular else (st.container(), st.container())
        with a:
            sel = st.selectbox("Agregar desde el catálogo", ["—"] + [f"#{p['id']} {p['nombre']}" for p in cat], label_visibility="collapsed", help="Trae un producto que ya guardaste, con sus medidas y FOB, en vez de escribirlo de nuevo.")
        with b:
            if st.button("Agregar al embarque", disabled=sel == "—", width="stretch"):
                p = cat[[f"#{x['id']} {x['nombre']}" for x in cat].index(sel)]
                nueva = {"producto": p["nombre"], "cajas": 5, "unidades_por_caja": p["unidades_por_caja"], "fob_unit_usd": p["fob_unit_usd"], "largo_cm": p["largo_cm"], "ancho_cm": p["ancho_cm"], "alto_cm": p["alto_cm"], "peso_kg": p["peso_kg"], "tlc": bool(p["tlc"]), "dg": bool(p["dg"]), "precio_esperado": 0.0, "producto_id": p["id"]}
                st.session_state["lineas_df"] = pd.concat([st.session_state["lineas_df"], pd.DataFrame([nueva])], ignore_index=True)
                st.rerun()
        st.caption("Una fila por producto. Escribe directo en la tabla, usa la fila vacía del final para agregar otro y selecciona una fila para borrarla. Pasa el cursor sobre el título de cada columna para ver qué significa.")
        df = st.data_editor(
            st.session_state["lineas_df"],
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key="editor_lineas",
            column_config={
                "producto": st.column_config.TextColumn("Producto", required=True, width="medium"),
                "cajas": st.column_config.NumberColumn("Cajas", min_value=1, step=1, format="%d"),
                "unidades_por_caja": st.column_config.NumberColumn("u/caja", min_value=1, step=1, format="%d"),
                "fob_unit_usd": st.column_config.NumberColumn("FOB u. USD", min_value=0.01, format="%.2f"),
                "largo_cm": st.column_config.NumberColumn("Largo cm", min_value=1.0, format="%.0f"),
                "ancho_cm": st.column_config.NumberColumn("Ancho cm", min_value=1.0, format="%.0f"),
                "alto_cm": st.column_config.NumberColumn("Alto cm", min_value=1.0, format="%.0f"),
                "peso_kg": st.column_config.NumberColumn("kg/caja", min_value=0.1, format="%.1f"),
                "tlc": st.column_config.CheckboxColumn("TLC 0 %", help="Con Certificado de Origen. Sin él: 6 %."),
                "dg": st.column_config.CheckboxColumn("DG", help="Baterías de litio / IMO clase 9"),
                "precio_esperado": st.column_config.NumberColumn("Precio venta CLP", min_value=0.0, format="%.0f", help="Con IVA. Solo para el semáforo de viabilidad."),
                "producto_id": None,
            },
        )
        df = df.dropna(subset=["producto"]).copy()
        for c in ("cajas", "unidades_por_caja"):
            df[c] = df[c].fillna(1).astype(int)
        for c in ("fob_unit_usd", "largo_cm", "ancho_cm", "alto_cm", "peso_kg", "precio_esperado"):
            df[c] = df[c].fillna(0.0).astype(float)
        df["tlc"] = df["tlc"].fillna(True).astype(bool)
        df["dg"] = df["dg"].fillna(False).astype(bool)
        st.session_state["lineas_df"] = df
        guardar_costeo()
        return df

    def lineas_de(df: pd.DataFrame) -> list[LineaInput]:
        return [LineaInput(r.producto, int(r.cajas), int(r.unidades_por_caja), float(r.fob_unit_usd), float(r.largo_cm), float(r.ancho_cm), float(r.alto_cm), float(r.peso_kg), bool(r.tlc), bool(r.dg), int(r.producto_id) if pd.notna(r.producto_id) else None) for r in df.itertuples()]

    def resumen_lote(df: pd.DataFrame) -> None:
        from customs_engine import cubicaje_lote
        cb = cubicaje_lote(lineas_de(df))
        fob = float((df["fob_unit_usd"] * df["cajas"] * df["unidades_por_caja"]).sum())
        a, b, c = cols(3)
        with a:
            html(f'<div class="card"><h4>Volumen del lote</h4><div class="mid num">{cb.cbm_total:.2f} m³</div><p style="margin-top:10px">{cb.unidades_totales} unidades · {len(df)} SKU · {cb.peso_bruto_total_kg:.0f} kg<br>Pagas <b>{cb.m3_facturados} m³</b>' + (f": caben <b>{cb.cajas_extra_sin_costo} cajas más ({cb.unidades_extra_sin_costo} u)</b> sin flete extra." if cb.cajas_extra_sin_costo else ". Una caja más paga el siguiente m³.") + "</p></div>")
        with b:
            html(f'<div class="card"><h4>FOB total</h4><div class="mid num">{usd(fob)}</div><p style="margin-top:10px">{clp(fob*TC)} al dólar de hoy<br>Peso volumétrico aéreo {cb.peso_cobrable_aereo_kg:.0f} kg</p></div>')
        with c:
            html(f'<div class="card"><h4>Regla W/M marítima</h4><div class="mid num">{cb.wm_maritimo:.2f}</div><p style="margin-top:10px">Se cobra por {cb.cobra_por.lower()}<br>{"Lleva carga peligrosa (DG): el flete tendrá recargo." if df["dg"].any() else "Sin carga peligrosa."}</p></div>')

    def form_comunes(pro: bool) -> None:
        a, b, c = cols(3)
        with a:
            C["origen"] = st.text_input("Origen", C.get("origen", "Shenzhen"), help="Ciudad o puerto donde embarca el proveedor. Solo informativo, para identificar el embarque.")
            C["flete"] = st.number_input("Flete internacional total (USD)", 0.0, 1_000_000.0, float(C.get("flete", 720.0)), 10.0, help="Cotización del forwarder por todo el lote.")
            C["dg_pct"] = st.slider("Recargo DG si hay baterías (%)", 0, 60, int(C.get("dg_pct", 30)), help="Los forwarders recargan el flete por carga peligrosa (IMO clase 9). Suele ser 25–40 %. Se aplica solo si marcaste DG en algún producto.")
        with b:
            C["destino"] = st.text_input("Destino", C.get("destino", "San Antonio"), help="Puerto o aeropuerto de llegada en Chile: San Antonio, Valparaíso, Iquique, SCL.")
            C["seguro"] = st.number_input("Seguro contratado (USD, 0 = presunto 2 %)", 0.0, 100_000.0, float(C.get("seguro", 0.0)), 5.0, help="Si contrataste una póliza, pon su prima. Si dejas 0, Aduanas presume un 2 % del FOB para calcular el CIF.")
            C["criterio"] = st.selectbox("Prorrateo de costos comunes", list(CRITERIOS_PRORRATEO), index=list(CRITERIOS_PRORRATEO).index(C.get("criterio", "cbm")), format_func=lambda k: CRITERIOS_PRORRATEO[k], help="Cómo repartir flete, agente y gastos locales entre productos.")
        with c:
            C["forwarder"] = st.text_input("Forwarder / naviera", C.get("forwarder", ""), help="Empresa que te cotizó el flete. Solo para tu referencia.")
            C["psi"] = st.number_input("Inspección pre-embarque PSI (USD)", 0.0, 5000.0, float(C.get("psi", 0.0)), 10.0, help="Recomendado 150–250 USD para productos críticos.")
            if pro:
                C["incoterm"] = st.selectbox("Incoterm 2020", INCOTERMS, index=INCOTERMS.index(C.get("incoterm", "FOB")), help="Regla que define qué costos incluye el precio del proveedor. FOB es lo más común: mercadería puesta a bordo en origen.")
                C["costos_origen"] = st.number_input("Costos en origen EXW (USD)", 0.0, 100_000.0, float(C.get("costos_origen", 0.0)), 10.0, disabled=C["incoterm"] != "EXW", help="Solo en EXW: transporte interno en el país del proveedor más despacho de exportación.")
                C["tc_aduanero"] = st.number_input("Dólar aduanero de la DIN (0 = usar observado)", 0.0, 5000.0, float(C.get("tc_aduanero", 0.0)), 1.0, help="Aduana liquida con el tipo de cambio que publica para la fecha de aceptación de la DIN; puede diferir del observado.")
            else:
                C["incoterm"], C["costos_origen"] = "FOB", 0.0
        guardar_costeo()

    def form_locales(pro: bool) -> None:
        a, b, c, d = cols(4)
        C["descons"] = a.number_input("Desconsolidación / puerto (CLP)", 0.0, 5_000_000.0, float(C.get("descons", 180_000.0)), 5000.0)
        C["almac"] = b.number_input("Almacenaje extraportuario (CLP)", 0.0, 5_000_000.0, float(C.get("almac", 60_000.0)), 5000.0)
        C["transp"] = c.number_input("Transporte a bodega (CLP)", 0.0, 5_000_000.0, float(C.get("transp", 90_000.0)), 5000.0)
        C["otros"] = d.number_input("Otros gastos (CLP)", 0.0, 5_000_000.0, float(C.get("otros", 0.0)), 5000.0)
        if pro:
            a, b = cols(2)
            C["tarifa_agente"] = a.number_input("Tarifa base agente de aduana (USD)", 50.0, 2000.0, float(C.get("tarifa_agente", 150.0)), 10.0)
            C["forzar_agente"] = b.checkbox("Usar agente aunque CIF ≤ US$3.000", C.get("forzar_agente", False))
        else:
            C.setdefault("tarifa_agente", 150.0)
            C.setdefault("forzar_agente", False)
        guardar_costeo()

    def calcular(df: pd.DataFrame) -> LoteResult:
        tc_liq = C.get("tc_aduanero") or TC
        comunes = LiquidacionInput(producto="lote", unidades=0, fob_unit_usd=0, flete_usd=C.get("flete", 0), tipo_cambio=tc_liq, incoterm=C.get("incoterm", "FOB"), tlc=True,
                                   recargo_dg_pct=C.get("dg_pct", 0) / 100, seguro_usd=C.get("seguro") or None, costos_origen_usd=C.get("costos_origen", 0),
                                   tarifa_agente_base_usd=C.get("tarifa_agente", 150.0), forzar_agente=C.get("forzar_agente", False),
                                   desconsolidacion_clp=C.get("descons", 0), almacenaje_clp=C.get("almac", 0), transporte_clp=C.get("transp", 0), otros_clp=C.get("otros", 0), psi_usd=C.get("psi", 0))
        return liquidar_lote(lineas_de(df), comunes, C.get("criterio", "cbm"))

    def mostrar_resultado(lote: LoteResult, df: pd.DataFrame) -> None:
        tot = lote.total
        # Semáforo de viabilidad ponderado por unidades
        margen_w, peso_w = 0.0, 0
        det = []
        for l, r in zip(lote.lineas, df.itertuples()):
            if r.precio_esperado > 0:
                m = calcular_mix({c.nombre: r.precio_esperado for c in canales_default()}, l.landed_unit_clp, canales_default(), kit_empaque, merma_pct)
                det.append((l.producto, r.precio_esperado, m.margen_ponderado, m.margen_pct_ponderado))
                margen_w += m.margen_pct_ponderado * l.unidades
                peso_w += l.unidades
        if peso_w:
            pct = margen_w / peso_w
            color, texto = semaforo_viabilidad(pct, tot.factor_internacion)
            peor = min(det, key=lambda d: d[3])
            extra = f" El SKU más ajustado es {peor[0]} ({peor[3]:.1f} %)." if len(det) > 1 else ""
            st.session_state["viab"] = (color, texto)
            sem(color, f"{'Negocio viable' if color == 'verde' else 'Viable con cuidado' if color == 'ambar' else 'No recomendable'} · margen limpio ponderado {pct:.1f} %", texto + extra)
        else:
            st.session_state["viab"] = None
            st.info("Ingresa un precio de venta esperado por producto para ver el semáforo de viabilidad.")

        a, b = st.columns([1.6, 1]) if not celular else (st.container(), st.container())
        with a:
            html('<div class="card" style="margin-bottom:8px"><h4>Liquidación aduanera del embarque</h4></div>')
            dfp = pd.DataFrame(tot.pasos)
            dfp["USD"] = dfp["usd"].map(usd)
            dfp["CLP"] = dfp["clp"].map(clp)
            st.dataframe(dfp[["paso", "USD", "CLP"]].rename(columns={"paso": "Concepto"}), width="stretch", hide_index=True)
            if tot.agente_obligatorio:
                st.caption(esc(f"Agente de aduana obligatorio: CIF {usd(tot.cif_usd)} supera US$3.000 ({tot.agente_detalle})."))
        with b:
            html(f'''<div class="card"><h4>Costo unitario promedio en bodega</h4><div class="big num">{clp(tot.landed_unit_clp)}</div><div class="hint">sin IVA · el IVA vuelve como crédito fiscal</div>
            <div class="subrow"><div>Desembolso total<b class="num">{clp(tot.desembolso_total_clp)}</b></div><div>Factor internación<b class="num">{tot.factor_internacion:.2f}×</b></div><div>IVA recuperable<b class="num">{clp(tot.iva_clp)}</b></div></div></div>''')
            cb = lote.cubicaje
            html(f'<div class="card"><h4>Cubicaje</h4><p>{cb.cbm_total:.2f} m³ · {cb.peso_bruto_total_kg:.0f} kg · pagas <b>{cb.m3_facturados} m³</b>.' + (f' Caben <b>{cb.cajas_extra_sin_costo} cajas más ({cb.unidades_extra_sin_costo} u)</b> sin flete adicional.' if cb.cajas_extra_sin_costo else '') + f'</p><div class="bar"><i style="width:{min(100, cb.cbm_total / cb.m3_facturados * 100):.0f}%;background:var(--blue)"></i></div></div>')

        html('<div class="card" style="margin-bottom:8px"><h4>Costo por producto (costos comunes repartidos ' + CRITERIOS_PRORRATEO[lote.criterio].lower() + ')</h4></div>')
        dfl = pd.DataFrame([l.to_dict() for l in lote.lineas])
        show = pd.DataFrame({
            "Producto": dfl["producto"], "Unidades": dfl["unidades"], "m³": dfl["cbm"].round(3), "Reparto": (dfl["participacion"] * 100).round(0).astype(int).astype(str) + " %",
            "FOB u.": dfl["fob_unit_usd"].map(lambda v: f"{v:.2f}"), "Arancel": dfl["tasa_advalorem"].map(lambda v: "TLC 0 %" if v == 0 else "6 %"),
            "Comunes u.": (dfl["comunes_clp"] / dfl["unidades"]).round(0).map(clp), "Landed u.": dfl["landed_unit_clp"].map(clp), "Con IVA u.": dfl["desembolso_unit_clp"].map(clp), "Factor": dfl["factor_internacion"].map(lambda v: f"{v:.2f}×"),
        })
        if det:
            mp = {d[0]: f"{clp(d[2])} ({d[3]:.0f} %)" for d in det}
            show["Margen limpio u."] = dfl["producto"].map(mp).fillna("—")
        st.dataframe(show, width="stretch", hide_index=True)

    def registrar_ui(lote: LoteResult, key: str) -> None:
        html('<div class="card" style="margin-bottom:8px"><h4>Registrar embarque</h4><p>Crea la cotización, el embarque con sus días libres, un ítem de inventario por producto y anota el IVA como crédito fiscal.</p></div>')
        a, b, c = cols(3)
        eta = a.date_input("Fecha estimada de arribo (ETA)", date.today() + timedelta(days=lead_time), key=f"{key}_eta")
        dl = int(b.number_input("Días libres de almacenaje", 1, 30, int(db.get_config_float("dias_libres_default", 5)), key=f"{key}_dl"))
        guardar_cat = c.checkbox("Guardar productos nuevos en el catálogo", True, key=f"{key}_cat")
        if st.button("Registrar embarque", type="primary", key=f"{key}_btn"):
            tot = lote.total
            cot = db.Cotizacion(producto=tot.producto, unidades=tot.unidades, fob_unit_usd=tot.fob_unit_usd, fob_total_usd=tot.fob_total_usd, flete_usd=tot.flete_usd, seguro_usd=tot.seguro_usd, cif_usd=tot.cif_usd, cif_clp=tot.cif_clp,
                                advalorem_usd=tot.advalorem_usd, iva_usd=tot.iva_usd, honorarios_usd=tot.honorarios_usd, gastos_locales_clp=tot.gastos_locales_clp, landed_clp=tot.landed_clp, landed_usd=tot.landed_usd, landed_unit_clp=tot.landed_unit_clp,
                                desembolso_total_clp=tot.desembolso_total_clp, factor_internacion=tot.factor_internacion, tipo_cambio=TC, incoterm=tot.incoterm, tlc=int(tot.tlc), cbm_total=lote.cubicaje.cbm_total,
                                peso_kg=lote.cubicaje.peso_bruto_total_kg, cajas=sum(l.cajas for l in lote.lineas), origen=C.get("origen", ""), destino=C.get("destino", ""), prorrateo=lote.criterio, n_items=len(lote.lineas))
            items = []
            for l, r in zip(lote.lineas, st.session_state["lineas_df"].itertuples()):
                pid = l.producto_id
                if guardar_cat and pid is None:
                    pid = db.upsert_producto(db.Producto(nombre=l.producto, largo_cm=r.largo_cm, ancho_cm=r.ancho_cm, alto_cm=r.alto_cm, peso_kg=r.peso_kg, unidades_por_caja=l.unidades_por_caja, fob_unit_usd=l.fob_unit_usd, tlc=int(l.tlc), dg=int(l.dg)))
                items.append(db.CotizacionItem(producto=l.producto, cajas=l.cajas, unidades_por_caja=l.unidades_por_caja, unidades=l.unidades, fob_unit_usd=l.fob_unit_usd, fob_total_usd=l.fob_total_usd, cbm=l.cbm, peso_kg=l.peso_kg,
                                               participacion=l.participacion, flete_usd=l.flete_usd, seguro_usd=l.seguro_usd, cif_usd=l.cif_usd, advalorem_usd=l.advalorem_usd, iva_usd=l.iva_usd, iva_clp=l.iva_clp, comunes_clp=l.comunes_clp,
                                               landed_clp=l.landed_clp, landed_unit_clp=l.landed_unit_clp, desembolso_unit_clp=l.desembolso_unit_clp, factor_internacion=l.factor_internacion, tlc=int(l.tlc), dg=int(l.dg), producto_id=pid))
            ids = db.registrar_importacion(cot, eta, dl, C.get("forwarder", ""), tot.iva_clp, items)
            st.success(esc(f"Embarque #{ids['embarque_id']} registrado con {len(items)} producto(s). IVA {clp(tot.iva_clp)} anotado como crédito fiscal."))

    # ---------------- Modo guiado ----------------
    if modo == "Guiado":
        step = ss("wiz_step", 1)
        subt = {1: "¿Qué productos vienen en este embarque?", 2: "Flete, seguro y reparto de costos", 3: "Gastos en Chile", 4: "Resultado y viabilidad"}
        title("¿Cuánto me cuesta puesto en bodega?", f"Paso {step} de 4 · {subt[step]}", ayuda="""**Qué hace:** te lleva paso a paso hasta saber el costo real de cada producto en tu bodega y si el negocio deja margen.\n\n**Cómo se usa:** completa cada paso y avanza. Todo se guarda solo: si cierras la app, vuelves donde quedaste.\n\n**Si no conoces un término** (FOB, CIF, TLC, W/M), míralo en el Glosario.""")
        html('<div class="prog">' + "".join(f'<i class="{"d" if i <= step else ""}"></i>' for i in range(1, 5)) + "</div>")
        if step == 1:
            df = editor_lineas()
            if len(df):
                resumen_lote(df)
            if st.button("Siguiente: flete y seguro", type="primary", disabled=len(df) == 0):
                st.session_state["wiz_step"] = 2
                st.rerun()
        elif step == 2:
            form_comunes(False)
            a, b = cols(2)
            if a.button("Anterior"):
                st.session_state["wiz_step"] = 1
                st.rerun()
            if b.button("Siguiente: gastos en Chile", type="primary"):
                st.session_state["wiz_step"] = 3
                st.rerun()
        elif step == 3:
            form_locales(False)
            a, b = cols(2)
            if a.button("Anterior"):
                st.session_state["wiz_step"] = 2
                st.rerun()
            if b.button("Calcular costo", type="primary"):
                st.session_state["wiz_step"] = 4
                st.rerun()
        else:
            df = st.session_state["lineas_df"]
            try:
                lote = calcular(df)
                st.session_state["lote"] = lote
                mostrar_resultado(lote, df)
                registrar_ui(lote, "w")
            except ValueError as exc:
                st.error(str(exc))
            a, b = cols(2)
            if a.button("Ajustar datos"):
                st.session_state["wiz_step"] = 1
                st.rerun()
            if b.button("Nuevo embarque"):
                st.session_state["lineas_df"] = df_default()
                st.session_state["comunes"] = {}
                st.session_state["wiz_step"] = 1
                st.rerun()

    # ---------------- Modo profesional ----------------
    else:
        title("Costeo e internación", "Embarque multiproducto · Incoterms 2020 · pagos escalonados · auditoría DIN", ayuda="""**Qué hace:** calcula cuánto te cuesta de verdad cada producto puesto en tu bodega, sumando flete, seguro, arancel, IVA, agente de aduana y gastos de puerto.\n\n**Cómo se usa:** 1) agrega los productos del embarque; 2) pon el flete y el seguro que te cotizó el forwarder; 3) los gastos en Chile; 4) revisa el resultado y registra el embarque.\n\n**Dato clave:** el IVA no es costo, lo recuperas en tu F29. Por eso el *landed cost* va sin IVA y aparte se muestra el desembolso real de caja.""")
        st.markdown("### 1. Productos del embarque")
        df = editor_lineas()
        if len(df):
            resumen_lote(df)
        st.markdown("### 2. Flete, seguro y condiciones comerciales")
        form_comunes(True)
        st.markdown("### 3. Gastos en Chile")
        form_locales(True)
        if len(df):
            lote = calcular(df)
            st.session_state["lote"] = lote
            st.markdown("### 4. Resultado")
            mostrar_resultado(lote, df)
            tot = lote.total
            with st.expander("Pagos escalonados 30/70 con doble tipo de cambio"):
                a, b, c = cols(3)
                pct_ant = a.slider("% anticipo", 0, 100, 30) / 100
                tc1 = b.number_input("Dólar al pagar el anticipo", 500.0, 2000.0, float(TC), 1.0)
                tc2 = c.number_input("Dólar al pagar el saldo", 500.0, 2000.0, float(TC), 1.0)
                pe = calcular_pago_escalonado(PagoEscalonado(tot.fob_total_usd, pct_ant, tc1, tc2))
                a, b, c, d = cols(4)
                a.metric("Anticipo", clp(pe["anticipo_clp"]), usd(pe["anticipo_usd"]))
                b.metric("Saldo", clp(pe["saldo_clp"]), usd(pe["saldo_usd"]))
                c.metric("Dólar efectivo", f"${pe['tc_efectivo']:,.2f}")
                d.metric("Diferencia cambiaria", clp(pe["diferencia_cambiaria_clp"]), "pérdida" if pe["diferencia_cambiaria_clp"] > 0 else "ganancia", delta_color="inverse")
            with st.expander("Auditoría de la DIN (declaración de ingreso)"):
                st.caption("Copia los valores de la DIN emitida por tu agente y compáralos con el cálculo interno. Tolerancia 2 %.")
                a, b, c = cols(3)
                d_fob = a.number_input("FOB declarado (USD)", 0.0, 1e9, float(tot.fob_total_usd))
                d_fle = a.number_input("Flete declarado (USD)", 0.0, 1e9, float(tot.flete_usd))
                d_seg = b.number_input("Seguro declarado (USD)", 0.0, 1e9, float(tot.seguro_usd))
                d_cif = b.number_input("CIF declarado (USD)", 0.0, 1e9, float(tot.cif_usd))
                d_adv = c.number_input("Ad-valorem declarado (USD)", 0.0, 1e9, float(tot.advalorem_usd))
                d_iva = c.number_input("IVA declarado (USD)", 0.0, 1e9, float(tot.iva_usd))
                hall = auditar_din({"fob_total_usd": d_fob, "flete_usd": d_fle, "seguro_usd": d_seg, "cif_usd": d_cif, "advalorem_usd": d_adv, "iva_usd": d_iva}, tot)
                st.dataframe(pd.DataFrame(hall), width="stretch", hide_index=True)
                if any(h["estado"] == "REVISAR" for h in hall):
                    st.error("Hay desvíos superiores al 2 %. Revisa con tu agente antes de pagar la DIN.")
                else:
                    st.success("DIN consistente con el cálculo interno.")
            with st.expander("Control de calidad pre-embarque (PSI) · checklist AQL antes de liberar el saldo"):
                aql = ["Cantidad y SKU coinciden con la orden de compra", "Muestreo AQL 2.5 (defectos mayores) / 4.0 (menores) aprobado", "Funcionalidad probada: capacidad real vs declarada en baterías", "Etiquetado y manual en español; sello SEC o SUBTEL si aplica", "Caja máster resiste apilado y lleva marcas de embarque", "Fotos y video del contenedor sellado con número de precinto"]
                ok = [st.checkbox(x, key=f"aql_{i}") for i, x in enumerate(aql)]
                if all(ok):
                    st.success("PSI aprobado: puedes liberar el pago final.")
                else:
                    st.caption(f"{len(aql) - sum(ok)} verificación(es) pendiente(s).")
            registrar_ui(lote, "p")

# =============================================================================
# PÁGINA: Catálogo de productos
# =============================================================================
elif page == "Catálogo de productos":
    title("Catálogo de productos", "Guarda cada producto una vez y agrégalo a futuros embarques con un clic.", ayuda="""**Qué hace:** guarda la ficha de cada producto (medidas de la caja, FOB, partida arancelaria, proveedor) para no escribirla de nuevo en cada importación.\n\n**Cómo se usa:** crea el producto una vez; después lo agregas a cualquier embarque con un clic. La tabla se edita en línea y se guarda sola.""")
    cat = db.list_productos()
    CATS = ["General", "Baterías de litio / Power banks", "Telecomunicaciones", "Cosméticos / Alimentos", "Textil / Hogar"]
    with st.expander("Nuevo producto o editar existente", expanded=not cat):
        sel = st.selectbox("Producto", ["Nuevo"] + [f"#{p['id']} {p['nombre']}" for p in cat])
        p = cat[[f"#{x['id']} {x['nombre']}" for x in cat].index(sel)] if sel != "Nuevo" else {}
        with st.form("form_prod"):
            a, b, c = cols(3)
            nombre = a.text_input("Nombre", p.get("nombre", ""))
            hs = a.text_input("Partida arancelaria (HS)", p.get("hs_code", "") or "")
            categoria = a.selectbox("Categoría normativa", CATS, index=CATS.index(p["categoria"]) if p.get("categoria") in CATS else 0)
            proveedor = a.text_input("Proveedor", p.get("proveedor", "") or "")
            fob = b.number_input("FOB unitario (USD)", 0.01, 100000.0, float(p.get("fob_unit_usd", 5.0)), 0.1)
            upc = int(b.number_input("Unidades por caja máster", 1, 10000, int(p.get("unidades_por_caja", 50))))
            peso = b.number_input("Peso por caja (kg)", 0.1, 500.0, float(p.get("peso_kg", 10.0)), 0.5)
            tlc = b.checkbox("Certificado de origen TLC (0 %)", bool(p.get("tlc", 1)))
            largo = c.number_input("Largo caja (cm)", 1.0, 300.0, float(p.get("largo_cm", 50.0)))
            ancho = c.number_input("Ancho caja (cm)", 1.0, 300.0, float(p.get("ancho_cm", 40.0)))
            alto = c.number_input("Alto caja (cm)", 1.0, 300.0, float(p.get("alto_cm", 40.0)))
            dg = c.checkbox("Carga peligrosa (baterías de litio)", bool(p.get("dg", 0)))
            notas = st.text_area("Notas (requisitos, certificaciones, contacto)", p.get("notas", "") or "", height=70, help="Espacio libre: contacto del proveedor, certificaciones pendientes, observaciones de calidad.")
            if st.form_submit_button("Guardar producto", type="primary"):
                if not nombre.strip():
                    st.error("Ingresa un nombre.")
                else:
                    db.upsert_producto(db.Producto(nombre=nombre.strip(), hs_code=hs, categoria=categoria, largo_cm=largo, ancho_cm=ancho, alto_cm=alto, peso_kg=peso, unidades_por_caja=upc, fob_unit_usd=fob, tlc=int(tlc), dg=int(dg), proveedor=proveedor, notas=notas, id=p.get("id")))
                    st.success("Producto guardado")
                    st.rerun()
    if cat:
        st.caption("Edita directamente en la tabla: los cambios se guardan solos.")
        dfc = pd.DataFrame(cat)[["id", "nombre", "hs_code", "categoria", "proveedor", "fob_unit_usd", "unidades_por_caja", "largo_cm", "ancho_cm", "alto_cm", "peso_kg", "tlc", "dg"]].copy()
        dfc["tlc"] = dfc["tlc"].astype(bool)
        dfc["dg"] = dfc["dg"].astype(bool)
        edit = st.data_editor(dfc, width="stretch", hide_index=True, key="cat_editor", disabled=["id"], column_config={
            "id": st.column_config.NumberColumn("#", format="%d"), "nombre": "Producto", "hs_code": "HS", "categoria": st.column_config.SelectboxColumn("Categoría", options=CATS), "proveedor": "Proveedor",
            "fob_unit_usd": st.column_config.NumberColumn("FOB u. USD", format="%.2f", min_value=0.01), "unidades_por_caja": st.column_config.NumberColumn("u/caja", format="%d", min_value=1),
            "largo_cm": st.column_config.NumberColumn("Largo", format="%.0f"), "ancho_cm": st.column_config.NumberColumn("Ancho", format="%.0f"), "alto_cm": st.column_config.NumberColumn("Alto", format="%.0f"), "peso_kg": st.column_config.NumberColumn("kg/caja", format="%.1f"),
            "tlc": st.column_config.CheckboxColumn("TLC 0 %"), "dg": st.column_config.CheckboxColumn("DG")})
        cambios = 0
        for orig, (_, row) in zip(cat, edit.iterrows()):
            nuevo = {k: row[k] for k in ("nombre", "hs_code", "categoria", "proveedor", "fob_unit_usd", "unidades_por_caja", "largo_cm", "ancho_cm", "alto_cm", "peso_kg")}
            nuevo["tlc"], nuevo["dg"] = int(bool(row["tlc"])), int(bool(row["dg"]))
            if any(str(orig.get(k)) != str(nuevo[k]) for k in nuevo) and str(nuevo["nombre"]).strip():
                db.upsert_producto(db.Producto(id=orig["id"], nombre=str(nuevo["nombre"]).strip(), hs_code=str(nuevo["hs_code"] or ""), categoria=str(nuevo["categoria"]), largo_cm=float(nuevo["largo_cm"]), ancho_cm=float(nuevo["ancho_cm"]), alto_cm=float(nuevo["alto_cm"]), peso_kg=float(nuevo["peso_kg"]), unidades_por_caja=int(nuevo["unidades_por_caja"]), fob_unit_usd=float(nuevo["fob_unit_usd"]), tlc=nuevo["tlc"], dg=nuevo["dg"], proveedor=str(nuevo["proveedor"] or ""), notas=orig.get("notas") or ""))
                cambios += 1
        if cambios:
            st.toast(f"{cambios} producto(s) actualizado(s)")
            st.rerun()
        a, b = cols(2)
        borrar = a.selectbox("Eliminar del catálogo", ["—"] + [f"#{p['id']} {p['nombre']}" for p in cat])
        if b.button("Eliminar", disabled=borrar == "—"):
            db.delete_producto(int(borrar.split()[0][1:]))
            st.rerun()
    else:
        html('<div class="card"><h4>Tu catálogo está vacío</h4><p>Crea tu primer producto arriba, o regístralo automáticamente al guardar un embarque desde Costeo e internación.</p></div>')

# =============================================================================
# PÁGINA: Precios y márgenes
# =============================================================================
elif page == "Precios y márgenes":
    title("Precios y márgenes", "Mercado Libre, web con Webpay y B2B · margen limpio · calculadora inversa Target 2.5x", ayuda="""**Qué hace:** te dice a qué precio vender en cada canal para ganar de verdad, después de comisiones, envío, publicidad, empaque y merma.\n\n**Cómo se usa:** elige el producto, ajusta comisión y publicidad de cada canal, y reparte el mix de ventas (debe sumar 100 %). El *margen limpio* es lo que realmente te queda por unidad.\n\n**Target 2.5x:** dime tu capital y te digo cuántas unidades comprar y a qué precio venderlas para multiplicarlo.""")
    lote = st.session_state.get("lote")
    inv_list = db.list_inventario()
    fuentes = []
    if lote:
        fuentes += [(f"Cotización actual · {l.producto}", l.landed_unit_clp, l.desembolso_unit_clp, l.factor_internacion, l.producto) for l in lote.lineas]
    for i in inv_list:
        cot = db.get_cotizacion(i["cotizacion_id"]) if i.get("cotizacion_id") else None
        fuentes.append((f"Inventario #{i['id']} · {i['producto']}", i["costo_unitario_clp"], i["costo_unitario_clp"] * (1 + IVA), cot["factor_internacion"] if cot else 1.5, i["producto"]))
    fuentes.append(("Ingresar costo manualmente", None, None, 1.5, ""))
    sel = st.selectbox("Producto a costear", [f[0] for f in fuentes], help="Elige de qué producto quieres fijar precio: uno recién costeado, uno en inventario o un costo manual.")
    f = fuentes[[x[0] for x in fuentes].index(sel)]
    if f[1] is None:
        landed_unit = st.number_input("Landed cost unitario (CLP, sin IVA)", 100.0, 10_000_000.0, 9500.0, 100.0, help="Cuánto te cuesta una unidad puesta en bodega, sin IVA. Si costeaste un embarque, la app lo trae solo.")
        desembolso_unit, factor, nombre_prod = landed_unit * (1 + IVA), 1.5, "Producto"
    else:
        landed_unit, desembolso_unit, factor, nombre_prod = f[1], f[2], f[3], f[4]

    html(f'<div class="card"><h4>Costo en bodega · {E(nombre_prod)}</h4><div class="mid num">{clp(landed_unit)}</div><div class="hint">sin IVA · desembolso con IVA {clp(desembolso_unit)} · factor {factor:.2f}×</div></div>')

    st.markdown("### Canales, mix de ventas y publicidad")
    P = db.cargar_borrador("pricing") or {}
    a, b, c = cols(3)
    with a:
        html('<div class="status">Mercado Libre</div>')
        ml_com = st.slider("Comisión de categoría (%)", 10.0, 20.0, float(P.get("ml_com", 15.0)), 0.5, help="Lo que cobra Mercado Libre por venta según la categoría: entre 13 % y 19 %. Lo ves en tu panel de vendedor.") / 100
        flex = st.checkbox("Bonificación Mercado Envíos Flex", bool(P.get("flex", False)), help="Si despachas tú mismo el día de la compra en tu ciudad, ML bonifica parte del envío.")
        mix_ml = st.number_input("Mix ML (%)", 0, 100, int(P.get("mix_ml", 50)), help="Qué porcentaje de tus ventas esperas hacer en Mercado Libre. Entre los tres canales deben sumar 100 %.")
        p_ml = st.number_input("Precio ML (CLP c/IVA)", 0.0, 10_000_000.0, float(P.get("p_ml", 24990.0)), 500.0, help="Precio de venta al público, con IVA incluido. Desde $19.990 el envío gratis es obligatorio y lo pagas tú.")
        ads_ml = st.number_input("Product Ads ML (% de la venta)", 0.0, 50.0, float(P.get("ads_ml", 5.0)), 0.5, help="ACOS típico en Mercado Libre Ads: 5–15 %.")
    with b:
        html('<div class="status">Web / Instagram · Webpay</div>')
        flete_web = st.number_input("Flete plano que asumes (CLP, 0 = paga el cliente)", 0.0, 50000.0, float(P.get("flete_web", 0.0)), 500.0, help="Si ofreces envío gratis o a precio fijo en tu tienda, pon aquí lo que te cuesta. Si lo paga el cliente, deja 0.")
        mix_web = st.number_input("Mix web (%)", 0, 100, int(P.get("mix_web", 30)), help="Porcentaje de ventas esperado en tu tienda propia e Instagram.")
        p_web = st.number_input("Precio web (CLP c/IVA)", 0.0, 10_000_000.0, float(P.get("p_web", 22990.0)), 500.0, help="Precio en tu tienda, con IVA. Suele ser algo menor que en marketplace porque no pagas comisión.")
        ads_web = st.number_input("Meta / Google Ads (% de la venta)", 0.0, 60.0, float(P.get("ads_web", 15.0)), 0.5, help="Equivale a un ROAS de 100/este %. 15 % = ROAS 6,7.")
        cac_web = st.number_input("Costo fijo por venta web (CLP)", 0.0, 100000.0, float(P.get("cac_web", 0.0)), 500.0, help="Alternativa al %: CAC promedio por pedido.")
    with c:
        html('<div class="status">B2B / Mayorista</div>')
        mix_b2b = st.number_input("Mix B2B (%)", 0, 100, int(P.get("mix_b2b", 20)), help="Porcentaje de ventas al por mayor a otras empresas.")
        p_b2b = st.number_input("Precio B2B (CLP c/IVA)", 0.0, 10_000_000.0, float(P.get("p_b2b", 17990.0)), 500.0, help="Precio mayorista con IVA. Menor margen unitario, pero vendes volumen y cobras por transferencia.")
        ads_b2b = st.number_input("Prospección B2B (% de la venta)", 0.0, 30.0, float(P.get("ads_b2b", 0.0)), 0.5, help="Lo que gastas en conseguir clientes mayoristas: viajes, muestras, comisión de vendedor.")
    autosave("pricing", {"ml_com": ml_com * 100, "flex": flex, "mix_ml": mix_ml, "p_ml": p_ml, "ads_ml": ads_ml, "flete_web": flete_web, "mix_web": mix_web, "p_web": p_web, "ads_web": ads_web, "cac_web": cac_web, "mix_b2b": mix_b2b, "p_b2b": p_b2b, "ads_b2b": ads_b2b})
    canales = canales_default(ml_com, flex, flete_web, (mix_ml / 100, mix_web / 100, mix_b2b / 100), (ads_ml / 100, ads_web / 100, ads_b2b / 100), (0.0, cac_web, 0.0))
    mix = calcular_mix({"Mercado Libre": p_ml, "Web / Instagram": p_web, "B2B / Mayorista": p_b2b}, landed_unit, canales, kit_empaque, merma_pct)
    if not mix.mix_valido:
        st.error(f"El mix suma {mix_ml + mix_web + mix_b2b} %. Ajusta para que sume 100 %.")
    if mix.canales[0].envio_gratis_aplica:
        st.caption(esc(f"Precio ML ≥ {clp(19990)}: envío gratis obligatorio, se descuenta flete del vendedor {clp(mix.canales[0].flete_vendedor)}."))
    dfm = pd.DataFrame([r.to_dict() for r in mix.canales])
    show = dfm[["canal", "precio_bruto", "precio_neto", "comision_neta", "pasarela_neta", "flete_vendedor", "merma", "kit_empaque", "publicidad", "costo_unit", "margen_limpio", "margen_pct_sobre_neto", "cobro_neto_recibido"]].copy()
    show.columns = ["Canal", "Precio", "Neto s/IVA", "Comisión", "Pasarela", "Flete", "Merma", "Kit", "Publicidad", "Costo", "Margen limpio", "% margen", "Llega a cuenta"]
    st.dataframe(show, width="stretch", hide_index=True)
    color, texto = semaforo_viabilidad(mix.margen_pct_ponderado, factor)
    sem(color, f"Margen limpio ponderado {clp(mix.margen_ponderado)} por unidad ({mix.margen_pct_ponderado:.1f} %) · precio ponderado {clp(mix.precio_ponderado)}", texto)
    st.session_state["mix"] = mix
    rw = mix.canales[1]
    st.caption(esc(f"ROAS mínimo en web para no perder dinero: {roas_minimo(rw.margen_limpio + rw.publicidad, rw.precio_bruto)}× (por cada $1 de publicidad debes vender al menos eso). Publicidad ponderada: {clp(sum(r.publicidad * r.mix_pct for r in mix.canales))} por unidad."))

    st.markdown("### Punto de equilibrio mensual (costos fijos)")
    fijos_db = db.costos_fijos_mensuales()
    a, b = cols(2)
    fijos = a.number_input("Costos fijos mensuales netos (CLP)", 0.0, 500_000_000.0, float(P.get("fijos", fijos_db) if fijos_db == 0 else fijos_db), 50_000.0, help="Se toma de los gastos marcados como recurrentes en Gastos y F29. Puedes ajustarlo aquí.")
    pe = punto_equilibrio_mensual(fijos, mix.margen_ponderado, mix.precio_ponderado)
    if pe["viable"]:
        b.metric("Unidades por mes para cubrir fijos", f"{pe['unidades_mes']:.0f}", f"{pe['unidades_dia']:.1f} por día · venta {clp(pe['venta_bruta_mes'])}")
    else:
        b.error("Con margen negativo no hay punto de equilibrio: revisa precios o costos.")

    st.markdown("### Calculadora inversa Target 2.5x")
    a, b = cols(2)
    capital = a.number_input("Capital disponible (CLP)", 100_000.0, 500_000_000.0, 3_000_000.0, 100_000.0)
    multiplo = b.slider("Múltiplo objetivo sobre el capital", 1.5, 4.0, 2.5, 0.1)
    tgt = calcular_target(capital, desembolso_unit, landed_unit, canales, kit_empaque, merma_pct, multiplo)
    st.session_state["target"] = tgt
    a, b, c, d = cols(4)
    a.metric("Unidades que puedes comprar", f"{tgt.unidades_posibles}")
    b.metric("Precio ponderado requerido", clp(tgt.precio_unico_requerido))
    c.metric("Margen requerido por unidad", clp(tgt.margen_unit_requerido_clp))
    d.metric("Retorno objetivo", clp(tgt.meta_retorno_total_clp))
    sem("verde" if tgt.viable else "rojo", f"Target {multiplo:.1f}×", tgt.mensaje)

    st.markdown("### Proyección de caja y punto de equilibrio")
    a, b = cols(2)
    vd = a.number_input("Venta diaria estimada (unidades)", 0.1, 1000.0, 3.0, 0.5, key="vd_pricing")
    ret = int(b.number_input("Días de retención de la pasarela", 0, 30, 14, help="Mercado Pago: 48 h a 14 días · Transbank: 1–3 días hábiles"))
    inv_tot = tgt.capital_usado_clp if tgt.unidades_posibles else desembolso_unit * 100
    dfp, be = proyeccion_flujo(inv_tot, vd, mix.margen_ponderado, mix.cobro_neto_ponderado, ret)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dfp["dia"], y=dfp["flujo_acumulado"], mode="lines", name="Caja acumulada", line=dict(color=BASE["blue"], width=3), fill="tozeroy", fillcolor="rgba(37,99,235,.08)"))
    fig.add_hline(y=0, line=dict(color=BASE["green"], dash="dash"), annotation_text="Punto de equilibrio")
    if be is not None:
        fig.add_vline(x=be, line=dict(color=BASE["green"], dash="dot"), annotation_text=f"Día {be}")
    fig.update_layout(xaxis_title="Día", yaxis_title="CLP")
    st.plotly_chart(fig_layout(fig), width="stretch")
    st.session_state["flujo"] = {"inversion": inv_tot, "venta_diaria": vd, "break_even_dia": be, "retencion": ret}

    st.markdown("### Benchmark en Mercado Libre Chile")
    a, b = cols(2)
    q = a.text_input("Buscar producto similar", nombre_prod or "power bank 20000")
    token = b.text_input("Access token de Mercado Libre (opcional)", "", type="password", help="Si la API pública responde 401/403, usa un token de developers.mercadolibre.cl")
    if st.button("Buscar competencia"):
        st.session_state["ml_res"] = buscar_mercadolibre(q, 50, token)
    res = st.session_state.get("ml_res")
    if res:
        if res["ok"] and res["items"]:
            stt = resumir_precios(res["items"])
            a, b, c, d = cols(4)
            a.metric("Mínimo", clp(stt["min"]))
            b.metric("Mediana", clp(stt["mediana"]))
            c.metric("Máximo", clp(stt["max"]))
            d.metric("Con envío gratis", f"{stt['pct_envio_gratis']:.0f} %", f"{stt['pct_full']:.0f} % Full")
            st.dataframe(items_a_df(res["items"])[["titulo", "precio", "envio_gratis", "logistica", "vendedor", "url"]], width="stretch", hide_index=True, column_config={"url": st.column_config.LinkColumn("Link")})
        else:
            st.warning(f"No se pudo consultar la API: {res['error'] or 'sin resultados'}. Pega precios de la competencia abajo.")
            manual_p = st.text_area("Precios separados por coma", "24990, 21990, 29990, 19990", help="Pega los precios que veas en la competencia, separados por coma, para comparar sin la API.")
            stt = resumen_manual(manual_p)
            if stt["n"]:
                a, b, c = cols(3)
                a.metric("Mínimo", clp(stt["min"]))
                b.metric("Mediana", clp(stt["mediana"]))
                c.metric("Máximo", clp(stt["max"]))

# =============================================================================
# PÁGINA: Operación y stock
# =============================================================================
elif page == "Operación y stock":
    title("Operación y stock", "Días libres en el extraportuario · cobertura de inventario · ciclo cash-to-cash", ayuda="""**Qué hace:** evita las dos pérdidas más caras del importador: pagar sobrestadía por no retirar a tiempo y quedarte sin stock.\n\n**Cómo se usa:** actualiza el estado de cada embarque y revisa los semáforos. Cuando la cobertura de stock baje del lead time, la app te avisa la fecha límite para emitir la siguiente orden.""")
    st.markdown("### Embarques y días libres")
    tarifa_dem = st.number_input("Tarifa de sobrestadía estimada (USD por día)", 10.0, 500.0, 35.0, 5.0, help="Lo que te cobra el almacén extraportuario por cada día pasado los días libres. Suele ser US$25–60.")
    embs = db.list_embarques()
    if not embs:
        html('<div class="card"><h4>Sin embarques</h4><p>Registra tu primer embarque desde Costeo e internación.</p></div>')
    for e in embs:
        est = estado_dias_libres(date.fromisoformat(e["fecha_eta"]), e["dias_libres"], tarifa_dia_usd=tarifa_dem, estado_embarque=e["estado"])
        eta = date.fromisoformat(e["fecha_eta"])
        a, b = st.columns([3, 1]) if not celular else (st.container(), st.container())
        with a:
            d1 = "done" if e["estado"] != "En Tránsito" or date.today() >= eta else "now"
            d2 = "done" if e["estado"] == "En Bodega" else ("now" if e["estado"] == "En Aduana" or date.today() >= eta else "")
            d3 = "done" if e["estado"] == "En Bodega" else ""
            html(f'''<div class="card"><div class="status"><span class="dot" style="background:var(--{SEM[est.color]})"></span>#{e["id"]} {E(e["producto"])} · {e["unidades"]} u{(" · " + E(e["forwarder"])) if e["forwarder"] else ""}</div><p>{E(est.mensaje)}</p>
            <div class="steps"><div class="st {d1}"><b>Tránsito</b>ETA {eta.strftime("%d-%m-%Y")}</div><div class="st {d2}"><b>Extraportuario</b>{e["dias_libres"]} días libres · límite {date.fromisoformat(est.fecha_limite).strftime("%d-%m")}</div><div class="st {d3}"><b>Bodega</b>{"retirado" if d3 else "pendiente"}</div></div></div>''')
        with b:
            opciones = ["En Tránsito", "En Aduana", "En Bodega"]
            nuevo = st.selectbox("Estado", opciones, index=opciones.index(e["estado"]), key=f"est_{e['id']}", help="En Tránsito: viajando. En Aduana: llegó y corre el reloj de días libres. En Bodega: ya lo retiraste.")
            if nuevo != e["estado"]:
                db.update_embarque_estado(e["id"], nuevo)
                st.toast("Estado actualizado")
                st.rerun()
            eta_n = st.date_input("ETA", eta, key=f"eta_{e['id']}", help="Fecha estimada de llegada del barco o avión. Desde aquí cuentan los días libres de almacenaje.")
            dl_n = int(st.number_input("Días libres", 1, 60, int(e["dias_libres"]), key=f"dl_{e['id']}", help="Días sin costo que te da la naviera o el almacén antes de cobrar sobrestadía. Suelen ser 5 a 7."))
            if eta_n != eta or dl_n != e["dias_libres"]:
                db.update_embarque(e["id"], eta_n.isoformat(), dl_n)
                st.toast("Embarque actualizado")
                st.rerun()
            items = db.list_items(e["cotizacion_id"])
            if len(items) > 1:
                st.caption(", ".join(f"{i['producto']} ({i['unidades']} u)" for i in items))
            with st.expander("Eliminar"):
                nv = db.ventas_de_cotizacion(e["cotizacion_id"])
                st.caption("Borra cotización, embarque, inventario y el crédito fiscal asociado." + (f" Tiene {nv} venta(s): se borrarán también con sus débitos." if nv else ""))
                conf = st.checkbox("Confirmo", key=f"delc_{e['id']}")
                if st.button("Eliminar embarque", key=f"delb_{e['id']}", disabled=not conf):
                    res = db.eliminar_cotizacion(e["cotizacion_id"], forzar=True)
                    db.auditar("embarque", f"eliminado COT-{e['cotizacion_id']} {res}")
                    st.rerun()

    st.markdown("### Cobertura de stock y punto de reorden")
    inv_list = db.list_inventario()
    ventas_all = db.list_ventas()
    if not inv_list:
        html('<div class="card"><h4>Sin inventario</h4><p>El inventario se crea automáticamente al registrar un embarque.</p></div>')
    for it in inv_list:
        vs = [v for v in ventas_all if v["producto_id"] == it["id"]]
        vd_auto = sum(v["cantidad"] for v in vs) / max(1, (date.today() - min(date.fromisoformat(v["fecha"]) for v in vs)).days + 1) if vs else 0.0
        a, b = st.columns([1, 3]) if not celular else (st.container(), st.container())
        vd_use = a.number_input(f"Venta diaria · {it['producto']}", 0.0, 1000.0, round(vd_auto, 2), 0.1, key=f"vd_{it['id']}", help="Calculada del historial; puedes sobreescribirla.")
        cs = cobertura_stock(it["unidades_disponibles"], vd_use, lead_time)
        cob = "∞" if cs.dias_cobertura == float("inf") else f"{cs.dias_cobertura:.0f}"
        with b:
            html(f'''<div class="card"><div class="status"><span class="dot" style="background:var(--{SEM[cs.color]})"></span>{E(it["producto"])} · {it["unidades_disponibles"]} u en stock · {cob} días de cobertura</div><p>{E(cs.mensaje)}</p>''' + (f'<span class="tag blue">Reorden sugerido {cs.unidades_reorden_sugeridas} u · costo {clp(cs.unidades_reorden_sugeridas * it["costo_unitario_clp"])}</span>' if cs.unidades_reorden_sugeridas else "") + "</div>")

    st.markdown("### Cash-to-cash: ¿cuándo autofinancias la orden #2?")
    mix_ss = st.session_state.get("mix")
    a, b, c, d = cols(4)
    vd_c2c = a.number_input("Venta diaria (u)", 0.1, 1000.0, 3.0, 0.5, key="vd_c2c")
    cobro_u = b.number_input("Cobro neto por unidad (CLP)", 100.0, 10_000_000.0, float(mix_ss.cobro_neto_ponderado if mix_ss else 18000.0), 500.0, help="Lo que llega a tu cuenta tras comisiones y flete (desde Precios y márgenes).")
    costo_o2 = c.number_input("Costo de la orden #2 (CLP con IVA)", 100_000.0, 500_000_000.0, float(sum(x["desembolso_total_clp"] for x in db.list_cotizaciones()) or 3_000_000.0), 100_000.0)
    ret_c2c = int(d.number_input("Retención pasarela (días)", 0, 30, 14, key="ret_c2c"))
    c2c = ciclo_cash_to_cash(vd_c2c, cobro_u, costo_o2, ret_c2c)
    sem("verde" if c2c.dia_autofinanciamiento is not None else "rojo", "Cash-to-cash", c2c.mensaje)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=c2c.curva["dia"], y=c2c.curva["cobrado_acumulado"], name="Cobros liberados", line=dict(color=BASE["green"], width=3)))
    fig.add_hline(y=costo_o2, line=dict(color=BASE["amber"], dash="dash"), annotation_text="Costo orden #2")
    fig.update_layout(xaxis_title="Día", yaxis_title="CLP")
    st.plotly_chart(fig_layout(fig, 300), width="stretch")
    st.session_state["c2c_msg"] = c2c.mensaje

# =============================================================================
# PÁGINA: Requisitos Chile
# =============================================================================
elif page == "Requisitos Chile":
    title("Requisitos normativos y documentales", "Selecciona el tipo de producto para ver qué necesitas antes de embarcar.", ayuda="""**Qué hace:** lista los documentos y certificaciones que exige la ley chilena según tu producto, más tus obligaciones con el consumidor.\n\n**Cómo se usa:** elige el tipo de producto y marca lo que ya tienes. Revísalo **antes** de pagar el anticipo: un producto sin sello SEC puede quedar retenido.""")
    tipo = st.selectbox("Tipo de producto", ["Baterías de litio / Power banks", "Dispositivos de telecomunicaciones (WiFi, BT, 4G)", "Cosméticos / Alimentos / Suplementos", "Producto general (textil, hogar, accesorios)"], help="Define qué certificaciones y documentos exige la ley chilena para tu producto.")
    base = ["Commercial Invoice con Incoterm, moneda y condiciones de pago", "Packing List con cajas, pesos, dimensiones y unidades por caja", "B/L (marítimo) o AWB (aéreo) original o telex release", "Certificado de Origen TLC (Form F China / TLC USA / UE) para ad-valorem 0 %", "Mandato al agente de aduana si el CIF supera US$3.000", "Inicio de actividades en el SII con giro de importación y RUT vigente"]
    especificos = {
        "Baterías de litio / Power banks": ["MSDS (hoja de seguridad) del fabricante", "Reporte de prueba UN38.3 vigente", "Declaración IMO clase 9 / IATA PI965–967 en la reserva del flete (recargo DG)", "Con enchufe 220 V integrado: sello SEC obligatorio antes de vender", "Solo carga por USB-C o adaptador externo certificado: no requiere sello SEC", "Etiquetado en español: capacidad (mAh/Wh), advertencias, datos del importador"],
        "Dispositivos de telecomunicaciones (WiFi, BT, 4G)": ["Homologación SUBTEL si emite en bandas reguladas (WiFi, BT, celular, LoRa)", "Certificado del fabricante (FCC/CE) como respaldo técnico", "Sello SEC si incluye fuente de poder 220 V", "Etiqueta con número de homologación SUBTEL en producto o empaque"],
        "Cosméticos / Alimentos / Suplementos": ["CDA: Certificado de Destinación Aduanera (SEREMI de Salud / ISP) antes del retiro", "Resolución de Uso y Disposición para liberar el lote", "Registro o notificación sanitaria ISP (cosméticos) o análisis de laboratorio (alimentos)", "Rotulado según RSA (D.S. 977) o D.S. 239 cosméticos, en español", "Bodega autorizada por SEREMI para almacenamiento"],
        "Producto general (textil, hogar, accesorios)": ["Etiquetado de origen y composición (textil: D.S. 26/1984)", "Advertencias de seguridad en español; juguetes: certificación de seguridad", "Marcas registradas INAPI: evita productos con logos de terceros"],
    }
    a, b = cols(2)
    with a:
        html('<div class="status">Documentación base obligatoria</div>')
        ok_base = [st.checkbox(x, key=f"base_{i}") for i, x in enumerate(base)]
    with b:
        html(f'<div class="status">Requisitos específicos · {tipo}</div>')
        ok_esp = [st.checkbox(x, key=f"esp_{tipo}_{i}") for i, x in enumerate(especificos[tipo])]
    html('<div class="status" style="margin-top:14px">Ley del Consumidor (19.496 y 21.398) para vender en Chile</div>')
    consumidor = ["Garantía legal de 6 meses: cambio, reparación o devolución del dinero a elección del cliente (Ley 21.398)", "Derecho a retracto de 10 días en compras por internet o a distancia, si no se informó lo contrario", "Precio exhibido con IVA incluido y visible antes de comprar; si hay descuento, precio anterior real", "Términos y condiciones, política de cambios y datos del vendedor (razón social, RUT, contacto) visibles en la tienda", "Información en español: características, origen, advertencias y modo de uso", "Boleta o factura electrónica por cada venta (SII) y registro de reclamos con respuesta en plazo razonable"]
    ok_cons = [st.checkbox(x, key=f"cons_{i}") for i, x in enumerate(consumidor)]
    tot, done = len(ok_base) + len(ok_esp) + len(ok_cons), sum(ok_base) + sum(ok_esp) + sum(ok_cons)
    st.progress(done / tot, text=f"Cumplimiento documental {done} de {tot}")
    if done == tot:
        sem("verde", "Listo para embarcar", "Toda la documentación está marcada como lista.")
    st.caption("Referencia general. Confirma vigencia con Aduanas, SEC, SUBTEL o SEREMI según corresponda.")

# =============================================================================
# PÁGINA: Ventas y dossier
# =============================================================================
elif page == "Ventas y dossier":
    title("Ventas y dossier", "Registra ventas, controla la plata retenida y exporta el informe ejecutivo.", ayuda="""**Qué hace:** registra cada venta para actualizar stock, caja y el IVA que debes declarar.\n\n**Cómo se usa:** elige producto, cantidad, canal y medio de pago. Los días de liberación son clave: Mercado Pago puede tardar 14 días en depositarte y esa plata todavía no es caja disponible.""")
    inv_list = db.list_inventario()
    if not inv_list:
        html('<div class="card"><h4>Sin inventario</h4><p>Registra un embarque para habilitar el registro de ventas.</p></div>')
    else:
        with st.form("form_venta", clear_on_submit=True):
            html('<div class="status">Registrar venta</div>')
            a, b, c = cols(3)
            prod_lbl = [f"#{i['id']} {i['producto']} (stock {i['unidades_disponibles']})" for i in inv_list]
            sel = a.selectbox("Producto", prod_lbl)
            cant = int(a.number_input("Cantidad", 1, 100000, 1))
            fecha_v = a.date_input("Fecha", date.today())
            canal = b.selectbox("Canal", ["ML", "Web", "B2B"])
            precio_v = b.number_input("Precio unitario (CLP c/IVA)", 100.0, 100_000_000.0, 24990.0, 500.0)
            medio = c.selectbox("Medio de pago", ["Mercado Pago", "Transbank / Webpay", "Transferencia", "Efectivo"])
            ret_v = int(c.number_input("Días hasta liberación del pago", 0, 30, 14, help="Mercado Pago 14 · Transbank 2 · transferencia 0"))
            com_v = c.number_input("Comisión total cobrada (CLP)", 0.0, 100_000_000.0, 0.0, 100.0, help="Déjalo en 0 para calcularla automáticamente por canal.")
            documento = b.selectbox("Documento tributario", ["Boleta", "Factura"], help="Factura si el cliente es empresa (B2B). Ambas generan débito fiscal.")
            folio = b.text_input("Folio del documento (opcional)")
            if st.form_submit_button("Registrar venta", type="primary"):
                it = inv_list[prod_lbl.index(sel)]
                if com_v == 0:
                    com_v = round(precio_v * cant * {"ML": 0.15, "Web": 0.029 * 1.19, "B2B": 0.0}[canal])
                try:
                    ids = db.registrar_venta(db.Venta(producto_id=it["id"], cantidad=cant, canal=canal, precio_unitario=precio_v, medio_pago=medio, comision=com_v, fecha=fecha_v.isoformat(), documento=documento, folio=folio.strip()), ret_v)
                    st.toast(f"Venta #{ids['venta_id']} registrada: stock y F29 actualizados", icon="✅")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    ventas = db.list_ventas()
    st.markdown("### Historial de ventas")
    if ventas:
        a, b, c = cols(3)
        a.metric("Ventas brutas", clp(sum(v["total_bruto"] for v in ventas)))
        b.metric("Neto tras comisiones", clp(sum(v["total_neto"] for v in ventas)))
        utilidad = sum(v["total_neto"] - (v["total_bruto"] - v["total_bruto"] / 1.19) - v["cantidad"] * v["costo_unitario_clp"] for v in ventas)
        c.metric("Utilidad bruta", clp(utilidad), "neto − IVA − costo en bodega")
        dfv = pd.DataFrame(ventas)[["id", "fecha", "documento", "folio", "producto", "cantidad", "canal", "precio_unitario", "comision", "total_neto", "medio_pago", "estado_liquidacion", "fecha_liberacion"]]
        dfv.columns = ["#", "Fecha", "Doc.", "Folio", "Producto", "Cant.", "Canal", "Precio u.", "Comisión", "Neto", "Medio de pago", "Estado", "Libera el"]
        st.dataframe(dfv, width="stretch", hide_index=True)
        pend = [v for v in ventas if v["estado_liquidacion"] == "Retenido"]
        if pend:
            with st.expander(f"Marcar como liberada ({len(pend)} retenidas)"):
                lbl = [f"#{v['id']} {v['producto']} {clp(v['total_neto'])}" for v in pend]
                sv = st.selectbox("Venta retenida", lbl, help="Ventas cuyo dinero aún no llega a tu cuenta. Márcalas en cuenta cuando la pasarela te deposite.")
                if st.button("Marcar en cuenta"):
                    db.update_venta_estado(pend[lbl.index(sv)]["id"], "En Cuenta")
                    st.rerun()
    else:
        html('<div class="card"><h4>Aún no hay ventas</h4><p>Registra la primera arriba. La caja retenida, el stock y el F29 se actualizan solos.</p></div>')

    st.markdown("### Libro F29")
    f29_rows = db.list_f29()
    if f29_rows:
        dff = pd.DataFrame(f29_rows)[["fecha", "tipo", "monto_clp", "descripcion", "referencia"]]
        dff.columns = ["Fecha", "Tipo", "Monto CLP", "Descripción", "Referencia"]
        st.dataframe(dff, width="stretch", hide_index=True)
    else:
        st.caption("Sin movimientos todavía.")

    st.markdown("### Dossier ejecutivo en PDF")
    lote = st.session_state.get("lote")
    if lote is None:
        cots = db.list_cotizaciones()
        if cots:
            st.caption("Usa la última cotización guardada. Para un dossier con pricing y proyección, calcula primero en Costeo y Precios.")
            c = cots[0]
            liq_pdf = {**c, "pasos": [{"paso": "FOB total", "usd": c["fob_total_usd"], "clp": c["fob_total_usd"] * c["tipo_cambio"]}, {"paso": "Flete", "usd": c["flete_usd"], "clp": c["flete_usd"] * c["tipo_cambio"]}, {"paso": "Seguro", "usd": c["seguro_usd"], "clp": c["seguro_usd"] * c["tipo_cambio"]}, {"paso": "= CIF", "usd": c["cif_usd"], "clp": c["cif_clp"]}, {"paso": "Ad-valorem", "usd": c["advalorem_usd"], "clp": c["advalorem_usd"] * c["tipo_cambio"]}, {"paso": "IVA 19%", "usd": c["iva_usd"], "clp": c["iva_usd"] * c["tipo_cambio"]}, {"paso": "Honorarios agente", "usd": c["honorarios_usd"], "clp": c["honorarios_usd"] * c["tipo_cambio"]}, {"paso": "Gastos locales", "usd": c["gastos_locales_clp"] / c["tipo_cambio"], "clp": c["gastos_locales_clp"]}, {"paso": "= LANDED COST (sin IVA)", "usd": c["landed_usd"], "clp": c["landed_clp"]}, {"paso": "= Desembolso total", "usd": c["desembolso_total_clp"] / c["tipo_cambio"], "clp": c["desembolso_total_clp"]}], "iva_clp": c["iva_usd"] * c["tipo_cambio"], "agente_obligatorio": c["honorarios_usd"] > 0, "agente_detalle": "", "seguro_es_presunto": False}
            lineas_pdf = db.list_items(c["id"])
            cub_pdf = None
        else:
            liq_pdf, lineas_pdf, cub_pdf = None, None, None
    else:
        liq_pdf, lineas_pdf, cub_pdf = lote.total.to_dict(), [l.to_dict() for l in lote.lineas], lote.cubicaje.to_dict()
    if liq_pdf is None:
        st.caption("Calcula un embarque en Costeo e internación para habilitar el dossier.")
    else:
        mix_pdf, tgt_pdf = st.session_state.get("mix"), st.session_state.get("target")
        mix_dict = None
        if mix_pdf:
            mix_dict = {"canales": [c.to_dict() for c in mix_pdf.canales], "precio_ponderado": mix_pdf.precio_ponderado, "margen_ponderado": mix_pdf.margen_ponderado, "margen_pct_ponderado": mix_pdf.margen_pct_ponderado, "cobro_neto_ponderado": mix_pdf.cobro_neto_ponderado}
            if tgt_pdf:
                mix_dict["target"] = {k: v for k, v in asdict(tgt_pdf).items() if k != "detalle_canales"}
        f29_tot = db.resumen_f29()
        f29_pdf = resumen_f29(f29_tot["credito"], f29_tot["debito"], db.ventas_netas_periodo(date.today().strftime("%Y-%m"))).to_dict()
        flujo_pdf = dict(st.session_state.get("flujo", {}))
        flujo_pdf["cash_to_cash"] = st.session_state.get("c2c_msg", "")
        pdf_bytes = generar_dossier(liq_pdf, cub_pdf, mix_dict, f29_pdf, flujo_pdf, st.session_state.get("viab"), lineas_pdf)
        st.download_button("Descargar dossier ejecutivo (PDF)", pdf_bytes, file_name=f"dossier_importo_{date.today()}.pdf", mime="application/pdf", type="primary")

# =============================================================================
# PÁGINA: Mi cuenta
# =============================================================================
elif page == "Mi cuenta":
    title("Mi cuenta", usuario.email)
    res = db.resumen_usuario(usuario.id)
    a, b, c = cols(3)
    a.metric("Productos en catálogo", res["productos"])
    b.metric("Embarques cotizados", res["cotizaciones"])
    c.metric("Ventas registradas", res["ventas"])
    g1, g2 = cols(2)
    with g1:
        html('<div class="status">Perfil</div>')
        with st.form("perfil"):
            nombre_n = st.text_input("Nombre", usuario.nombre, help="Cómo te saluda la app. No afecta tu correo ni tu acceso.")
            if st.form_submit_button("Guardar nombre", type="primary"):
                db.actualizar_perfil(usuario.id, nombre_n.strip() or usuario.nombre)
                st.session_state["auth_user"] = auth.Usuario(usuario.id, usuario.email, nombre_n.strip() or usuario.nombre, usuario.rol)
                st.success("Perfil actualizado")
                st.rerun()
    with g2:
        html('<div class="status">Cambiar contraseña</div>')
        with st.form("clave"):
            actual = st.text_input("Contraseña actual", type="password", help="Por seguridad, confirma que eres tú antes de cambiarla.")
            nueva = st.text_input("Nueva contraseña", type="password", help="Mínimo 8 caracteres con letras y números.")
            nueva2 = st.text_input("Repite la nueva", type="password", help="Debe coincidir con la nueva contraseña.")
            if st.form_submit_button("Actualizar contraseña", type="primary"):
                if nueva != nueva2:
                    st.error("Las contraseñas nuevas no coinciden.")
                else:
                    ok, msg = auth.cambiar_password(usuario.id, actual, nueva)
                    (st.success if ok else st.error)(msg)
    html('<div class="card"><h4>Seguridad de tu cuenta</h4><p>Contraseña cifrada con PBKDF2-SHA256 (600.000 iteraciones) y sal única. Bloqueo de 15 minutos tras 5 intentos fallidos. Sesión expira a las 8 horas sin uso. Tus productos, embarques, ventas y libro F29 solo son visibles con tu correo.</p></div>')
    if usuario.rol == "admin":
        st.markdown("### Administración de usuarios")
        us = db.listar_usuarios()
        dfu = pd.DataFrame(us)[["id", "email", "nombre", "rol", "activo", "creado", "ultimo_login"]]
        dfu["activo"] = dfu["activo"].astype(bool)
        st.dataframe(dfu, width="stretch", hide_index=True)
        a, b = cols(2)
        objetivo = a.selectbox("Usuario", [f"#{u['id']} {u['email']}" for u in us if u["id"] != usuario.id] or ["—"])
        if objetivo != "—":
            uid_obj = int(objetivo.split()[0][1:])
            activo_obj = next(u["activo"] for u in us if u["id"] == uid_obj)
            if b.button("Desactivar cuenta" if activo_obj else "Reactivar cuenta"):
                db.set_usuario_activo(uid_obj, not activo_obj)
                db.auditar("admin_cuenta", f"usuario #{uid_obj} {'desactivado' if activo_obj else 'reactivado'}")
                st.rerun()

# =============================================================================
# PÁGINA: Privacidad y mis datos (derechos del titular)
# =============================================================================
elif page == "Privacidad y mis datos":
    title("Privacidad y mis datos", "Tus derechos según la Ley 19.628 / 21.719, ejercibles aquí mismo y sin intermediarios.", ayuda="""**Qué hace:** aquí ejerces tus derechos sobre tus datos personales según la Ley 19.628 / 21.719.\n\n**Cómo se usa:** descarga todo lo que la app guarda de ti, cambia tu consentimiento de comunicaciones, pide bloqueo u oposición, o elimina tu cuenta por completo.""")
    r = privacy.datos_responsable()
    html(f'<div class="card"><h4>Responsable del tratamiento</h4><p><b>{E(r["resp_nombre"])}</b> · RUT {E(r["resp_rut"])} · {E(r["resp_direccion"])}<br>Contacto para ejercer derechos: <b>{E(r["resp_email"])}</b>' + (f'<br>Delegado de protección de datos: {E(r["resp_dpo"])}' if r.get("resp_dpo") else "") + '</p></div>')

    g1, g2 = cols(2)
    with g1:
        html('<div class="status">Acceso y portabilidad</div>')
        st.caption("Descarga todo lo que la app guarda sobre ti en formato abierto (JSON).")
        datos = privacy.exportar_json(usuario.id)
        if st.download_button("Descargar mis datos (JSON)", datos, file_name=f"mis_datos_importo_{date.today()}.json", mime="application/json", type="primary"):
            db.auditar("exportacion", "el titular descargó sus datos (portabilidad)")
        html('<div class="status" style="margin-top:18px">Rectificación</div>')
        st.caption("Corrige tu nombre y contraseña en **Mi cuenta**; tus datos comerciales se editan en cada sección.")
        html('<div class="status" style="margin-top:18px">Oposición a comunicaciones</div>')
        com = db.ultimo_consentimiento(usuario.id, "comunicaciones")
        actual = bool(com and com["aceptado"])
        nuevo = st.toggle("Acepto recibir avisos y novedades por correo", value=actual)
        if nuevo != actual:
            db.registrar_consentimiento(usuario.id, "comunicaciones", privacy.VERSION_POLITICA, nuevo, "Cambiado por el titular")
            db.auditar("consentimiento", f"comunicaciones: {'aceptadas' if nuevo else 'rechazadas'}")
            st.rerun()
    with g2:
        html('<div class="status">Bloqueo, oposición u otra solicitud</div>')
        st.caption(f"El responsable debe responder dentro de {privacy.PLAZO_RESPUESTA_DIAS} días. Verás el estado aquí.")
        with st.form("solicitud"):
            derecho = st.selectbox("Derecho", ["Bloqueo", "Oposición", "Rectificación", "Acceso", "Otra consulta"], help="Qué quieres pedir sobre tus datos personales. En el Glosario y en la política se explica cada uno.")
            det = st.text_area("Describe tu solicitud", height=90, help="Cuenta qué necesitas. El responsable debe responderte dentro del plazo legal.")
            if st.form_submit_button("Enviar solicitud", type="primary"):
                sid = db.crear_solicitud(usuario.id, derecho, det, privacy.PLAZO_RESPUESTA_DIAS)
                db.auditar("solicitud_derecho", f"#{sid} {derecho}")
                st.success(f"Solicitud #{sid} registrada.")
                st.rerun()
        mis = db.solicitudes(usuario.id)
        if mis:
            dfs = pd.DataFrame(mis)[["id", "derecho", "fecha", "plazo", "estado", "respuesta"]]
            dfs.columns = ["#", "Derecho", "Enviada", "Plazo", "Estado", "Respuesta"]
            st.dataframe(dfs, width="stretch", hide_index=True)

    html('<div class="status" style="margin-top:8px">Supresión de la cuenta</div>')
    st.caption("Elimina de forma definitiva tu cuenta y todos tus datos (productos, embarques, ventas, libro F29, consentimientos). En la bitácora de seguridad queda solo un identificador irreversible. Si necesitas conservar registros contables, descarga primero tus datos.")
    with st.expander("Eliminar mi cuenta y mis datos"):
        conf = st.text_input("Escribe tu correo para confirmar", help="Medida de seguridad: la eliminación es definitiva y no se puede deshacer.")
        pw_conf = st.text_input("Tu contraseña", type="password", key="pw_supresion", help="Confirma tu identidad antes de eliminar la cuenta.")
        if st.button("Eliminar definitivamente", type="primary"):
            u_db = db.get_usuario(usuario.id)
            if conf.strip().lower() != usuario.email or not auth.verificar_password(pw_conf, u_db["password_hash"], u_db["salt"]):
                st.error("El correo o la contraseña no coinciden.")
            elif usuario.rol == "admin" and sum(1 for x in db.listar_usuarios() if x["rol"] == "admin") == 1:
                st.error("Eres el único administrador. Nombra otro antes de eliminar tu cuenta.")
            else:
                db.eliminar_cuenta(usuario.id, privacy.hash_email(usuario.email))
                auth.cerrar_sesion()
                st.success("Cuenta y datos eliminados.")
                st.rerun()

    with st.expander("Mis consentimientos y mi historial de accesos"):
        cons = db.consentimientos_usuario(usuario.id)
        if cons:
            dfc = pd.DataFrame(cons)[["fecha", "tipo", "version", "aceptado", "detalle"]]
            dfc["aceptado"] = dfc["aceptado"].astype(bool)
            st.dataframe(dfc, width="stretch", hide_index=True)
        aud = db.auditoria_usuario(usuario.id)
        if aud:
            st.dataframe(pd.DataFrame(aud)[["fecha", "accion", "detalle"]], width="stretch", hide_index=True)
    with st.expander("Política de Privacidad vigente"):
        st.markdown(privacy.politica_privacidad())

# =============================================================================
# PÁGINA: Cumplimiento (solo administrador)
# =============================================================================
elif page == "Cumplimiento (admin)":
    if usuario.rol != "admin":
        st.error("Esta sección es solo para el administrador de la cuenta.")
        st.stop()
    title("Cumplimiento · Ley 19.628 / 21.719", "Evidencia operativa: consentimientos, solicitudes, brechas, registro de actividades y bitácora.", ayuda="""**Qué hace:** reúne la evidencia que debes poder mostrar si la Agencia te fiscaliza.\n\n**Cómo se usa:** completa los datos del responsable (aparecen en la política y el RAT), responde las solicitudes dentro del plazo, registra cualquier brecha dentro de 72 horas y revisa el checklist organizacional.""")
    est = db.estadisticas_tratamiento()
    a, b, c, d = cols(4)
    a.metric("Titulares (cuentas)", est["usuarios"])
    b.metric("Consentimientos vigentes", est["consentimientos"])
    c.metric("Solicitudes pendientes", est["solicitudes_pendientes"])
    d.metric("Brechas abiertas", est["incidentes_abiertos"])

    st.markdown("### Responsable del tratamiento")
    st.caption("Estos datos aparecen en la Política de Privacidad, en el RAT y en las notificaciones a la Agencia.")
    r = privacy.datos_responsable()
    with st.form("responsable"):
        vals = {}
        c1, c2 = cols(2)
        for i, (k, (lbl, _)) in enumerate(privacy.CAMPOS_RESPONSABLE.items()):
            vals[k] = (c1 if i % 2 == 0 else c2).text_input(lbl, r[k])
        if st.form_submit_button("Guardar", type="primary"):
            for k, v in vals.items():
                db.set_config(k, v, global_=True)
            db.auditar("config_responsable", "datos del responsable actualizados")
            st.success("Guardado")
            st.rerun()

    st.markdown("### Solicitudes de derechos")
    sols = db.solicitudes()
    if sols:
        for sdt in sols:
            venc = (date.fromisoformat(sdt["plazo"]) - date.today()).days
            color = "verde" if sdt["estado"] != "Pendiente" else ("rojo" if venc < 0 else "ambar" if venc <= 7 else "verde")
            estado_txt = sdt["estado"] if sdt["estado"] != "Pendiente" else (f"vencida hace {abs(venc)} días" if venc < 0 else f"vence en {venc} días")
            a, b = st.columns([3, 1]) if not celular else (st.container(), st.container())
            with a:
                html(f'<div class="card"><div class="status"><span class="dot" style="background:var(--{SEM[color]})"></span>#{sdt["id"]} {E(sdt["derecho"])} · {E(sdt["email"])} · {estado_txt}</div><p>{E(sdt["detalle"]) or "(sin detalle)"}' + (f'<br><b>Respuesta:</b> {E(sdt["respuesta"])}' if sdt.get("respuesta") else "") + "</p></div>")
            if sdt["estado"] == "Pendiente":
                with b:
                    resp = st.text_input("Respuesta", key=f"resp_{sdt['id']}", help="Qué le responderás al titular. Queda registrado como evidencia de cumplimiento.")
                    est_n = st.selectbox("Resolver", ["Atendida", "Rechazada"], key=f"est_{sdt['id']}", help="Atendida si accediste a lo pedido; Rechazada si legalmente no corresponde (explica el motivo).")
                    if st.button("Cerrar solicitud", key=f"cerrar_{sdt['id']}"):
                        db.responder_solicitud(sdt["id"], est_n, resp)
                        if sdt["derecho"] == "Bloqueo" and est_n == "Atendida":
                            db.set_usuario_activo(sdt["usuario_id"], False)
                        db.auditar("respuesta_solicitud", f"#{sdt['id']} {est_n}")
                        st.rerun()
    else:
        st.caption("Sin solicitudes.")

    st.markdown("### Brechas de seguridad (notificación a la Agencia en 72 h)")
    with st.expander("Registrar una vulneración"):
        with st.form("incidente"):
            fdet = st.text_input("Fecha y hora de detección (AAAA-MM-DD HH:MM)", datetime.now().strftime("%Y-%m-%d %H:%M"), help="Momento en que te enteraste de la brecha. Desde aquí corren las 72 horas para notificar a la Agencia.")
            desc = st.text_area("Qué ocurrió", height=80)
            datos_af = st.text_input("Datos afectados (categorías)", help="Qué tipo de datos se vieron comprometidos: correos, nombres, contraseñas, datos comerciales.")
            n_af = int(st.number_input("Titulares afectados (aprox.)", 0, 1_000_000, 0, help="Cuántas personas se vieron afectadas. Si no lo sabes aún, pon tu mejor estimación y actualízala."))
            riesgo = st.selectbox("Riesgo para los titulares", ["Bajo", "Medio", "Alto"], help="Alto si pueden sufrir fraude, suplantación o perjuicio económico: en ese caso hay que avisarles a ellos también.")
            medidas = st.text_area("Medidas adoptadas", height=60, help="Qué hiciste para contener la brecha y evitar que se repita.")
            if st.form_submit_button("Registrar", type="primary"):
                try:
                    fdt = datetime.strptime(fdet.strip(), "%Y-%m-%d %H:%M").isoformat(timespec="minutes")
                    iid = db.crear_incidente({"fecha_deteccion": fdt, "descripcion": desc, "datos_afectados": datos_af, "usuarios_afectados": n_af, "riesgo": riesgo, "medidas": medidas, "creado_por": usuario.id})
                    db.auditar("incidente", f"#{iid} registrado, riesgo {riesgo}")
                    st.rerun()
                except ValueError:
                    st.error("Formato de fecha inválido.")
    for inc in db.listar_incidentes():
        eb = privacy.estado_brecha(inc)
        color = "verde" if inc["estado"] != "Abierto" else eb["color"]
        html(f'<div class="card"><div class="status"><span class="dot" style="background:var(--{SEM[color]})"></span>#{inc["id"]} · {E(inc["estado"])} · riesgo {E(inc["riesgo"])} · detectada {E(inc["fecha_deteccion"])}</div><p>{E(inc["descripcion"])}<br>{E(eb["mensaje"])}</p></div>')
        if inc["estado"] == "Abierto":
            a, b, c, d = cols(4)
            if not inc["notificado_agencia"] and a.button("Marcar notificada a la Agencia", key=f"ag_{inc['id']}"):
                db.actualizar_incidente(inc["id"], {"notificado_agencia": 1, "fecha_notificacion_agencia": datetime.now().isoformat(timespec="minutes")})
                db.auditar("incidente", f"#{inc['id']} notificado a la Agencia")
                st.rerun()
            if not inc["notificado_titulares"] and b.button("Marcar titulares notificados", key=f"ti_{inc['id']}"):
                db.actualizar_incidente(inc["id"], {"notificado_titulares": 1, "fecha_notificacion_titulares": datetime.now().isoformat(timespec="minutes")})
                db.auditar("incidente", f"#{inc['id']} titulares notificados")
                st.rerun()
            c.download_button("Plantilla de notificación", privacy.plantilla_notificacion_agencia(inc), file_name=f"notificacion_apdp_{inc['id']}.txt", key=f"pl_{inc['id']}")
            if d.button("Cerrar incidente", key=f"cl_{inc['id']}"):
                db.actualizar_incidente(inc["id"], {"estado": "Cerrado"})
                db.auditar("incidente", f"#{inc['id']} cerrado")
                st.rerun()

    st.markdown("### Registro de actividades de tratamiento (RAT)")
    st.dataframe(pd.DataFrame(privacy.registro_actividades(r)), width="stretch", hide_index=True)
    st.download_button("Descargar RAT (Markdown)", privacy.rat_markdown(), file_name=f"RAT_importo_{date.today()}.md")

    st.markdown("### Retención: cuentas inactivas")
    meses = int(float(r["resp_retencion_meses"] or 24))
    inact = db.cuentas_inactivas(meses)
    if inact:
        st.dataframe(pd.DataFrame(inact), width="stretch", hide_index=True)
        st.caption("Antes de eliminar, avisa al correo registrado. La eliminación borra todos los datos de la cuenta.")
        objetivo = st.selectbox("Cuenta a eliminar", [f"#{u['id']} {u['email']}" for u in inact], help="Cuentas sin actividad según el plazo de retención que declaraste. Avisa al correo antes de eliminar.")
        if st.button("Eliminar cuenta inactiva"):
            uid_obj = int(objetivo.split()[0][1:])
            em = next(u["email"] for u in inact if u["id"] == uid_obj)
            db.eliminar_cuenta(uid_obj, privacy.hash_email(em))
            db.auditar("retencion", f"cuenta inactiva eliminada {privacy.hash_email(em)}")
            st.rerun()
    else:
        st.caption(f"No hay cuentas con más de {meses} meses sin actividad.")

    st.markdown("### Lista de verificación organizacional")
    st.caption("Lo que la ley exige y no se resuelve con software. Márcalo cuando esté hecho; se guarda por administrador.")
    hechos = 0
    for i, (item, tipo) in enumerate(privacy.CHECKLIST_ORGANIZACIONAL):
        clave = f"chk_{i}"
        auto = tipo == "config" and all(r[k] and r[k] != v[1] for k, v in privacy.CAMPOS_RESPONSABLE.items() if k in ("resp_nombre", "resp_rut", "resp_direccion", "resp_email"))
        val = st.checkbox(item, value=auto or db.get_config(clave, "0") == "1", key=clave, disabled=tipo == "config")
        if tipo != "config" and (val != (db.get_config(clave, "0") == "1")):
            db.set_config(clave, "1" if val else "0")
        hechos += int(val)
    st.progress(hechos / len(privacy.CHECKLIST_ORGANIZACIONAL), text=f"{hechos} de {len(privacy.CHECKLIST_ORGANIZACIONAL)} obligaciones cubiertas")

    with st.expander("Bitácora global de auditoría"):
        aud = db.auditoria_global()
        if aud:
            dfa = pd.DataFrame(aud)[["fecha", "email", "accion", "detalle"]]
            st.dataframe(dfa, width="stretch", hide_index=True)
            st.download_button("Descargar bitácora (CSV)", dfa.to_csv(index=False).encode("utf-8"), file_name=f"auditoria_{date.today()}.csv")

# =============================================================================
# PÁGINA: Gastos y F29
# =============================================================================
elif page == "Gastos y F29":
    title("Gastos y F29", "Compras y gastos con crédito fiscal, costos fijos para el punto de equilibrio y el F29 mensual listo para tu contador.", ayuda="""**Qué hace:** reúne tus gastos y arma el F29 mensual con débito, crédito, remanente y PPM.\n\n**Cómo se usa:** registra todo gasto con factura (recuperas el 19 %) y marca como fijo lo que pagas todos los meses. Luego elige el período y descarga los libros para tu contador.\n\n**Ojo:** solo la factura da crédito fiscal; la boleta de compra, no.""")
    CATS_G = ["Publicidad", "Arriendo", "Sueldos y honorarios", "Software y suscripciones", "Envíos y logística", "Contabilidad y legal", "Insumos y empaque", "Servicios básicos", "Otros"]
    with st.form("form_gasto", clear_on_submit=True):
        html('<div class="status">Registrar gasto o compra</div>')
        a, b, c = cols(3)
        fecha_g = a.date_input("Fecha", date.today())
        cat_g = a.selectbox("Categoría", CATS_G)
        desc_g = a.text_input("Descripción")
        prov_g = b.text_input("Proveedor")
        doc_g = b.selectbox("Documento", ["Factura", "Boleta", "Sin documento"], help="Solo la factura da derecho a crédito fiscal de IVA.")
        folio_g = b.text_input("Folio")
        total_g = c.number_input("Total pagado (CLP, con IVA si aplica)", 0.0, 1_000_000_000.0, 0.0, 1000.0)
        con_iva = c.checkbox("Incluye IVA 19 %", True)
        rec_g = c.checkbox("Es un costo fijo mensual (recurrente)", False, help="Arriendo, sueldos, software: se usa para el punto de equilibrio.")
        if st.form_submit_button("Registrar gasto", type="primary"):
            if total_g <= 0:
                st.error("Ingresa el total.")
            else:
                neto_g = round(total_g / 1.19) if con_iva else round(total_g)
                iva_g = round(total_g) - neto_g if con_iva else 0.0
                ids = db.registrar_gasto(db.Gasto(fecha_g.isoformat(), cat_g, neto_g, iva_g, round(total_g), desc_g, prov_g, doc_g, folio_g.strip(), int(rec_g)))
                db.auditar("gasto", f"#{ids['gasto_id']} {cat_g} {clp(total_g)}")
                st.toast(f"Gasto registrado. IVA {clp(iva_g)}" + (" → crédito fiscal" if doc_g == "Factura" and iva_g else ""), icon="✅")
                st.rerun()

    gastos = db.list_gastos()
    if gastos:
        dfg = pd.DataFrame(gastos)[["id", "fecha", "categoria", "descripcion", "proveedor", "documento", "folio", "neto", "iva", "total", "recurrente"]]
        dfg["recurrente"] = dfg["recurrente"].astype(bool)
        dfg.columns = ["#", "Fecha", "Categoría", "Descripción", "Proveedor", "Doc.", "Folio", "Neto", "IVA", "Total", "Fijo mensual"]
        st.dataframe(dfg, width="stretch", hide_index=True)
        a, b, c = cols(3)
        a.metric("Costos fijos mensuales (neto)", clp(db.costos_fijos_mensuales()))
        b.metric("Gastos del mes", clp(sum(g["total"] for g in gastos if g["fecha"][:7] == date.today().strftime("%Y-%m"))))
        c.metric("Crédito fiscal por compras (histórico)", clp(sum(g["iva"] for g in gastos if g["documento"] == "Factura")))
        with st.expander("Eliminar un gasto"):
            gl = st.selectbox("Gasto", [f"#{g['id']} {g['fecha']} {g['categoria']} {clp(g['total'])}" for g in gastos], help="Elige el gasto que quieres borrar. También se elimina su crédito fiscal asociado.")
            if st.button("Eliminar gasto"):
                gid = int(gl.split()[0][1:])
                db.eliminar_gasto(gid)
                db.auditar("gasto", f"eliminado #{gid}")
                st.rerun()
    else:
        html('<div class="card"><h4>Sin gastos registrados</h4><p>Registra publicidad, arriendo, software y compras con factura: el IVA de las facturas suma crédito fiscal y los costos fijos alimentan tu punto de equilibrio.</p></div>')

    st.markdown("### F29 mensual")
    meses = db.meses_con_movimiento() or [date.today().strftime("%Y-%m")]
    mes_sel = st.selectbox("Período", meses, help="Mes que quieres declarar, en formato año-mes.")
    rm = db.resumen_f29_mensual(mes_sel)
    a, b = cols(2)
    regs = list(guide.REGIMENES)
    reg_act = db.get_config("regimen", guide.REGIMEN_DEFAULT)
    regimen = a.selectbox("Régimen tributario", regs, index=regs.index(reg_act) if reg_act in regs else 1, help="Define la tasa de PPM. Puedes cambiar de régimen ante el SII una vez al año, antes del 30 de abril.")
    ppm_def = guide.REGIMENES[regimen]["ppm"] * 100
    if regimen != reg_act:
        db.set_config("regimen", regimen)
        db.set_config("tasa_ppm", ppm_def)
    tasa_ppm = b.number_input("Tasa PPM (%)", 0.0, 10.0, float(db.get_config("tasa_ppm", str(ppm_def))), 0.005, format="%.3f", help="Se ajusta sola al cambiar de régimen. Después del primer F22 el SII te asigna una tasa propia: escríbela aquí.") / 100
    if db.get_config("tasa_ppm", "") != str(tasa_ppm * 100):
        db.set_config("tasa_ppm", tasa_ppm * 100)
    st.caption(guide.REGIMENES[regimen]["resumen"])
    f = f29_mensual(mes_sel, rm["debito"], rm["credito"], rm["remanente_anterior"], rm["ventas_netas"], tasa_ppm)
    sem(f["color"], f"F29 {mes_sel} · vence {date.fromisoformat(f['vencimiento']).strftime('%d-%m-%Y')}", f["mensaje"])
    dfl = pd.DataFrame(f["lineas"])
    dfl["monto"] = dfl["monto"].map(clp)
    dfl.columns = ["Código F29", "Concepto", "Monto"]
    st.dataframe(dfl, width="stretch", hide_index=True)
    st.caption("Los códigos son referenciales para ubicar cada valor en el formulario del SII. El remanente arrastrado debe reajustarse por UTM; tu contador lo aplica.")

    st.markdown("### Libros para el contador")
    lv, lc = db.libro_ventas(mes_sel), db.libro_compras(mes_sel)
    a, b = cols(2)
    with a:
        html(f'<div class="status">Libro de ventas · {len(lv)} documentos</div>')
        if lv:
            st.dataframe(pd.DataFrame(lv), width="stretch", hide_index=True)
            st.download_button("Descargar libro de ventas (CSV)", pd.DataFrame(lv).to_csv(index=False).encode("utf-8-sig"), file_name=f"libro_ventas_{mes_sel}.csv")
    with b:
        html(f'<div class="status">Libro de compras · {len(lc)} documentos</div>')
        if lc:
            st.dataframe(pd.DataFrame(lc), width="stretch", hide_index=True)
            st.download_button("Descargar libro de compras (CSV)", pd.DataFrame(lc).to_csv(index=False).encode("utf-8-sig"), file_name=f"libro_compras_{mes_sel}.csv")

# =============================================================================
# PÁGINA: Salud de tu empresa
# =============================================================================
elif page == "Salud de tu empresa":
    title("Salud de tu empresa", "Seis señales, un puntaje y la acción que más importa hoy.", ayuda="""**Qué hace:** resume en un número cómo va tu negocio en seis frentes y te dice qué atender primero.\n\n**Cómo se leerlo:** verde vale 100, ámbar 50, rojo 0; el puntaje es el promedio. Gris significa que aún faltan datos: registra ventas y gastos para que la foto sea real.""")
    hecho = sum(1 for i in range(len(privacy.CHECKLIST_ORGANIZACIONAL)) if db.get_config(f"chk_{i}", "0") == "1")
    tasa = float(db.get_config("tasa_ppm", str(guide.REGIMENES[guide.REGIMEN_DEFAULT]["ppm"] * 100))) / 100
    sl = salud_empresa(lead_time, tasa, hecho, len(privacy.CHECKLIST_ORGANIZACIONAL))
    a, b = st.columns([1, 2]) if not celular else (st.container(), st.container())
    with a:
        html(f'<div class="card" style="text-align:center"><h4>Puntaje de salud</h4><div class="big num" style="color:var(--{SEM[sl.color]})">{sl.puntaje}</div><div class="hint">de 100</div></div>')
    with b:
        sem(sl.color, "Lo más importante hoy", sl.resumen)
    c1, c2, c3 = cols(3)
    for i, d in enumerate(sl.dimensiones):
        with (c1, c2, c3)[i % 3]:
            html(f'<div class="card"><div class="status"><span class="dot" style="background:var(--{SEM[d.color]})"></span>{E(d.nombre)}</div><p><b>{E(d.valor)}</b><br>{E(d.accion)}</p></div>')
    st.caption("Verde = 100, ámbar = 50, rojo = 0; el puntaje es el promedio. Gris significa que aún no hay datos para medir.")

# =============================================================================
# PÁGINA: Guía del emprendedor
# =============================================================================
elif page == "Guía del emprendedor":
    title("De cero a vender con éxito en e-commerce", "Guía práctica ajustada a la ley chilena, con tu avance guardado.", ayuda="""**Qué hace:** el camino completo desde que no tienes nada hasta vender con éxito, ajustado a la ley chilena.\n\n**Cómo se usa:** marca cada tarea a medida que la completas; tu avance queda guardado. Las otras pestañas te dicen qué empresa crear, qué régimen tributario conviene, con qué medios cobrar y dónde vender.""")
    t1, t2, t3, t4 = st.tabs(["Plan por etapas", "Sociedad y régimen tributario", "Canales de pago", "Dónde vender"])
    with t1:
        total = sum(len(e["tareas"]) for e in guide.ETAPAS)
        hechas = 0
        for e in guide.ETAPAS:
            claves = [f"plan_{e['n']}_{i}" for i in range(len(e["tareas"]))]
            done_e = sum(1 for k in claves if db.get_config(k, "0") == "1")
            hechas += done_e
            with st.expander(f"Etapa {e['n']} · {e['titulo']} · {e['dias']} · {done_e}/{len(claves)}", expanded=done_e < len(claves) and e["n"] <= 1):
                for k, tarea in zip(claves, e["tareas"]):
                    val = st.checkbox(tarea, value=db.get_config(k, "0") == "1", key=k)
                    if val != (db.get_config(k, "0") == "1"):
                        db.set_config(k, "1" if val else "0")
        st.progress(hechas / total, text=f"Avance del plan: {hechas} de {total} tareas")
    with t2:
        st.markdown("#### ¿Qué tipo de sociedad me conviene?")
        sem("verde", "Recomendación: SpA con régimen Pro Pyme", "Una SpA protege tu patrimonio, se crea gratis y en el día, y admite socios después. Con Pro Pyme General pagas 12,5 % de impuesto de empresa hasta 2027 si reinviertes; con Pro Pyme Transparente no pagas impuesto de empresa y tributas tú por lo que ganas, lo que suele ser menos si tus ingresos personales son bajos. Decide con tu contador según cuánto piensas retirar.")
        for so in guide.SOCIEDADES:
            html(f'<div class="card"><div class="status">{so["tipo"]}</div><p><b>Socios:</b> {so["socios"]} · <b>Responsabilidad:</b> {so["responsabilidad"]}<br><b>Cómo se crea:</b> {so["constitucion"]}<br><b>Cuándo elegirla:</b> {so["cuando"]}<br><b>Contras:</b> {so["contras"]}</p></div>'.replace("**", ""))
        st.markdown("#### Regímenes tributarios 2026")
        rows = [{"Régimen": k, "Impuesto de empresa": f"{v['idpc']*100:.1f} %" if v["idpc"] else "No paga (tributan los dueños)", "PPM año 1": f"{v['ppm']*100:.3f} %", "PPM si > 50.000 UF": f"{v['ppm_alto']*100:.2f} %", "Para quién": v["resumen"]} for k, v in guide.REGIMENES.items()]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        html('<div class="card"><h4>Cómo sacar el máximo provecho, dentro de la ley</h4><p>1. <b>Gasta con factura</b>: cada factura a nombre de la empresa recupera el 19 % de IVA y rebaja la utilidad tributable (publicidad, software, bodega, envíos, contador).<br>2. <b>Depreciación instantánea</b> en Pro Pyme: computadores, estanterías o una impresora de etiquetas se descuentan completos el año de compra.<br>3. <b>No retires todo</b>: en Pro Pyme General solo tributas personalmente por lo que retiras; lo reinvertido paga 12,5 % hasta 2027.<br>4. <b>Sueldo empresarial</b>: si trabajas en tu empresa puedes asignarte un sueldo con cotizaciones; es gasto aceptado y construye tu previsión.<br>5. <b>Revisa el régimen cada abril</b>: cuando la utilidad crezca y tu tramo personal suba, General suele ganar a Transparente.<br>6. <b>Crédito fiscal de la DIN el mismo mes</b>: importa a inicio de mes y declara ese IVA en el F29 siguiente para no financiar al fisco más de lo necesario.</p></div>')
        st.caption("Datos verificados en septiembre de 2026 (Ley 21.755). Confirma con tu contador antes de decidir; los tramos y tasas se actualizan cada año.")
    with t3:
        st.markdown("#### Canales de pago recomendados")
        st.dataframe(pd.DataFrame(guide.PAGOS).rename(columns={"canal": "Canal", "tipo": "Tipo", "comision": "Comisión referencial", "liquidacion": "Liquidación", "para": "Para qué sirve"}), width="stretch", hide_index=True)
        sem("verde", "Combinación recomendada para partir", "Webpay Plus + Mercado Pago en tu tienda (cubres tarjetas y cuotas), Mercado Pago dentro de Mercado Libre, y transferencia o Khipu para B2B. Registra en la app los días de liberación de cada uno: eso es lo que define tu caja real.")
        st.caption("Comisiones referenciales a 2026; cada pasarela negocia por rubro y volumen. Verifica en el contrato.")
    with t4:
        st.markdown("#### Dónde promover y vender")
        st.dataframe(pd.DataFrame(guide.PLATAFORMAS).rename(columns={"plataforma": "Plataforma", "tipo": "Tipo", "costo": "Costo referencial", "para": "Cuándo usarla"}), width="stretch", hide_index=True)
        sem("verde", "Secuencia que funciona", "Mes 1: Mercado Libre para validar demanda con tráfico existente. Mes 2–3: tienda propia (Jumpseller o Shopify) + Instagram y WhatsApp para construir marca y margen sin comisión. Mes 4+: marketplaces de retail y B2B para volumen. Mide el margen limpio por canal en Precios y mueve el mix hacia el que más deja.")

# =============================================================================
# PÁGINA: Glosario
# =============================================================================
elif page == "Glosario":
    title("Glosario", "Los términos de importación, tributarios y de e-commerce que usa la app, explicados en simple.", ayuda="""**Qué hace:** explica en palabras simples cada término que verás en la app, en tu DIN o en el SII.\n\n**Cómo se usa:** escribe una palabra y filtra. Si algo en otra sección no se entiende, búscalo aquí.""")
    q = st.text_input("Buscar término", "", help="Escribe una palabra y la app filtra el glosario.")
    items = [(k, v) for k, v in sorted(guide.GLOSARIO.items()) if not q or q.lower() in k.lower() or q.lower() in v.lower()]
    if not items:
        st.caption("Sin resultados.")
    c1, c2 = cols(2)
    for i, (k, v) in enumerate(items):
        with (c1, c2)[i % 2]:
            html(f'<div class="card" style="padding:14px 18px;margin-bottom:10px"><div class="status" style="font-size:14px">{k}</div><p>{v}</p></div>')

# =============================================================================
# PÁGINA: Mi recorrido
# =============================================================================
elif page == "Mi recorrido":
    niv, niv_txt = journey.nivel(_ruta["hechos"])
    r = journey.racha()
    title("Mi recorrido", "Cada logro se desbloquea cuando lo cumples de verdad en la app, no al marcar una casilla.",
          ayuda="""**Qué hace:** te muestra en qué punto del camino estás, de novato a experto, y cuál es el siguiente paso concreto.\n\n**Cómo funciona:** los logros se verifican contra tus datos reales (productos, fletes, embarques, ventas, F29). Los módulos nunca se bloquean: puedes saltarte pasos si ya sabes importar.""")
    mision_banner()

    a, b, c = cols(3)
    with a:
        grados = int(_ruta["pct"] * 360)
        html(f'<div class="card" style="text-align:center"><h4>Tu nivel</h4>'
             f'<div style="width:96px;height:96px;margin:6px auto 10px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--green) 0 {grados}deg,var(--line) {grados}deg 360deg)">'
             f'<div style="width:76px;height:76px;border-radius:50%;background:var(--card);display:grid;place-items:center"><span class="num" style="font-size:22px;font-weight:600;color:var(--ink)">{_ruta["pct"]*100:.0f}%</span></div></div>'
             f'<div style="font-weight:800;font-size:16px">{niv}</div><div class="hint">{_ruta["hechos"]} de {_ruta["total"]} logros</div></div>')
    with b:
        chispas = "".join('<i style="flex:1;height:8px;border-radius:99px;background:var(--amber)"></i>' if d else '<i style="flex:1;height:8px;border-radius:99px;background:var(--line)"></i>' for d in r["ultimos7"])
        html(f'<div class="card"><h4>Racha</h4><div class="mid num">{r["dias"]} {"día" if r["dias"] == 1 else "días"}</div>'
             f'<div style="display:flex;gap:5px;margin-top:12px">{chispas}</div>'
             f'<p style="margin-top:10px">{E(r["mensaje"])}</p></div>')
    with c:
        falta = _ruta["total"] - _ruta["hechos"]
        html(f'<div class="card"><h4>Lo que falta</h4><div class="mid num">{falta}</div>'
             f'<p style="margin-top:10px">{niv_txt}</p></div>')

    st.markdown("### Tus módulos")
    mundos = []
    for m in _mods:
        if not m["total"]:
            continue
        estado = "done" if m["completo"] else ("now" if m["clave"] == _mod_actual else "")
        color = "var(--green)" if m["completo"] else ("var(--blue)" if m["clave"] == _mod_actual else "var(--line)")
        etq = "completo" if m["completo"] else ("estás aquí" if m["clave"] == _mod_actual else f'{m["hechos"]} de {m["total"]}')
        mundos.append(f'<div class="mundo {estado}"><div class="em">{m["emoji"]}</div><b>{m["nombre"]}</b><small>{etq}</small>'
                      f'<div class="bar"><i style="width:{m["pct"]*100:.0f}%;background:{color}"></i></div></div>')
    html(f'<div class="mapa">{"".join(mundos)}</div>')

    g1, g2 = st.columns([1.55, 1]) if not celular else (st.container(), st.container())
    with g1:
        st.markdown("### El camino")
        nodos, y = [], 44
        paso = 86
        mods_con_hitos = [m for m in _mods if m["total"]]
        for i, m in enumerate(mods_con_hitos):
            lado = 62 if i % 2 == 0 else 150
            if m["completo"]:
                fill, stroke, txt, marca = "#10B981", "#10B981", "#fff", "✓"
            elif m["clave"] == _mod_actual:
                fill, stroke, txt, marca = "var(--card)", BASE["blue"], BASE["blue"], str(i + 1)
            else:
                fill, stroke, txt, marca = "var(--line)", "#CBD5E1", "#94A3B8", str(i + 1)
            nodos.append({"x": lado, "y": y, "fill": fill, "stroke": stroke, "txt": txt, "marca": marca, "m": m})
            y += paso
        camino = " ".join(f'{"M" if i == 0 else "L"}{n["x"]} {n["y"]}' for i, n in enumerate(nodos))
        corte = 0
        for n in nodos:
            if not n["m"]["completo"]:
                break
            corte += 1
        camino_ok = " ".join(f'{"M" if i == 0 else "L"}{n["x"]} {n["y"]}' for i, n in enumerate(nodos[:corte]))
        alto = y + 40
        svg = [f'<svg viewBox="0 0 560 {alto}" width="100%" height="{alto}" font-family="Manrope" font-size="14">']
        svg.append(f'<path d="{camino}" fill="none" stroke="var(--line)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>')
        if corte > 1:
            svg.append(f'<path d="{camino_ok}" fill="none" stroke="#10B981" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>')
        for n in nodos:
            svg.append(f'<circle cx="{n["x"]}" cy="{n["y"]}" r="22" fill="{n["fill"]}" stroke="{n["stroke"]}" stroke-width="4"/>')
            svg.append(f'<text x="{n["x"]}" y="{n["y"] + 5}" text-anchor="middle" fill="{n["txt"]}" font-weight="700">{n["marca"]}</text>')
            tx = n["x"] + 34
            svg.append(f'<text x="{tx}" y="{n["y"] - 2}" fill="var(--ink)" font-weight="700">{n["m"]["emoji"]} {n["m"]["nombre"]}</text>')
            _lema = n["m"]["lema"] if len(n["m"]["lema"]) <= 44 else n["m"]["lema"][:41] + "…"
            svg.append(f'<text x="{tx}" y="{n["y"] + 15}" fill="var(--mute)" font-size="12.5">{n["m"]["hechos"]} de {n["m"]["total"]} logros · {_lema}</text>')
        ultimo = nodos[-1]
        svg.append(f'<circle cx="{ultimo["x"] + 120}" cy="{ultimo["y"] + 62}" r="24" fill="var(--amber2)" stroke="var(--amber)" stroke-width="4"/>')
        svg.append(f'<text x="{ultimo["x"] + 120}" y="{ultimo["y"] + 70}" text-anchor="middle" font-size="19">🏆</text>')
        svg.append(f'<text x="{ultimo["x"] - 10}" y="{ultimo["y"] + 58}" fill="var(--ambert)" font-weight="700">Meta final</text>')
        svg.append(f'<text x="{ultimo["x"] - 10}" y="{ultimo["y"] + 74}" fill="var(--ambert)" font-size="11.5">recuperar la inversión</text>')
        svg.append("</svg>")
        html(f'<div class="card">{"".join(svg)}</div>')
    with g2:
        st.markdown("### Tus medallas")
        medallas = "".join(
            f'<div class="logro {"ok" if h.logrado else ""}"><div class="med">{journey.MEDALLAS.get(h.clave, "🎖️")}</div>{h.titulo}</div>'
            for h in _hitos)
        html(f'<div class="card"><h4>{_ruta["hechos"]} de {_ruta["total"]} desbloqueadas</h4><div class="logros">{medallas}</div></div>')

    st.markdown("### Detalle por módulo")
    for m in _mods:
        if not m["total"]:
            continue
        with st.expander(f'{m["emoji"]}  {m["nombre"]} · {m["hechos"]} de {m["total"]}', expanded=m["clave"] == _mod_actual):
            st.caption(m["lema"])
            for h in m["lista"]:
                if h.logrado:
                    html(f'<div class="hito ok"><span class="chk">✓</span><div><b>{E(h.titulo)}</b><p>{E(h.detalle)}' + (f' · logrado el {h.fecha[:10]}' if h.fecha else "") + '</p></div></div>')
                else:
                    html(f'<div class="hito"><span class="chk">✓</span><div><b>{E(h.titulo)}</b><p>{E(journey.MISIONES.get(h.clave, h.detalle))} · en {h.pagina}</p></div></div>')
            pendientes = [h for h in m["lista"] if not h.logrado]
            if pendientes and st.button(f'Ir a {pendientes[0].pagina}', key=f'gomod_{m["clave"]}'):
                st.session_state["page"] = pendientes[0].pagina
                st.rerun()

# =============================================================================
# PÁGINA: Cotiza tu flete
# =============================================================================
elif page == "Cotiza tu flete":
    title("Cotiza tu flete", "Guarda las cotizaciones de tus forwarders y compara marítimo, aéreo y courier con tus números reales.",
          ayuda="""**Qué hace:** toma el volumen y peso de tu carga y te muestra, lado a lado, cuánto cuesta traerla por cada medio de transporte y cómo queda el costo final por unidad.\n\n**Cómo se usa:** 1) guarda las cotizaciones que te pasaron tus forwarders (puedes cargar ejemplos para probar); 2) ajusta arriba el volumen, peso y valor FOB de tu lote; 3) mira la comparación y marca tu favorita.\n\n**Dato clave:** el flete más barato no siempre gana. El aéreo cuesta más pero adelanta 30 días de venta, y en LCL se cobra el mayor entre metros cúbicos y toneladas.""")

    with st.expander("Cómo se cobra cada medio de transporte"):
        st.dataframe(pd.DataFrame([{"Medio": k, "Se cobra por": v["unidad"], "Tránsito típico": f"{v['dias']} días", "Cuándo conviene": v["ayuda"]} for k, v in MODOS_FLETE.items()]), width="stretch", hide_index=True)

    st.markdown("### 1. Tu carga")
    lote = st.session_state.get("lote")
    dfl_act = st.session_state.get("lineas_df")
    if lote is not None:
        cbm_d, peso_d, fob_d, un_d = lote.cubicaje.cbm_total, lote.cubicaje.peso_bruto_total_kg, lote.total.fob_total_usd, lote.total.unidades
        st.caption("Datos tomados de tu costeo actual. Puedes ajustarlos aquí sin afectarlo.")
    elif dfl_act is not None and len(dfl_act):
        cbm_d = float((dfl_act["largo_cm"] * dfl_act["ancho_cm"] * dfl_act["alto_cm"] / 1e6 * dfl_act["cajas"]).sum())
        peso_d = float((dfl_act["peso_kg"] * dfl_act["cajas"]).sum())
        fob_d = float((dfl_act["fob_unit_usd"] * dfl_act["cajas"] * dfl_act["unidades_por_caja"]).sum())
        un_d = int((dfl_act["cajas"] * dfl_act["unidades_por_caja"]).sum())
        st.caption("Datos tomados de los productos que cargaste en Costeo e internación.")
    else:
        cbm_d, peso_d, fob_d, un_d = 1.2, 200.0, 7000.0, 1000
        st.caption("Sin costeo cargado: usa estos valores de ejemplo o escribe los tuyos.")
    a, b, c, d = cols(4)
    cbm_l = a.number_input("Volumen total (m³)", 0.01, 500.0, float(round(cbm_d, 3)), 0.1, help="Suma del largo × ancho × alto de todas tus cajas, en metros.")
    peso_l = b.number_input("Peso bruto total (kg)", 0.1, 100000.0, float(round(peso_d, 1)), 1.0, help="Peso de toda la carga con embalaje incluido.")
    fob_l = c.number_input("Valor FOB total (USD)", 1.0, 10_000_000.0, float(round(fob_d, 2)), 50.0, help="Lo que le pagas al proveedor por la mercadería.")
    un_l = int(d.number_input("Unidades del lote", 1, 1_000_000, int(un_d), help="Para repartir el costo entre cada unidad."))
    a, b = cols(2)
    tlc_l = a.checkbox("Tengo Certificado de Origen TLC (arancel 0 %)", True, help="Sin certificado, Aduanas cobra 6 % sobre el CIF.")
    dg_l = b.checkbox("La carga lleva baterías de litio u otra carga peligrosa", False, help="Activa el recargo DG de cada cotización.")

    st.markdown("### 2. Tus cotizaciones")
    fletes = db.list_fletes()
    if not fletes:
        html('<div class="card"><h4>Aún no guardas cotizaciones</h4><p>Pide precio a dos o tres forwarders y guárdalos aquí abajo. Si quieres ver cómo funciona, carga un set de ejemplo con valores de mercado referenciales y edítalo después.</p></div>')
        if st.button("Cargar 4 cotizaciones de ejemplo", type="primary"):
            for f in [
                db.Flete("LCL consolidado", "Marítimo LCL", 95.0, "Forwarder A", "Shenzhen", "San Antonio", 250.0, 180.0, 330000.0, 40, 30.0, 0.0, "", "Tarifa por m³ con mínimo de 1 m³."),
                db.Flete("FCL 20 pies", "Marítimo FCL 20'", 2200.0, "Naviera B", "Shenzhen", "San Antonio", 0.0, 350.0, 450000.0, 35, 0.0, 0.0, "", "Contenedor completo, ~28 m³ útiles."),
                db.Flete("Aéreo consolidado", "Aéreo", 6.2, "Aerolínea C", "Hong Kong", "Santiago", 180.0, 120.0, 180000.0, 8, 40.0, 0.0, "", "Por kg cobrable, divisor volumétrico 5000."),
                db.Flete("Courier puerta a puerta", "Courier (DHL/FedEx)", 9.5, "DHL", "Shenzhen", "Santiago", 0.0, 0.0, 0.0, 6, 50.0, 0.0, "", "Incluye despacho aduanero bajo US$3.000 FOB."),
            ]:
                db.upsert_flete(f)
            db.auditar("flete", "cargadas cotizaciones de ejemplo")
            st.rerun()
    else:
        st.caption("Edita cualquier celda y se guarda sola. Marca la casilla Eliminar y confirma para borrarla.")
        dff = pd.DataFrame(fletes)[["id", "nombre", "modo", "proveedor", "tarifa", "minimo_usd", "recargos_usd", "locales_clp", "dias_transito", "dg_pct", "origen", "destino", "validez", "favorito"]].copy()
        dff["favorito"] = dff["favorito"].astype(bool)
        dff["eliminar"] = False
        ed = st.data_editor(dff, width="stretch", hide_index=True, key="fletes_editor", disabled=["id"], column_config={
            "id": st.column_config.NumberColumn("#", format="%d"),
            "nombre": st.column_config.TextColumn("Cotización", help="Cómo identificas esta oferta."),
            "modo": st.column_config.SelectboxColumn("Medio", options=list(MODOS_FLETE), help="Define cómo se calcula el cobro."),
            "proveedor": st.column_config.TextColumn("Forwarder"),
            "tarifa": st.column_config.NumberColumn("Tarifa USD", format="%.2f", help="Por m³ en LCL, por contenedor en FCL, por kg cobrable en aéreo y courier."),
            "minimo_usd": st.column_config.NumberColumn("Mínimo USD", format="%.0f", help="Cobro mínimo aunque tu carga sea menor."),
            "recargos_usd": st.column_config.NumberColumn("Recargos USD", format="%.0f", help="THC, emisión de BL, handling, documentación."),
            "locales_clp": st.column_config.NumberColumn("Gastos locales CLP", format="%.0f", help="Desconsolidación, almacenaje y transporte a tu bodega."),
            "dias_transito": st.column_config.NumberColumn("Días", format="%d", help="Tránsito puerta a puerta estimado."),
            "dg_pct": st.column_config.NumberColumn("Recargo DG %", format="%.0f", help="Sobrecosto por carga peligrosa."),
            "origen": "Origen", "destino": "Destino",
            "validez": st.column_config.TextColumn("Válida hasta", help="Las tarifas de flete suelen durar 15 a 30 días."),
            "favorito": st.column_config.CheckboxColumn("Elegida", help="Marca la que vas a usar."),
            "eliminar": st.column_config.CheckboxColumn("Eliminar", help="Marca y confirma abajo."),
        })
        borrar = [int(r["id"]) for _, r in ed.iterrows() if r["eliminar"]]
        cambios = 0
        for orig, (_, row) in zip(fletes, ed.iterrows()):
            if int(row["id"]) in borrar:
                continue
            nuevo = {k: row[k] for k in ("nombre", "modo", "proveedor", "tarifa", "minimo_usd", "recargos_usd", "locales_clp", "dias_transito", "dg_pct", "origen", "destino", "validez")}
            nuevo["favorito"] = int(bool(row["favorito"]))
            if any(str(orig.get(k)) != str(nuevo[k]) for k in nuevo) and str(nuevo["nombre"]).strip():
                db.upsert_flete(db.Flete(id=orig["id"], nombre=str(nuevo["nombre"]).strip(), modo=str(nuevo["modo"]), tarifa=float(nuevo["tarifa"]), proveedor=str(nuevo["proveedor"] or ""), origen=str(nuevo["origen"] or ""), destino=str(nuevo["destino"] or ""), minimo_usd=float(nuevo["minimo_usd"]), recargos_usd=float(nuevo["recargos_usd"]), locales_clp=float(nuevo["locales_clp"]), dias_transito=int(nuevo["dias_transito"]), dg_pct=float(nuevo["dg_pct"]), seguro_pct=orig.get("seguro_pct", 0.0), validez=str(nuevo["validez"] or ""), notas=orig.get("notas") or "", favorito=nuevo["favorito"], fecha=orig["fecha"]))
                cambios += 1
        if cambios:
            st.toast(f"{cambios} cotización(es) actualizada(s)")
            st.rerun()
        if borrar:
            st.warning(f"Vas a eliminar {len(borrar)} cotización(es): {', '.join(str(b) for b in borrar)}.")
            if st.button("Confirmar eliminación", type="primary"):
                for fid in borrar:
                    db.eliminar_flete(fid)
                db.auditar("flete", f"eliminadas {borrar}")
                st.rerun()

    with st.expander("Agregar una cotización nueva"):
        with st.form("form_flete", clear_on_submit=True):
            a, b, c = cols(3)
            n_f = a.text_input("Nombre de la cotización", help="Por ejemplo: LCL Andes octubre.")
            modo_f = a.selectbox("Medio de transporte", list(MODOS_FLETE), help="Cambia la forma de cobro: m³, contenedor o kg.")
            prov_f = a.text_input("Forwarder o naviera", help="Quién te entregó el precio.")
            st.caption(MODOS_FLETE[modo_f]["ayuda"])
            tar_f = b.number_input(f"Tarifa ({MODOS_FLETE[modo_f]['unidad']})", 0.0, 1_000_000.0, 0.0, 1.0, help="El precio base que te cotizaron.")
            min_f = b.number_input("Cobro mínimo (USD)", 0.0, 100000.0, 0.0, 10.0, help="Lo que cobran aunque tu carga sea más chica. En LCL suele ser 1 m³.")
            rec_f = b.number_input("Recargos fijos (USD)", 0.0, 100000.0, 0.0, 10.0, help="THC, emisión de BL, handling, documentación: pídelos desglosados.")
            loc_f = c.number_input("Gastos locales en Chile (CLP)", 0.0, 10_000_000.0, 0.0, 10000.0, help="Desconsolidación, almacenaje y transporte a tu bodega.")
            dias_f = int(c.number_input("Días de tránsito", 1, 200, int(MODOS_FLETE[modo_f]["dias"]), help="Puerta a puerta. Influye en cuándo puedes empezar a vender."))
            dg_f = c.number_input("Recargo por carga peligrosa (%)", 0.0, 100.0, 0.0, 5.0, help="Se aplica solo si marcas que tu carga lleva baterías.")
            a, b, c = cols(3)
            ori_f = a.text_input("Origen", help="Puerto o ciudad de salida.")
            des_f = b.text_input("Destino", help="Puerto o aeropuerto de llegada en Chile.")
            val_f = c.text_input("Válida hasta", help="Fecha de vencimiento de la tarifa.")
            if st.form_submit_button("Guardar cotización", type="primary"):
                if not n_f.strip() or tar_f <= 0:
                    st.error("Ingresa un nombre y una tarifa mayor a cero.")
                else:
                    db.upsert_flete(db.Flete(nombre=n_f.strip(), modo=modo_f, tarifa=tar_f, proveedor=prov_f, origen=ori_f, destino=des_f, minimo_usd=min_f, recargos_usd=rec_f, locales_clp=loc_f, dias_transito=dias_f, dg_pct=dg_f, validez=val_f))
                    db.auditar("flete", f"guardada cotización {n_f.strip()}")
                    st.toast("Cotización guardada", icon="✅")
                    st.rerun()

    fletes = db.list_fletes()
    if fletes:
        st.markdown("### 3. Comparación para tu carga")
        ops = comparar_fletes(fletes, cbm_l, peso_l, fob_l, un_l, TC, tlc_l, dg_l)
        mejor, rapido = ops[0], min(ops, key=lambda o: o.dias_transito)
        a, b, c = cols(3)
        with a:
            html(f'<div class="card"><h4>Más barato</h4><div class="mid num">{clp(mejor.landed_unit_clp)}</div><p style="margin-top:8px"><b>{E(mejor.nombre)}</b> · {E(mejor.modo)}<br>{mejor.dias_transito} días · flete {usd(mejor.flete_usd)}</p></div>')
        with b:
            dif = rapido.landed_unit_clp - mejor.landed_unit_clp
            dias_menos = mejor.dias_transito - rapido.dias_transito
            html(f'<div class="card"><h4>Más rápido</h4><div class="mid num">{rapido.dias_transito} días</div><p style="margin-top:8px"><b>{E(rapido.nombre)}</b><br>' + (f'Llega {dias_menos} días antes y cuesta {clp(dif)} más por unidad.' if dif > 0 else 'Además es el más barato.') + '</p></div>')
        with c:
            spread = ops[-1].landed_unit_clp - mejor.landed_unit_clp
            html(f'<div class="card"><h4>Diferencia entre la mejor y la peor</h4><div class="mid num">{clp(spread)}</div><p style="margin-top:8px">por unidad · {clp(spread * un_l)} en todo el lote</p></div>')
        tabla = pd.DataFrame([{
            "Cotización": o.nombre, "Medio": o.modo, "Se cobra": o.unidad_texto, "Días": o.dias_transito,
            "Flete USD": round(o.flete_usd), "Seguro USD": round(o.seguro_usd), "CIF USD": round(o.cif_usd),
            "Arancel USD": round(o.advalorem_usd), "Agente USD": round(o.agente_usd), "Locales CLP": o.locales_clp,
            "Flete por unidad": o.costo_flete_unit_clp, "Landed por unidad": o.landed_unit_clp,
            "Desembolso total": o.desembolso_clp, "Factor": o.factor_internacion, "IVA recuperable": round(o.iva_usd * TC),
        } for o in ops])
        st.dataframe(tabla.style.background_gradient(subset=["Landed por unidad"], cmap="RdYlGn_r"), width="stretch", hide_index=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Flete y gastos por unidad", x=[o.nombre for o in ops], y=[o.costo_flete_unit_clp for o in ops], marker_color=BASE["amber"]))
        fig.add_trace(go.Bar(name="Resto del landed cost", x=[o.nombre for o in ops], y=[o.landed_unit_clp - o.costo_flete_unit_clp for o in ops], marker_color=BASE["blue"]))
        fig.update_layout(barmode="stack", yaxis_title="CLP")
        st.markdown("**Costo por unidad puesta en bodega**")
        st.plotly_chart(fig_layout(fig, 330), width="stretch")
        for o in ops:
            if o.aviso:
                st.caption(f"**{o.nombre}:** {o.aviso}")
        fav = next((o for o in ops if any(f["favorito"] and f["nombre"] == o.nombre for f in fletes)), None)
        elegida = st.selectbox("Marcar la cotización que vas a usar", [o.nombre for o in ops], index=[o.nombre for o in ops].index(fav.nombre) if fav else 0, help="Queda marcada como elegida y puedes copiar sus valores al costeo.")
        a, b = cols(2)
        if a.button("Marcar como elegida"):
            fid = next(f["id"] for f in fletes if f["nombre"] == elegida)
            db.marcar_favorito_flete(fid)
            st.toast("Cotización elegida", icon="✅")
            st.rerun()
        if b.button("Usar estos valores en mi costeo", type="primary"):
            o = next(x for x in ops if x.nombre == elegida)
            C = st.session_state.setdefault("comunes", {})
            C.update(flete=o.flete_base_usd, dg_pct=next(f["dg_pct"] for f in fletes if f["nombre"] == elegida), descons=o.locales_clp, almac=0.0, transp=0.0, forwarder=o.proveedor, origen=next(f["origen"] for f in fletes if f["nombre"] == elegida), destino=next(f["destino"] for f in fletes if f["nombre"] == elegida))
            _bor = db.cargar_borrador("costeo") or {}
            _lin = st.session_state["lineas_df"].to_dict("records") if "lineas_df" in st.session_state else _bor.get("lineas", [])
            db.guardar_borrador("costeo", {"lineas": _lin, "comunes": C})
            st.session_state["page"] = "Costeo e internación"
            st.toast("Valores copiados al costeo", icon="✅")
            st.rerun()
