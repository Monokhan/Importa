"""
market_intel.py — Benchmark de precios en Mercado Libre Chile.

Consulta `https://api.mercadolibre.com/sites/MLC/search?q=...`. La API pública puede exigir un
Access Token (Bearer) para algunas cuentas/regiones; se acepta uno opcional. Si la consulta falla,
la app ofrece ingresar precios de competencia manualmente.
"""
from __future__ import annotations

import statistics
from typing import Any

import pandas as pd
import requests
import streamlit as st

ML_SEARCH_URL = "https://api.mercadolibre.com/sites/MLC/search"
TIMEOUT = 8


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_mercadolibre(query: str, limit: int = 50, access_token: str = "") -> dict[str, Any]:
    """Devuelve {'ok', 'error', 'items': [...]}. Nunca lanza."""
    headers = {"User-Agent": "Importa/2.1", "Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    try:
        r = requests.get(ML_SEARCH_URL, params={"q": query, "limit": min(limit, 50)}, headers=headers, timeout=TIMEOUT)
        if r.status_code in (401, 403):
            return {"ok": False, "error": f"Mercado Libre respondió {r.status_code}: la API requiere Access Token para esta búsqueda.", "items": []}
        r.raise_for_status()
        data = r.json()
        items = []
        for it in data.get("results", []):
            ship = it.get("shipping") or {}
            items.append(
                {
                    "titulo": it.get("title", ""),
                    "precio": float(it.get("price") or 0),
                    "envio_gratis": bool(ship.get("free_shipping", False)),
                    "logistica": ship.get("logistic_type", "") or "",
                    "vendidos": it.get("sold_quantity", 0),
                    "condicion": it.get("condition", ""),
                    "vendedor": (it.get("seller") or {}).get("nickname", ""),
                    "url": it.get("permalink", ""),
                }
            )
        return {"ok": True, "error": "", "items": items}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "items": []}


def resumir_precios(items: list[dict[str, Any]]) -> dict[str, Any]:
    precios = [i["precio"] for i in items if i.get("precio", 0) > 0]
    if not precios:
        return {"n": 0, "min": 0, "mediana": 0, "max": 0, "promedio": 0, "pct_envio_gratis": 0, "pct_full": 0}
    n = len(precios)
    gratis = sum(1 for i in items if i.get("envio_gratis"))
    full = sum(1 for i in items if i.get("logistica") == "fulfillment")
    return {
        "n": n,
        "min": min(precios),
        "mediana": statistics.median(precios),
        "max": max(precios),
        "promedio": sum(precios) / n,
        "pct_envio_gratis": gratis / len(items) * 100 if items else 0,
        "pct_full": full / len(items) * 100 if items else 0,
    }


def items_a_df(items: list[dict[str, Any]]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["titulo", "precio", "envio_gratis", "logistica", "vendidos", "vendedor", "url"])
    return pd.DataFrame(items).sort_values("precio").reset_index(drop=True)


def resumen_manual(precios_texto: str) -> dict[str, Any]:
    """Permite pegar precios separados por coma/espacio/salto si la API no responde."""
    nums: list[float] = []
    for tok in precios_texto.replace("$", "").replace(".", "").replace(";", ",").replace("\n", ",").replace(" ", ",").split(","):
        tok = tok.strip()
        if tok.isdigit():
            nums.append(float(tok))
    return resumir_precios([{"precio": p, "envio_gratis": False, "logistica": ""} for p in nums])
