"""Integration tests covering the PetSafe login flow."""
from __future__ import annotations

import pytest

from petsafe import general
from petsafe.client import PetSafeClient


@pytest.mark.asyncio
async def test_can_retrieve_product_sharing(authenticated_client: PetSafeClient) -> None:
    relationships = await general.list_product_sharing(authenticated_client)
    assert isinstance(relationships, list)


@pytest.mark.asyncio
async def test_tokens_are_available(authenticated_client: PetSafeClient) -> None:
    assert authenticated_client.id_token
    assert authenticated_client.access_token
    assert authenticated_client.refresh_token
