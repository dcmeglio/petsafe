"""Helpers for miscellaneous PetSafe platform endpoints."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from .client import PetSafeClient


async def list_product_sharing(client: "PetSafeClient") -> List[Dict[str, Any]]:
    """Return product sharing relationships for the authenticated account."""

    response = await client.api_get("directory/product-sharing")
    payload = json.loads(response.content.decode("UTF-8"))
    data = payload.get("data", payload)
    return data if isinstance(data, list) else [data]


async def get_account_details(client: "PetSafeClient") -> Dict[str, Any]:
    """Return the account details for the authenticated PetSafe user."""

    response = await client.api_get("directory/account")
    payload = json.loads(response.content.decode("UTF-8"))
    data = payload.get("data", payload)
    if isinstance(data, dict):
        return data
    raise ValueError("Unexpected response payload for account details")
