# Written with AI assistance (Claude Code). See AI_USE.md.
"""HiRISE footprints from the PDS Orbital Data Explorer (ODE) REST API."""

from __future__ import annotations

import math

from ariadne.fetch.http import get_json
from ariadne.fetch.places import MARS_RADIUS_M

ODE_URL = "https://oderest.rsl.wustl.edu/live2/"


def bounds_to_lonlat(bounds: tuple[float, float, float, float]) -> dict:
    left, bottom, right, top = bounds
    deg = lambda m: math.degrees(m / MARS_RADIUS_M)  # noqa: E731
    return {
        "westlon": round(deg(left), 6),
        "eastlon": round(deg(right), 6),
        "minlat": round(deg(bottom), 6),
        "maxlat": round(deg(top), 6),
    }


def query_params(bounds, product_type: str) -> dict:
    return {
        "query": "product",
        "target": "mars",
        "output": "JSON",
        "ihid": "MRO",
        "iid": "HIRISE",
        "pt": product_type,
        **bounds_to_lonlat(bounds),
    }


def query_products(bounds, product_type: str) -> tuple[list[dict], dict]:
    """All HiRISE products of a type whose footprints touch the box, plus the query record."""
    params = query_params(bounds, product_type)
    count = int(get_json(ODE_URL, {**params, "results": "c"})["ODEResults"].get("Count", 0))
    products: list[dict] = []
    if count:
        res = get_json(ODE_URL, {**params, "results": "m", "limit": count + 10, "offset": 1})
        raw = res["ODEResults"].get("Products", {})
        raw = raw.get("Product", []) if isinstance(raw, dict) else []
        products = raw if isinstance(raw, list) else [raw]
    if len(products) != count:
        raise OSError(f"ODE returned {len(products)} of {count} {product_type} products")
    return products, {"url": ODE_URL, "params": params, "count": count}
