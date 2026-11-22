"""
currency.py — Tipo de cambio resiliente (Dólar Observado y UF) desde mindicador.cl.

- `fetch_indicadores()` consulta la API pública con caché de 1 hora.
- Si la API falla, se usa el último valor guardado en `config_general` (editable en pantalla).
- `get_rates()` devuelve los valores vigentes considerando overrides manuales en session_state.
"""
from __future__ import annotations

from typing import Any

import requests
import streamlit as st

from database import get_config_float, set_config

API_URL = "https://mindicador.cl/api"
TIMEOUT = 6


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_indicadores() -> dict[str, Any]:
    """Consulta mindicador.cl. Nunca lanza excepción: devuelve `ok=False` y error."""
    try:
        r = requests.get(API_URL, timeout=TIMEOUT, headers={"User-Agent": "Importa/2.1"})
        r.raise_for_status()
        data = r.json()
        return {
            "dolar": float(data["dolar"]["valor"]),
            "uf": float(data["uf"]["valor"]),
            "fecha": str(data["dolar"]["fecha"])[:10],
            "ok": True,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de red/formato cae a fallback
        return {"dolar": 0.0, "uf": 0.0, "fecha": "", "ok": False, "error": str(exc)}


def get_rates() -> dict[str, Any]:
    """Devuelve {'usd','uf','fuente','fecha'} respetando el override manual del usuario."""
    api = fetch_indicadores()
    if api["ok"] and not st.session_state.get("tc_manual", False):
        usd, uf, fuente, fecha = api["dolar"], api["uf"], "mindicador.cl", api["fecha"]
        # Persistimos el último valor válido como fallback futuro
        if get_config_float("tc_usd") != usd:
            set_config("tc_usd", round(usd, 2), global_=True)
            set_config("tc_uf", round(uf, 2), global_=True)
    else:
        usd = float(st.session_state.get("tc_usd_manual", get_config_float("tc_usd", 950.0)))
        uf = float(st.session_state.get("tc_uf_manual", get_config_float("tc_uf", 39500.0)))
        fuente = "manual" if st.session_state.get("tc_manual") else "fallback local"
        fecha = ""
    return {"usd": usd, "uf": uf, "fuente": fuente, "fecha": fecha, "api_ok": api["ok"], "api_error": api["error"]}


def render_rate_controls() -> dict[str, Any]:
    """Controles de sidebar: muestra la API y permite forzar un valor manual."""
    api = fetch_indicadores()
    st.sidebar.markdown("#### 💱 Tipo de cambio")
    if api["ok"]:
        st.sidebar.caption(f"mindicador.cl · {api['fecha']}")
    else:
        st.sidebar.warning("API no disponible, usando valor local editable.")
    manual = st.sidebar.toggle("Editar manualmente", value=not api["ok"], key="tc_manual")
    if manual:
        st.sidebar.number_input(
            "USD Observado (CLP)",
            min_value=1.0,
            value=float(st.session_state.get("tc_usd_manual", api["dolar"] or get_config_float("tc_usd", 950.0))),
            step=1.0,
            key="tc_usd_manual",
        )
        st.sidebar.number_input(
            "UF (CLP)",
            min_value=1.0,
            value=float(st.session_state.get("tc_uf_manual", api["uf"] or get_config_float("tc_uf", 39500.0))),
            step=10.0,
            key="tc_uf_manual",
        )
        if st.sidebar.button("Guardar como fallback"):
            set_config("tc_usd", st.session_state["tc_usd_manual"])
            set_config("tc_uf", st.session_state["tc_uf_manual"])
            st.sidebar.success("Guardado.")
    rates = get_rates()
    st.sidebar.metric("USD", f"${rates['usd']:,.0f}".replace(",", "."))
    st.sidebar.metric("UF", f"${rates['uf']:,.0f}".replace(",", "."))
    return rates
