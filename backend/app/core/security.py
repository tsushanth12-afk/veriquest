# ==========================================================================
# VeriQuest Backend — JWKS RS256 JWT Verification & Auth Dependencies
#
# Method: Asymmetric RS256 verification via JWKS
# Source: Supabase official docs (2025-2026) — asymmetric signing is
#         the default for projects created since late 2025.
# JWKS URL: {SUPABASE_URL}/auth/v1/.well-known/jwks.json
#
# The backend fetches public keys from Supabase's JWKS endpoint,
# caches them (TTL 1 hour), and verifies JWTs locally — no network
# roundtrip per request, no shared secret needed.
# ==========================================================================

import time
import logging
from typing import Optional
import httpx
from fastapi import Depends, Request
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode

from .config import get_settings, Settings
from .errors import unauthorized, forbidden

logger = logging.getLogger("veriquest.security")


# ======================================================================
# JWKS Cache
# ======================================================================

_jwks_cache: dict | None = None
_jwks_cache_time: float = 0
_JWKS_TTL_SECONDS = 3600  # Re-fetch keys every hour


def _fetch_jwks(supabase_url: str) -> dict:
    """Fetch JSON Web Key Set from Supabase's well-known endpoint."""
    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(jwks_url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
        raise unauthorized("Unable to verify authentication (JWKS fetch failed)")


def get_jwks(supabase_url: str) -> dict:
    """Get JWKS with caching (TTL = 1 hour)."""
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if _jwks_cache is not None and (now - _jwks_cache_time) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    _jwks_cache = _fetch_jwks(supabase_url)
    _jwks_cache_time = now
    logger.info("JWKS cache refreshed")
    return _jwks_cache


def _find_key(jwks: dict, kid: str) -> dict | None:
    """Find a key in the JWKS by kid (Key ID)."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


# ======================================================================
# Authenticated User
# ======================================================================

class AuthenticatedUser:
    """Represents a verified Supabase user from JWT claims."""

    def __init__(self, user_id: str, email: str | None = None, role: str = "authenticated"):
        self.user_id = user_id
        self.email = email
        self.role = role

    def __repr__(self) -> str:
        return f"AuthenticatedUser(id={self.user_id}, email={self.email})"


# ======================================================================
# JWT Verification
# ======================================================================

def verify_supabase_jwt(token: str, settings: Settings) -> dict:
    """
    Verify a Supabase JWT using JWKS-based RS256 asymmetric verification.

    Steps:
    1. Decode JWT header (unverified) to get `kid`
    2. Look up matching public key in cached JWKS
    3. Verify signature (RS256), audience, and expiry
    4. Return decoded payload
    """
    try:
        # 1. Get unverified header to find kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise unauthorized("Token missing key ID (kid)")

        # 2. Get matching key from JWKS
        jwks_data = get_jwks(settings.supabase_url)
        key_data = _find_key(jwks_data, kid)

        if key_data is None:
            # Key not found — maybe keys rotated. Force refresh and retry once.
            global _jwks_cache_time
            _jwks_cache_time = 0
            jwks_data = get_jwks(settings.supabase_url)
            key_data = _find_key(jwks_data, kid)

            if key_data is None:
                raise unauthorized("Token signed with unknown key")

        # 3. Verify token
        payload = jwt.decode(
            token,
            key_data,
            algorithms=["RS256"],
            audience="authenticated",
            options={
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": False,  # Supabase issuer varies by project
            },
        )

        return payload

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise unauthorized("Invalid or expired authentication token")


# ======================================================================
# FastAPI Dependencies
# ======================================================================

async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """
    FastAPI dependency: extract and verify Supabase JWT from the
    Authorization header. Returns AuthenticatedUser.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise unauthorized("Missing or malformed Authorization header")

    token = auth_header[7:]  # Strip "Bearer "
    if not token:
        raise unauthorized("Empty token")

    payload = verify_supabase_jwt(token, settings)

    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized("Token missing subject claim")

    return AuthenticatedUser(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )


async def get_optional_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Optional[AuthenticatedUser]:
    """
    FastAPI dependency: extract and verify Supabase JWT if present.
    Returns None if no Authorization header, allowing anonymous browsing.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    if not token:
        return None

    payload = verify_supabase_jwt(token, settings)
    user_id = payload.get("sub")
    if not user_id:
        return None

    return AuthenticatedUser(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    FastAPI dependency: require admin role.
    The actual admin check queries user_roles table in the database.
    """
    # Note: Real admin verification happens at the route handler level
    # by querying user_roles table. This dependency is a marker that
    # triggers at least authentication. Individual admin routes verify
    # the role via DB query.
    return user
