"""Capability seam for verifying a Supabase Auth access token.

The frontend authenticates the user with Supabase Auth and sends the resulting
access token as ``Authorization: Bearer <jwt>``. The backend never trusts a
client-supplied identity: it resolves the token to a real user here, then maps
that user to a merchant server-side (security-architecture.md #4).

Real verifier -> ``GET {SUPABASE_URL}/auth/v1/user`` (no JWT secret needed; the
Supabase Auth server validates the signature and expiry). Fake verifier -> a
deterministic local user, so the whole stack runs with no Supabase project.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import get_settings


class InvalidAuthToken(Exception):
    """The bearer token is missing, malformed, expired or rejected by Supabase."""


@dataclass(frozen=True)
class AuthenticatedUser:
    provider_id: str  # Supabase auth.users.id
    email: str


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedUser: ...


class SupabaseTokenVerifier:
    def __init__(self, *, base_url: str, anon_key: str) -> None:
        self._url = f"{base_url.rstrip('/')}/auth/v1/user"
        self._anon_key = anon_key

    def verify(self, token: str) -> AuthenticatedUser:
        if not token:
            raise InvalidAuthToken("missing bearer token")
        try:
            response = httpx.get(
                self._url,
                headers={"apikey": self._anon_key, "Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
        except httpx.HTTPError as exc:  # network / timeout — treat as unauthenticated
            raise InvalidAuthToken("auth provider unreachable") from exc
        if response.status_code != 200:
            raise InvalidAuthToken("token rejected by auth provider")

        body = response.json()
        provider_id = body.get("id")
        email = body.get("email")
        if not provider_id or not email:
            raise InvalidAuthToken("auth provider returned no identity")
        return AuthenticatedUser(provider_id=str(provider_id), email=str(email).lower())


class FakeTokenVerifier:
    """Accepts any non-empty token and derives a stable demo identity from it, so
    local dev and tests need no Supabase project. A token of the form
    ``demo:alice@example.com`` pins the email; anything else maps to one user."""

    def verify(self, token: str) -> AuthenticatedUser:
        if not token:
            raise InvalidAuthToken("missing bearer token")
        email = "owner@novatech.example"
        if token.startswith("demo:") and "@" in token:
            email = token.split(":", 1)[1].strip().lower()
        return AuthenticatedUser(provider_id=f"fake-{email}", email=email)


@lru_cache
def get_token_verifier() -> TokenVerifier:
    settings = get_settings()
    if settings.supabase_url and settings.supabase_anon_key:
        return SupabaseTokenVerifier(
            base_url=settings.supabase_url, anon_key=settings.supabase_anon_key
        )
    return FakeTokenVerifier()
