"""Convenience helpers for PetSafe pet-related API endpoints."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from .client import PetSafeClient


async def list_pets(client: "PetSafeClient") -> List[Dict[str, Any]]:
    """Return all pets configured in the account."""

    response = await client.api_get("pets/pets")
    payload = json.loads(response.content.decode("UTF-8"))
    data = payload.get("data", payload)
    return data if isinstance(data, list) else [data]


async def list_pet_products(
    client: "PetSafeClient", pet_id: str
) -> List[Dict[str, Any]]:
    """Return all products associated with the provided pet identifier."""

    if not pet_id:
        raise ValueError("pet_id must be provided")

    from urllib.parse import quote_plus

    path = f"directory/petProduct?petId={quote_plus(pet_id)}"
    response = await client.api_get(path)
    payload = json.loads(response.content.decode("UTF-8"))
    data = payload.get("data", payload)
    return data if isinstance(data, list) else [data]
