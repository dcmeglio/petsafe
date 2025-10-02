"""Shared integration testing fixtures for authenticated PetSafe access."""
from __future__ import annotations

import json
import os
import stat
import sys
import time
from getpass import getpass
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest
import pytest_asyncio

try:
    from petsafe import general
    from petsafe.client import InvalidCodeException, PetSafeClient
except ModuleNotFoundError as exc:  # pragma: no cover - dependency missing
    pytest.skip(f"Required dependency not available: {exc}", allow_module_level=True)

_SECRET_PATH = Path.home() / ".petsafe_integration_secrets.json"


def _load_secrets() -> Dict[str, Any]:
    if _SECRET_PATH.exists():
        try:
            return json.loads(_SECRET_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_secrets(secrets: Dict[str, Any]) -> None:
    _SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_PATH.write_text(json.dumps(secrets, indent=2))
    if os.name == "posix":
        _SECRET_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _collect_tokens(client: PetSafeClient) -> Dict[str, Any]:
    return {
        "id_token": client.id_token,
        "access_token": client.access_token,
        "refresh_token": client.refresh_token,
        "expires_at": getattr(client, "_token_expires_time", 0),
    }


def _ensure_email(secrets: Dict[str, Any]) -> str:
    email = secrets.get("email")
    if email:
        return email

    email = input("Enter the PetSafe account email: ").strip()
    if not email:
        raise RuntimeError("A PetSafe account email address is required to continue.")

    secrets["email"] = email
    _save_secrets(secrets)
    return email


async def _perform_interactive_login(client: PetSafeClient, secrets: Dict[str, Any]) -> None:
    await client.request_code()
    print("A verification code has been sent to your PetSafe account email.")
    while True:
        code = getpass("Enter the verification code from the email: ").strip()
        if not code:
            raise RuntimeError("A verification code is required to authenticate.")
        try:
            await client.request_tokens_from_code(code)
            secrets["last_code"] = code
            break
        except InvalidCodeException:
            print("The provided code was not accepted. Please try again.")

    secrets["tokens"] = _collect_tokens(client)
    _save_secrets(secrets)


async def _ensure_active_tokens(client: PetSafeClient, secrets: Dict[str, Any]) -> None:
    tokens = secrets.get("tokens", {})
    if tokens:
        client._id_token = tokens.get("id_token")  # noqa: SLF001 - intentional use of private attribute
        client._access_token = tokens.get("access_token")  # noqa: SLF001 - intentional use of private attribute
        client._refresh_token = tokens.get("refresh_token")  # noqa: SLF001 - intentional use of private attribute
        client._token_expires_time = tokens.get("expires_at", 0)  # noqa: SLF001 - intentional use of private attribute

    if not client.refresh_token:
        await _perform_interactive_login(client, secrets)
        return

    now = time.time()
    if not client.id_token or now >= getattr(client, "_token_expires_time", 0) - 120:
        await general.list_product_sharing(client)
        secrets["tokens"] = _collect_tokens(client)
        _save_secrets(secrets)
        return

    try:
        await general.list_product_sharing(client)
    except Exception:  # pragma: no cover - network error surface
        await _perform_interactive_login(client, secrets)
        return

    secrets["tokens"] = _collect_tokens(client)
    _save_secrets(secrets)


@pytest_asyncio.fixture
async def authenticated_client() -> PetSafeClient:
    if not sys.stdin.isatty():
        pytest.skip("Interactive login tests require a TTY.")

    secrets: Dict[str, Any] = _load_secrets()
    email = _ensure_email(secrets)

    async with httpx.AsyncClient() as httpx_client:
        client = PetSafeClient(
            email=email,
            id_token=secrets.get("tokens", {}).get("id_token"),
            refresh_token=secrets.get("tokens", {}).get("refresh_token"),
            access_token=secrets.get("tokens", {}).get("access_token"),
            client=httpx_client,
        )

        await _ensure_active_tokens(client, secrets)

        try:
            yield client
        finally:
            secrets["tokens"] = _collect_tokens(client)
            _save_secrets(secrets)
