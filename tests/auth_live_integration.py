"""Opt-in live test: creates/deletes exactly one disposable LOCAL Auth account.

Secrets are captured in memory, never command arguments/environment/files/output.
Fixed local API and local project container names deliberately prohibit hosted targets.
Run explicitly with project venv Python; requires local Docker and existing Supabase.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
from jose import jwt

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:54321"
ISSUER = API + "/auth/v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker", required=True)
    args = parser.parse_args()
    suffix = uuid4().hex[:12]
    container = "vq-auth-live-" + suffix
    image = container + ":test"
    user_id = None
    host = None
    created_container = False
    image_created = False
    result = {"assertions": 0, "cases": [], "cleanup": {}, "failed": False}
    admin = None

    def check(condition, name):
        if not condition:
            raise AssertionError(name)  # Names never contain secrets or response bodies.
        result["assertions"] += 1

    def docker(*command, timeout=120):
        proc = subprocess.run([args.docker, *command], capture_output=True, text=True, timeout=timeout)
        if proc.returncode:
            raise RuntimeError("Docker " + command[0] + " failed; exit " + str(proc.returncode))
        return proc.stdout

    def await_service(base):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                r = httpx.get(base + "/health", timeout=2, trust_env=False)
                if r.status_code == 200:
                    return r.json()
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        raise RuntimeError("Temporary HTTP service startup timeout")

    def exercise(base, token, subject, context):
        # Tamper payload, preserving the original signature: not just malformed JWT syntax.
        parts = token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        payload["sub"] = str(uuid4())
        parts[1] = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        tampered = ".".join(parts)
        cases = [("real-required", "/required", "Bearer " + token, 200, subject),
                 ("real-optional", "/optional", "Bearer " + token, 200, subject),
                 ("absent-required", "/required", None, 401, None),
                 ("absent-optional", "/optional", None, 200, None),
                 ("malformed-required", "/required", "Basic invalid", 401, None),
                 ("malformed-optional", "/optional", "Basic invalid", 401, None),
                 ("empty-required", "/required", "", 401, None),
                 ("empty-optional", "/optional", "", 401, None),
                 ("tampered-required", "/required", "Bearer " + tampered, 401, None),
                 ("tampered-optional", "/optional", "Bearer " + tampered, 401, None),
                 ("wrong-issuer", "/wrong-issuer", "Bearer " + token, 401, None)]
        with httpx.Client(timeout=20, trust_env=False) as client:
            for name, path, authorization, expected, expected_subject in cases:
                headers = {} if authorization is None else {"authorization": authorization}
                response = client.get(base + path, headers=headers)
                result["cases"].append({"context": context, "case": name, "status": response.status_code})
                check(response.status_code == expected, context + " " + name + " status")
                if expected == 200:
                    check(response.json().get("subject") == expected_subject, context + " " + name + " subject")

    with httpx.Client(base_url=API, timeout=15, trust_env=False) as auth:
        try:
            check(auth.get("/auth/v1/health").status_code == 200, "Local Auth healthy")
            metadata = json.loads(docker("inspect", "supabase_kong_veriquest-local-test"))[0]
            env = dict(item.split("=", 1) for item in metadata["Config"]["Env"])
            gateway = docker("exec", "supabase_kong_veriquest-local-test", "cat", env["KONG_DECLARATIVE_CONFIG"])
            candidates = re.findall(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", gateway)
            keys = {}
            for candidate in candidates:
                role = jwt.get_unverified_claims(candidate).get("role")
                if role in {"anon", "service_role"}:
                    keys[role] = candidate
            check(set(keys) == {"anon", "service_role"}, "Local API credentials privately acquired")
            admin = {"apikey": keys["service_role"], "authorization": "Bearer " + keys["service_role"]}
            public = {"apikey": keys["anon"]}
            del gateway, candidates, metadata, env

            # Build before account creation so a failed image build leaves no test account.
            docker("build", "--quiet", "-t", image, str(ROOT / "tests/auth_live_runtime"), timeout=300)
            image_created = True
            result["image_build_exit"] = 0
            password = secrets.token_urlsafe(36)
            email = "vq-auth-live-" + suffix + "@example.com"
            create = auth.post("/auth/v1/admin/users", headers=admin,
                               json={"email": email, "password": password, "email_confirm": True})
            result["account_create_status"] = create.status_code
            if create.status_code in (200, 201):
                user_id = create.json()["id"]  # Retain immediately for finally cleanup.
            check(user_id is not None, "Disposable account creation")
            signed = auth.post("/auth/v1/token?grant_type=password", headers=public,
                               json={"email": email, "password": password})
            result["sign_in_status"] = signed.status_code
            check(signed.status_code == 200, "Actual password sign-in")
            session = signed.json()
            token = session["access_token"]
            check(session["user"]["id"] == user_id, "Auth sign-in identity")
            del password, email, signed, session, create

            # Decoded header/claims are observations only until HTTP production validation succeeds.
            header = jwt.get_unverified_header(token)
            claims = jwt.get_unverified_claims(token)
            check(header.get("alg") == "ES256", "Issued token algorithm observation")
            check(claims.get("iss") == ISSUER, "Issued token issuer observation")
            del header, claims

            bound = socket.socket()
            bound.bind(("127.0.0.1", 0))
            port = bound.getsockname()[1]
            # Pass owned bound socket to Uvicorn in the same process thread, avoiding port races.
            import threading
            import uvicorn
            sys.path.insert(0, str(ROOT / "tests/auth_live_runtime"))
            from service import create_app
            server = uvicorn.Server(uvicorn.Config(create_app(), access_log=False, log_level="critical"))
            thread = threading.Thread(target=lambda: server.run(sockets=[bound]), daemon=True)
            host = (server, thread, bound, port)
            thread.start()
            base = "http://127.0.0.1:" + str(port)
            host_health = await_service(base)
            result["host"] = {"port": port, **host_health}
            exercise(base, token, user_id, "host")

            # Only public configuration in Docker args/environment; token travels in HTTP memory.
            jwks_url = "http://host.docker.internal:54321/auth/v1/.well-known/jwks.json"
            created_container = True  # Clean up even if Docker creates a container then startup fails.
            docker("run", "-d", "--name", container, "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges:true", "--memory=256m", "--cpus=1", "--pids-limit=64",
                   "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "-p", "127.0.0.1::8080",
                   "--mount", "type=bind,source=" + str(ROOT / "backend") + ",target=/app/backend,readonly",
                   "-e", "JWT_ISSUER=" + ISSUER, "-e", "JWT_JWKS_URL=" + jwks_url,
                   "-e", "JWT_ALGORITHMS=ES256", image)
            info = json.loads(docker("inspect", container))[0]
            container_port = int(info["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"])
            cbase = "http://127.0.0.1:" + str(container_port)
            container_health = await_service(cbase)
            result["container"] = {"port": container_port, **container_health}
            check(container_health["platform"] == "Linux", "Real Linux container")
            check(not container_health["docker_socket_present"], "No Docker socket inside container")
            check(container_health["issuer"] == ISSUER, "Container issuer unchanged")
            check(container_health["source_sha256"] == host_health["source_sha256"], "Same production source in container")
            probe = httpx.get(cbase + "/jwks-probe", timeout=20, trust_env=False)
            result["container_jwks_probe_status"] = probe.status_code
            check(probe.status_code == 200 and probe.json().get("compatible") is True, "Observed container JWKS reachability")
            exercise(cbase, token, user_id, "linux-container")
            del token
        except Exception as error:
            result["failed"] = True
            result["failure_type"] = type(error).__name__
            # Only controlled exception messages; never emit HTTP/debug response material.
            if isinstance(error, AssertionError): result["failed_assertion"] = str(error)
        finally:
            if host:
                server, thread, bound, port = host
                server.should_exit = True
                thread.join(timeout=10)
                bound.close()
                result["cleanup"]["host_service_stopped"] = not thread.is_alive()
            if created_container:
                try:
                    docker("rm", "-f", container)
                    result["cleanup"]["container_removed"] = True
                except Exception: result["cleanup"]["container_removed"] = False
            if image_created:
                proc = subprocess.run([args.docker, "image", "rm", image], capture_output=True, text=True)
                result["cleanup"]["temporary_image_removed"] = proc.returncode == 0
            if user_id:
                try:
                    deletion = auth.delete("/auth/v1/admin/users/" + user_id, headers=admin)
                    result["cleanup"]["account_delete_status"] = deletion.status_code
                    verification = auth.get("/auth/v1/admin/users/" + user_id, headers=admin)
                    result["cleanup"]["account_absence_status"] = verification.status_code
                    result["cleanup"]["account_removed"] = deletion.status_code in (200, 204) and verification.status_code == 404
                except Exception: result["cleanup"]["account_removed"] = False
            result["cleanup"]["existing_supabase_health_status"] = auth.get("/auth/v1/health").status_code
    cleanup_failed = any(value is False for value in result["cleanup"].values())
    print(json.dumps(result, indent=2))
    return 1 if result["failed"] or cleanup_failed else 0


if __name__ == "__main__":
    sys.exit(main())
