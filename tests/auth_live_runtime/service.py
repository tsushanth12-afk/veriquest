"""Minimal real HTTP auth test service. Never logs request headers or tokens."""
import argparse
import hashlib
import importlib.metadata
import os
import platform
import sys
from pathlib import Path

backend = Path(os.environ.get("VQ_AUTH_BACKEND_PATH", str(Path(__file__).resolve().parents[2] / "backend")))
sys.path.insert(0, str(backend))
from fastapi import Depends, FastAPI, Request
from app.core.config import Settings, get_settings
from app.core.security import get_current_user, get_optional_user, _fetch_jwks, _find_key


def create_app():
    # Authentication-only service deliberately never connects this dummy DB endpoint.
    settings = Settings(_env_file=None, database_url='postgresql://vq_api:unit-only@127.0.0.1:1/postgres')
    app = FastAPI()
    app.dependency_overrides[get_settings] = lambda: settings

    @app.get("/health")
    async def health():
        return {"platform": platform.system(), "issuer": settings.jwt_issuer,
                "jwks_url": settings.jwt_jwks_url,
                "docker_socket_present": Path("/var/run/docker.sock").exists(),
                "source_sha256": hashlib.sha256((backend / "app/core/security.py").read_bytes()).hexdigest(),
                "versions": {name: importlib.metadata.version(name) for name in
                             ("fastapi", "uvicorn", "python-jose", "cryptography", "httpx", "pydantic", "pydantic-settings")}}

    @app.get("/jwks-probe")
    def jwks_probe():
        document = _fetch_jwks(settings.jwt_jwks_url)
        key = document["keys"][0]
        _find_key(document, key["kid"], "ES256")
        return {"compatible": True, "alg": key["alg"], "kty": key["kty"], "crv": key["crv"]}

    @app.get("/required")
    async def required(user=Depends(get_current_user)):
        return {"subject": user.user_id}

    @app.get("/optional")
    async def optional(user=Depends(get_optional_user)):
        return {"subject": user.user_id if user else None}

    wrong = Settings(_env_file=None, database_url=settings.database_url, jwt_issuer=settings.jwt_issuer + "/wrong",
                     jwt_jwks_url=settings.jwt_jwks_url, jwt_algorithms=settings.jwt_algorithms,
                     jwt_audience=settings.jwt_audience)

    @app.get("/wrong-issuer")
    async def wrong_issuer(request: Request):
        user = await get_current_user(request, wrong)
        return {"subject": user.user_id}

    return app


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    uvicorn.run(create_app(), host=args.host, port=args.port, access_log=False, log_level="critical")
