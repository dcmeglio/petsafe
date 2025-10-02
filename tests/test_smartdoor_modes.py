"""Unit tests for SmartDoor mode control helpers."""

from __future__ import annotations

import json
import time
from typing import List

import httpx
import pytest

from petsafe.client import PetSafeClient
from petsafe.const import (
    PETSAFE_API_BASE,
    SMARTDOOR_MODE_MANUAL_LOCKED,
    SMARTDOOR_MODE_MANUAL_UNLOCKED,
    SMARTDOOR_MODE_SMART,
)
from petsafe.devices import DeviceSmartDoor


def _build_client(http_client: httpx.AsyncClient) -> PetSafeClient:
    client = PetSafeClient(
        email="user@example.com",
        id_token="id-token",
        refresh_token="refresh-token",
        access_token="access-token",
        client=http_client,
    )
    client._token_expires_time = time.time() + 3600  # noqa: SLF001 - test helper
    return client


def _decode_request_body(request: httpx.Request) -> dict:
    return json.loads(request.content.decode("utf-8")) if request.content else {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "expected_mode"),
    [
        ("lock", SMARTDOOR_MODE_MANUAL_LOCKED),
        ("unlock", SMARTDOOR_MODE_MANUAL_UNLOCKED),
        ("smart_mode", SMARTDOOR_MODE_SMART),
    ],
)
async def test_device_smartdoor_mode_helpers_send_patch(
    method_name: str, expected_mode: str
) -> None:
    requests: List[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = _build_client(http_client)
        door = DeviceSmartDoor(
            client,
            {
                "thingName": "door-123",
                "shadow": {"state": {"reported": {"door": {"mode": "INITIAL"}}}},
            },
        )

        method = getattr(door, method_name)
        await method(update_data=False)

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "PATCH"
    assert str(request.url) == (
        PETSAFE_API_BASE + "smartdoor/product/product/door-123/shadow"
    )
    assert _decode_request_body(request) == {"door": {"mode": expected_mode}}
    assert door.mode == expected_mode


@pytest.mark.asyncio
async def test_client_manual_lock_refreshes_state() -> None:
    requests: List[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "PATCH":
            return httpx.Response(200, json={})
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "thingName": "door-123",
                        "shadow": {
                            "state": {
                                "reported": {
                                    "door": {"mode": SMARTDOOR_MODE_MANUAL_LOCKED}
                                }
                            }
                        },
                    }
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = _build_client(http_client)
        door = await client.manual_lock_smartdoor("door-123")

    assert [req.method for req in requests] == ["PATCH", "GET"]
    assert str(requests[0].url) == (
        PETSAFE_API_BASE + "smartdoor/product/product/door-123/shadow"
    )
    assert _decode_request_body(requests[0]) == {
        "door": {"mode": SMARTDOOR_MODE_MANUAL_LOCKED}
    }
    assert door.mode == SMARTDOOR_MODE_MANUAL_LOCKED


@pytest.mark.asyncio
async def test_client_manual_unlock_without_refresh() -> None:
    requests: List[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = _build_client(http_client)
        door = await client.manual_unlock_smartdoor("door-123", update_data=False)

    assert [req.method for req in requests] == ["PATCH"]
    assert str(requests[0].url) == (
        PETSAFE_API_BASE + "smartdoor/product/product/door-123/shadow"
    )
    assert _decode_request_body(requests[0]) == {
        "door": {"mode": SMARTDOOR_MODE_MANUAL_UNLOCKED}
    }
    assert door.mode == SMARTDOOR_MODE_MANUAL_UNLOCKED


@pytest.mark.asyncio
async def test_client_smart_mode_helper() -> None:
    requests: List[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": {
                    "thingName": "door-123",
                    "shadow": {
                        "state": {
                            "reported": {"door": {"mode": SMARTDOOR_MODE_SMART}}
                        }
                    },
                }
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = _build_client(http_client)
        door = await client.smart_mode_smartdoor("door-123")

    assert [req.method for req in requests] == ["PATCH", "GET"]
    assert str(requests[0].url) == (
        PETSAFE_API_BASE + "smartdoor/product/product/door-123/shadow"
    )
    assert _decode_request_body(requests[0]) == {
        "door": {"mode": SMARTDOOR_MODE_SMART}
    }
    assert door.mode == SMARTDOOR_MODE_SMART
