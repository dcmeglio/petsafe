"""Integration coverage for the pet-focused API endpoints using live credentials."""
from __future__ import annotations

import json
from typing import Iterable, Mapping, Sequence
from urllib.parse import quote_plus

import pytest

from petsafe.client import PetSafeClient
from petsafe import pets


def _dump_response(response_json: object) -> str:
    """Return a pretty JSON string for captured API responses."""

    return json.dumps(response_json, indent=2, sort_keys=True)


def _extract_pet_id(pet_data: Mapping[str, object]) -> str | None:
    """Try to obtain a usable pet identifier from the API payload."""

    for key in ("id", "petId", "pet_id"):
        value = pet_data.get(key)
        if value:
            return str(value)
    return None


def _ensure_pets_available(pet_list: Sequence[Mapping[str, object]]) -> Mapping[str, object]:
    try:
        return pet_list[0]
    except IndexError:
        pytest.skip("No pets are associated with this PetSafe account.")


def _normalise_payload(payload: object) -> Iterable[object]:
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return list(payload)
    if payload is None:
        return []
    return [payload]


@pytest.mark.asyncio
async def test_list_pets(authenticated_client: PetSafeClient) -> None:
    response = await authenticated_client.api_get("pets/pets")
    response.raise_for_status()
    payload = response.json()
    print(_dump_response(payload))

    pets_from_helper = await pets.list_pets(authenticated_client)
    assert isinstance(pets_from_helper, list)

    normalised = list(_normalise_payload(payload))
    if normalised:
        assert len(pets_from_helper) == len(normalised)
        assert pets_from_helper == normalised


@pytest.mark.asyncio
async def test_list_pet_products(authenticated_client: PetSafeClient) -> None:
    pet_list = await pets.list_pets(authenticated_client)
    pet_data = _ensure_pets_available(pet_list)

    pet_id = _extract_pet_id(pet_data)
    if not pet_id:
        pytest.skip("Unable to determine a pet identifier from the API response.")

    response = await authenticated_client.api_get(
        f"directory/petProduct?petId={quote_plus(pet_id)}"
    )
    response.raise_for_status()
    payload = response.json()
    print(_dump_response(payload))

    products = await pets.list_pet_products(authenticated_client, pet_id)
    assert isinstance(products, list)

    normalised = list(_normalise_payload(payload))
    if normalised:
        assert len(products) == len(normalised)
        assert products == normalised
