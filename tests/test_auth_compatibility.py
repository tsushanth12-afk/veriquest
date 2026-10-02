"""Generated-key tests of production auth, with controlled HTTP JWKS transport.

Run: .venv/Scripts/python.exe -B -m unittest discover -s tests -p test_auth_compatibility.py -v
No real accounts, stored signing keys, DB connection or listening server.
"""
import asyncio
import base64
import copy
import json
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import httpx
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core import security
from app.core.config import Settings, get_settings
from app.core.errors import AppError


def configured(**kwargs):
    return Settings(_env_file=None, database_url='postgresql://vq_api:unit-only@127.0.0.1:1/postgres', **kwargs)


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def number(value, length=None):
    return b64(value.to_bytes(length or (value.bit_length() + 7) // 8, "big"))


def public(key, algorithm, kid):
    n = key.public_key().public_numbers()
    fields = {"kty": "EC", "crv": "P-256", "x": number(n.x, 32), "y": number(n.y, 32)} if algorithm == "ES256" else {"kty": "RSA", "n": number(n.n), "e": number(n.e)}
    return dict(fields, alg=algorithm, kid=kid, use="sig", key_ops=["verify"])


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ec = ec.generate_private_key(ec.SECP256R1())
        cls.other_ec = ec.generate_private_key(ec.SECP256R1())
        cls.rsa = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.settings = configured()
        self.document = {"keys": [public(self.ec, "ES256", "ec-one")]}
        self.calls = []
        self.clock = 1000.0
        self.status = 200
        self.body = None
        self.failure = None
        security._jwks_cache.clear()
        original_client = httpx.Client

        def transport(request):
            self.calls.append(str(request.url))
            if self.failure:
                raise self.failure
            if self.body is not None:
                return httpx.Response(self.status, content=self.body)
            return httpx.Response(self.status, json=self.document)

        def client(**kwargs):
            self.assertFalse(kwargs["follow_redirects"])
            self.assertFalse(kwargs["trust_env"])
            self.assertEqual(kwargs["timeout"].read, 5)
            return original_client(transport=httpx.MockTransport(transport), **kwargs)

        self.http_patch = patch.object(security.httpx, "Client", client)
        self.clock_patch = patch.object(security.time, "monotonic", lambda: self.clock)
        self.http_patch.start()
        self.clock_patch.start()
        self.addCleanup(self.http_patch.stop)
        self.addCleanup(self.clock_patch.stop)
        self.addCleanup(security._jwks_cache.clear)

    def claims(self):
        return {"iss": self.settings.jwt_issuer, "aud": "authenticated", "exp": int(time.time()) + 300,
                "sub": "11111111-1111-4111-8111-111111111111", "role": "authenticated"}

    def token(self, claims=None, key=None, algorithm="ES256", kid="ec-one"):
        return jwt.encode(self.claims() if claims is None else claims, key or self.ec, algorithm=algorithm, headers={"kid": kid})

    def reject(self, token, settings=None):
        with self.assertRaises(AppError) as caught:
            security.verify_supabase_jwt(token, settings or self.settings)
        self.assertEqual(caught.exception.status_code, 401)

    def test_valid_es256_and_audience_list(self):
        self.assertEqual(security.verify_supabase_jwt(self.token(), self.settings)["sub"], self.claims()["sub"])
        c = self.claims(); c["aud"] = ["another", "authenticated"]
        self.assertEqual(security.verify_supabase_jwt(self.token(c), self.settings)["aud"], c["aud"])
        self.assertEqual(len(self.calls), 1)

    def test_rs256_explicit_only(self):
        self.document["keys"].append(public(self.rsa, "RS256", "rsa-one"))
        token = self.token(key=self.rsa, algorithm="RS256", kid="rsa-one")
        self.reject(token)
        self.assertEqual(self.calls, [])
        settings = configured(jwt_algorithms="RS256")
        self.assertEqual(security.verify_supabase_jwt(token, settings)["sub"], self.claims()["sub"])
        settings = configured(jwt_algorithms="ES256,RS256")
        self.assertEqual(security.verify_supabase_jwt(token, settings)["sub"], self.claims()["sub"])

    def test_invalid_signature_tampering_and_algorithms(self):
        self.reject(self.token(key=self.other_ec))
        token = self.token().split(".")
        c = self.claims(); c["sub"] = "22222222-2222-4222-8222-222222222222"
        token[1] = b64(json.dumps(c).encode())
        self.reject(".".join(token))
        for alg in ("none", "HS256", "ES384", "RS512"):
            with self.subTest(algorithm=alg):
                header = b64(json.dumps({"alg": alg, "kid": "ec-one"}).encode())
                self.reject(header + "." + b64(json.dumps(self.claims()).encode()) + ".AA")
        self.reject(self.token(key="temporary-test-secret", algorithm="HS256"))

    def test_expiry_claims(self):
        for value in (None, True, "9999999999", 1.5, {}, [], -1, int(time.time()) - 120):
            with self.subTest(value=value):
                c = self.claims(); c["exp"] = value; self.reject(self.token(c))
        c = self.claims(); del c["exp"]; self.reject(self.token(c))

    def test_issuer_audience_subject_claims(self):
        values = {"iss": [None, "", self.settings.jwt_issuer + "/", "http://wrong/auth/v1", [], 123],
                  "aud": [None, "", "wrong", [], ["authenticated", 1], ["authenticated", ""]],
                  "sub": [None, "", " ", 123, [], "not-uuid", "00000000-0000-0000-0000-000000000000"]}
        for field, bad in values.items():
            for value in bad:
                with self.subTest(field=field, value=value):
                    c = self.claims(); c[field] = value; self.reject(self.token(c))
            c = self.claims(); del c[field]; self.reject(self.token(c))

    def test_nbf_and_clock_tolerance(self):
        c = self.claims(); c["nbf"] = int(time.time()) + 120; self.reject(self.token(c))
        for value in (None, True, "1", 1.5, [], {}):
            with self.subTest(value=value):
                c = self.claims(); c["nbf"] = value; self.reject(self.token(c))
        c = self.claims(); c["nbf"] = int(time.time()) + 10
        security.verify_supabase_jwt(self.token(c), self.settings)
        c = self.claims(); c["exp"] = int(time.time()) - 10
        security.verify_supabase_jwt(self.token(c), self.settings)

    def test_key_metadata_and_material(self):
        changes = [{"alg": "RS256"}, {"alg": None}, {"kty": "RSA"}, {"crv": "P-384"},
                   {"use": "enc"}, {"key_ops": ["sign"]}, {"key_ops": "verify"},
                   {"key_ops": ["verify", "sign"]}, {"x": None}, {"y": "!"},
                   {"x": "AA"}, {"x": number(0, 32), "y": number(0, 32)}, {"d": "AA"}]
        base = copy.deepcopy(self.document)
        for change in changes:
            with self.subTest(change=change):
                security._jwks_cache.clear(); self.document = copy.deepcopy(base)
                self.document["keys"][0].update(change); self.reject(self.token())
        for field in ("x", "y", "alg", "kty", "crv"):
            security._jwks_cache.clear(); self.document = copy.deepcopy(base)
            del self.document["keys"][0][field]; self.reject(self.token())

    def test_rsa_material(self):
        self.settings = configured(jwt_algorithms="RS256")
        self.document = {"keys": [public(self.rsa, "RS256", "rsa-one")]}
        token = self.token(key=self.rsa, algorithm="RS256", kid="rsa-one")
        for change in ({"n": None}, {"e": "Ag"}, {"n": "AQ"}, {"kty": "EC"}):
            with self.subTest(change=change):
                security._jwks_cache.clear()
                self.document = {"keys": [dict(public(self.rsa, "RS256", "rsa-one"), **change)]}
                self.reject(token)

    def test_malformed_jwks_and_duplicate_ids(self):
        key = self.document["keys"][0]
        for document in (None, [], {}, {"keys": []}, {"keys": "bad"}, {"keys": [None]},
                         {"keys": [{"kid": 1}]}, {"keys": [key, key]}, {"keys": [key] * 65}):
            with self.subTest(document_type=type(document).__name__):
                security._jwks_cache.clear(); self.document = document; self.reject(self.token())
        for body in (b"not json", b"x" * 65537):
            security._jwks_cache.clear(); self.body = body; self.reject(self.token())

    def test_transport_failure_cooldown(self):
        for status in (302, 404, 500):
            security._jwks_cache.clear(); self.status = status; self.reject(self.token())
        security._jwks_cache.clear(); self.status = 200
        self.failure = httpx.ConnectError("controlled failure")
        before = len(self.calls)
        for _ in range(10): self.reject(self.token())
        self.assertEqual(len(self.calls) - before, 1)
        self.clock += 31; self.reject(self.token())
        self.assertEqual(len(self.calls) - before, 2)

    def test_cache_endpoint_and_configuration_isolation(self):
        token = self.token(); security.verify_supabase_jwt(token, self.settings)
        for change in ({"jwt_jwks_url": "http://other.local/keys"}, {"jwt_algorithms": "ES256,RS256"}):
            settings = configured(**change)
            security.verify_supabase_jwt(token, settings)
        self.assertEqual(len(self.calls), 3)
        self.assertIn("http://other.local/keys", self.calls)
        for change in ({"jwt_issuer": "http://other.local/auth"}, {"jwt_audience": "other"}):
            settings = configured(**change)
            self.reject(token, settings)
        self.assertEqual(len(self.calls), 5)

    def test_rotation_and_unknown_kid_bounded_concurrent_refresh(self):
        security.verify_supabase_jwt(self.token(), self.settings)
        for index in range(10): self.reject(self.token(kid=f"unknown-{index}"))
        self.assertEqual(len(self.calls), 1)
        self.clock += 31
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda i: self.reject(self.token(kid=f"unknown-{i}")), range(20)))
        self.assertEqual(len(self.calls), 2)
        self.document = {"keys": [public(self.other_ec, "ES256", "rotated")]}
        self.clock += 31
        result = security.verify_supabase_jwt(self.token(key=self.other_ec, kid="rotated"), self.settings)
        self.assertEqual(result["sub"], self.claims()["sub"])
        self.assertEqual(len(self.calls), 3)
        self.clock += 3601
        security.verify_supabase_jwt(self.token(key=self.other_ec, kid="rotated"), self.settings)
        self.assertEqual(len(self.calls), 4)

    def test_configuration_fail_closed(self):
        for algorithms in ("", "HS256", "ES256,", "ES256,ES256", "ES256, RS256", "none"):
            with self.assertRaises(ValidationError): configured(jwt_algorithms=algorithms)
        for values in ({"jwt_issuer": ""}, {"jwt_jwks_url": "file:///keys"},
                       {"jwt_jwks_url": "http://user:password@local/keys"},
                       {"jwt_audience": ""}, {"jwt_clock_tolerance_seconds": 61}):
            with self.assertRaises(ValidationError): configured(**values)

    def test_headers_and_invalid_identity_types(self):
        payload = b64(json.dumps(self.claims()).encode())
        for header in ({"alg": "ES256"}, {"alg": "ES256", "kid": ""},
                       {"alg": "ES256", "kid": 12}, {"alg": ["ES256"], "kid": "ec-one"},
                       {"alg": "ES256", "kid": "ec-one", "crit": ["unknown"]}):
            with self.subTest(header=header):
                self.reject(b64(json.dumps(header).encode()) + "." + payload + ".AA")
        for claim in ("iat", "email", "role"):
            c = self.claims(); c[claim] = []
            self.reject(self.token(c))
        self.reject("not-a-token")
        self.reject("x" * 16385)

    def test_expired_cache_failure_and_refresh_recovery(self):
        security.verify_supabase_jwt(self.token(), self.settings)
        self.clock += 3601
        self.failure = httpx.ReadTimeout("controlled timeout")
        before = len(self.calls)
        for _ in range(5): self.reject(self.token())
        self.assertEqual(len(self.calls) - before, 1)
        self.failure = None
        self.clock += 31
        security.verify_supabase_jwt(self.token(), self.settings)
        self.assertEqual(len(self.calls) - before, 2)

    def test_actual_dependencies_and_http_routes(self):
        app = FastAPI()
        app.dependency_overrides[get_settings] = lambda: self.settings
        @app.get("/required")
        async def required(user=Depends(security.get_current_user)):
            return {"id": user.user_id}
        @app.get("/optional")
        async def optional(user=Depends(security.get_optional_user)):
            return {"id": user.user_id if user else None}
        with TestClient(app) as client:
            self.assertEqual(client.get("/optional").json(), {"id": None})
            self.assertEqual(client.get("/required").status_code, 401)
            for header in ("", "Basic abc", "Bearer", "Bearer bad", "Bearer a b"):
                for path in ("/required", "/optional"):
                    self.assertEqual(client.get(path, headers={"authorization": header}).status_code, 401)
            for path in ("/required", "/optional"):
                response = client.get(path, headers={"authorization": "Bearer " + self.token()})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["id"], self.claims()["sub"])
            self.assertEqual(client.get("/optional", headers=[("authorization", "Bearer " + self.token()), ("authorization", "Bearer " + self.token())]).status_code, 401)

    def test_async_dependency_offloads_verifier(self):
        original = security.verify_supabase_jwt
        threads = []
        def verifier(*args):
            threads.append(threading.get_ident()); return original(*args)
        async def execute():
            event_loop_thread = threading.get_ident()
            request = Request({"type": "http", "headers": [(b"authorization", ("Bearer " + self.token()).encode())]})
            with patch.object(security, "verify_supabase_jwt", verifier):
                user = await security.get_current_user(request, self.settings)
            self.assertEqual(user.user_id, self.claims()["sub"])
            self.assertNotEqual(threads[0], event_loop_thread)
        asyncio.run(execute())


if __name__ == "__main__":
    unittest.main()
