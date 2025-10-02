"""Integration coverage for the SmartDoor API endpoints using live credentials."""
from __future__ import annotations

import json
from typing import Iterable, Sequence

import httpx

import pytest

from petsafe.client import PetSafeClient
from petsafe.devices import DeviceSmartDoor


def _dump_response(response_json: object) -> str:
    """Return a pretty JSON string for captured API responses."""

    return json.dumps(response_json, indent=2, sort_keys=True)


def _normalise_payload(payload: object) -> Sequence[object]:
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return list(payload)
    if payload is None:
        return []
    return [payload]


def _ensure_smartdoor_available(smartdoors: Iterable[DeviceSmartDoor]) -> DeviceSmartDoor:
    try:
        return next(iter(smartdoors))
    except StopIteration:
        pytest.skip("No SmartDoor devices are associated with this PetSafe account.")


def _print_response_body(response: httpx.Response) -> object:
    """Pretty-print the HTTP response body for debugging live API runs."""

    try:
        payload = response.json()
    except ValueError:
        body = response.text
        print(body)
        return body

    print(_dump_response(payload))
    return payload


@pytest.mark.asyncio
async def test_get_smartdoors(authenticated_client: PetSafeClient) -> None:
    response = await authenticated_client.api_get("smartdoor/product/product")
    response.raise_for_status()
    payload = response.json()
    print(_dump_response(payload))

    smartdoors = await authenticated_client.get_smartdoors()
    assert isinstance(smartdoors, list)
    assert all(isinstance(door, DeviceSmartDoor) for door in smartdoors)

    normalised = list(_normalise_payload(payload))
    if normalised:
        assert len(smartdoors) == len(normalised)


@pytest.mark.asyncio
async def test_get_single_smartdoor(authenticated_client: PetSafeClient) -> None:
    smartdoors = await authenticated_client.get_smartdoors()
    door = _ensure_smartdoor_available(smartdoors)

    response = await authenticated_client.api_get(f"smartdoor/product/product/{door.api_name}/")
    response.raise_for_status()
    payload = response.json()
    print(_dump_response(payload))

    fresh = await authenticated_client.get_smartdoor(door.api_name)
    assert isinstance(fresh, DeviceSmartDoor)
    assert fresh.api_name == door.api_name

    normalised = _normalise_payload(payload)
    if normalised:
        assert fresh.data == normalised[0]


@pytest.mark.asyncio
async def test_smartdoor_activity(authenticated_client: PetSafeClient) -> None:
    smartdoors = await authenticated_client.get_smartdoors()
    door = _ensure_smartdoor_available(smartdoors)

    limit = 5
    response = await authenticated_client.api_get(f"{door.api_path}activity?limit={limit}")
    response.raise_for_status()
    payload = response.json()
    print(_dump_response(payload))

    activity = await door.get_activity(limit=limit)
    assert isinstance(activity, list)
    normalised = list(_normalise_payload(payload))
    if normalised:
        assert activity == normalised


@pytest.mark.asyncio
async def test_set_smartdoor_mode_noop(authenticated_client: PetSafeClient) -> None:
    smartdoors = await authenticated_client.get_smartdoors()
    door = _ensure_smartdoor_available(smartdoors)

    await door.update_data()
    current_mode = door.mode
    if not current_mode:
        pytest.skip("Unable to determine the SmartDoor mode for this account.")

    response = await authenticated_client.api_patch(
        door.api_path + "shadow", data={"door": {"mode": current_mode}}
    )
    payload = _print_response_body(response)
    response.raise_for_status()

    await door.update_data()
    assert door.mode == current_mode

    if isinstance(payload, dict):
        assert payload or payload == {}
