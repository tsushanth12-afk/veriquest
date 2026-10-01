"""Strict configured JWT verification; token-supplied URLs/algorithms are not authority."""
import base64
import json
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, Request
from jose import JWTError, jwt
from jose.exceptions import JWKError
from starlette.concurrency import run_in_threadpool

from .config import Settings, get_settings
from .errors import unauthorized

_JWKS_TTL_SECONDS = 3600
_JWKS_REFRESH_COOLDOWN_SECONDS = 30
_MAX_JWKS_BYTES = 65536
_MAX_CACHE_ENTRIES = 16
_cache_lock = threading.Lock()


@dataclass
class _CacheEntry:
    document: dict | None = None
    fetched_at: float = 0
    attempted_at: float = float("-inf")


_jwks_cache: OrderedDict[tuple, _CacheEntry] = OrderedDict()


def _validate_jwks(document: object) -> dict:
    if not isinstance(document, dict) or not isinstance(document.get("keys"), list) or not 1 <= len(document["keys"]) <= 64:
        raise ValueError("Invalid JWKS document")
    ids = set()
    for key in document["keys"]:
        if not isinstance(key, dict):
            raise ValueError("Invalid JWKS key")
        kid = key.get("kid")
        if not isinstance(kid, str) or not kid or len(kid) > 256 or kid in ids:
            raise ValueError("Invalid or duplicate key ID")
        ids.add(kid)
    return document


def _fetch_jwks(url: str) -> dict:
    # Explicit finite timeout, no redirects and no environment proxy selection.
    deadline = time.monotonic() + 10
    with httpx.Client(timeout=httpx.Timeout(5.0), follow_redirects=False, trust_env=False) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                if time.monotonic() > deadline or len(body) + len(chunk) > _MAX_JWKS_BYTES:
                    raise ValueError("JWKS exceeds size limit")
                body.extend(chunk)
    return _validate_jwks(json.loads(body))


def get_jwks(settings: Settings, *, refresh: bool = False) -> dict:
    identity = (settings.jwt_jwks_url, settings.jwt_issuer, settings.jwt_audience,
                settings.jwt_algorithms, settings.jwt_clock_tolerance_seconds)
    # Serialize fetches so concurrent unknown-kid requests cannot bypass cooldown.
    # Request dependencies call this through the threadpool, not the event loop.
    with _cache_lock:
        entry = _jwks_cache.setdefault(identity, _CacheEntry())
        _jwks_cache.move_to_end(identity)
        while len(_jwks_cache) > _MAX_CACHE_ENTRIES:
            _jwks_cache.popitem(last=False)
        now = time.monotonic()
        fresh = entry.document is not None and now - entry.fetched_at < _JWKS_TTL_SECONDS
        if fresh and not refresh:
            return entry.document
        if now - entry.attempted_at < _JWKS_REFRESH_COOLDOWN_SECONDS:
            if fresh:
                return entry.document
            raise unauthorized("Authentication keys unavailable")
        entry.attempted_at = now
        try:
            document = _validate_jwks(_fetch_jwks(settings.jwt_jwks_url))
        except Exception:
            # Never log response bodies, tokens or potentially sensitive URLs.
            raise unauthorized("Authentication keys unavailable") from None
        entry.document, entry.fetched_at = document, time.monotonic()
        return document


def _material(key: dict, field: str, length: int | None = None) -> bytes:
    value = key.get(field)
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Invalid key material")
    data = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if not data or (length is not None and len(data) != length):
        raise ValueError("Invalid key material")
    return data


def _find_key(document: dict, kid: str, algorithm: str) -> dict | None:
    matches = [key for key in document["keys"] if key["kid"] == kid]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("Ambiguous key")
    key = matches[0]
    if key.get("alg") != algorithm or ("use" in key and key["use"] != "sig"):
        raise ValueError("Incompatible key metadata")
    if "key_ops" in key and key["key_ops"] != ["verify"]:
        raise ValueError("Incompatible key operations")
    if any(field in key for field in ("d", "p", "q", "dp", "dq", "qi", "k")):
        raise ValueError("Expected public asymmetric key")
    if algorithm == "ES256":
        if key.get("kty") != "EC" or key.get("crv") != "P-256":
            raise ValueError("Incompatible EC key")
        _material(key, "x", 32)
        _material(key, "y", 32)
    else:
        if key.get("kty") != "RSA":
            raise ValueError("Incompatible RSA key")
        modulus = int.from_bytes(_material(key, "n"), "big")
        exponent = int.from_bytes(_material(key, "e"), "big")
        if modulus.bit_length() < 2048 or exponent < 3 or exponent % 2 == 0:
            raise ValueError("Invalid RSA key")
    return key


def verify_supabase_jwt(token: str, settings: Settings) -> dict:
    try:
        if not isinstance(token, str) or len(token) > 16384:
            raise ValueError("Invalid token")
        header = jwt.get_unverified_header(token)
        algorithm, kid = header.get("alg"), header.get("kid")
        if algorithm not in settings.jwt_algorithms.split(",") or not isinstance(kid, str) or not kid or len(kid) > 256:
            raise ValueError("Invalid algorithm or key ID")
        if header.get("crit") or header.get("b64") is False:
            raise ValueError("Unsupported JOSE extension")
        key = _find_key(get_jwks(settings), kid, algorithm)
        if key is None:
            key = _find_key(get_jwks(settings, refresh=True), kid, algorithm)
        if key is None:
            raise ValueError("Unknown signing key")
        payload = jwt.decode(
            token, key, algorithms=settings.jwt_algorithms.split(","),
            issuer=settings.jwt_issuer, audience=settings.jwt_audience,
            options={"verify_signature": True, "verify_iss": True, "verify_aud": True,
                     "verify_exp": True, "verify_nbf": True, "verify_sub": True,
                     "require_iss": True, "require_aud": True, "require_exp": True,
                     "require_sub": True, "leeway": settings.jwt_clock_tolerance_seconds},
        )
        if not isinstance(payload["iss"], str) or payload["iss"] != settings.jwt_issuer:
            raise ValueError("Invalid issuer")
        audience = payload["aud"]
        if not (isinstance(audience, str) or (isinstance(audience, list) and audience and all(isinstance(a, str) and a for a in audience))):
            raise ValueError("Invalid audience")
        for claim in ("exp", "nbf", "iat"):
            if claim in payload and (type(payload[claim]) is not int or payload[claim] < 0):
                raise ValueError("Invalid numeric date")
        subject = payload["sub"]
        if not isinstance(subject, str) or str(UUID(subject)) != subject.lower() or UUID(subject).int == 0:
            raise ValueError("Invalid UUID subject")
        for claim in ("email", "role"):
            if claim in payload and not isinstance(payload[claim], str):
                raise ValueError("Invalid identity claim")
        return payload
    except (JWTError, JWKError, ValueError, TypeError, KeyError, OverflowError):
        raise unauthorized("Invalid or expired authentication token") from None


class AuthenticatedUser:
    def __init__(self, user_id: str, email: str | None = None, role: str = "authenticated"):
        self.user_id, self.email, self.role = user_id, email, role

    def __repr__(self) -> str:
        return f"AuthenticatedUser(id={self.user_id})"


async def _authenticate(request: Request, settings: Settings, optional: bool) -> AuthenticatedUser | None:
    headers = request.headers.getlist("authorization")
    if not headers and optional:
        return None
    if len(headers) != 1:
        raise unauthorized("Missing or malformed Authorization header")
    parts = headers[0].split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise unauthorized("Malformed Authorization header")
    payload = await run_in_threadpool(verify_supabase_jwt, parts[1], settings)
    return AuthenticatedUser(payload["sub"], payload.get("email"), payload.get("role", "authenticated"))


async def get_current_user(request: Request, settings: Settings = Depends(get_settings)) -> AuthenticatedUser:
    return await _authenticate(request, settings, False)


async def get_optional_user(request: Request, settings: Settings = Depends(get_settings)) -> AuthenticatedUser | None:
    return await _authenticate(request, settings, True)


async def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    # Existing route-level database role checks remain authoritative.
    return user
