"""Integration coverage for miscellaneous PetSafe API endpoints using live credentials."""
from __future__ import annotations

import json
from typing import Iterable

import pytest

from petsafe.client import PetSafeClient
from petsafe import general


def _dump_response(response_json: object) -> str:
    """Return a pretty JSON string for captured API responses."""

    return json.dumps(response_json, indent=2, sort_keys=True)


def _normalise_payload(payload: object) -> Iterable[object]:
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if isinstance(payload, list):
        return payload
    if payload is None:
        return []
    return [payload]


@pytest.mark.asyncio
async def test_list_product_sharing(authenticated_client: PetSafeClient) -> None:
    response = await authenticated_client.api_get("directory/product-sharing")
    payload = response.json()
    print(_dump_response(payload))

    sharing = await general.list_product_sharing(authenticated_client)
    assert isinstance(sharing, list)

    normalised = list(_normalise_payload(payload))
    if normalised:
        assert len(sharing) == len(normalised)
