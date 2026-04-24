import time
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from core.auth import verify_jwt
from core.config import API_AUDIENCE, BETTER_AUTH_URL


def _make_ed25519_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """テスト用の Ed25519 鍵ペアを生成"""
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def _sign_token(private_key: Ed25519PrivateKey, payload: dict[str, Any]) -> str:
    """Ed25519 秘密鍵で JWT を署名"""
    return jwt.encode(payload, private_key, algorithm="EdDSA")


def _make_valid_payload(sub: str = "test-user-123", **overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": now,
        "exp": now + 3600,
        "aud": API_AUDIENCE,
        "iss": BETTER_AUTH_URL,
    }
    payload.update(overrides)
    return payload


class TestVerifyJwt:
    """core.auth.verify_jwt のユニットテスト"""

    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey

    def setup_method(self) -> None:
        self.private_key, self.public_key = _make_ed25519_keypair()

    def _patch_jwks(self) -> Any:
        """jwks_client.get_signing_key_from_jwt をパッチして公開鍵を返す"""
        mock_signing_key = MagicMock()
        mock_signing_key.key = self.public_key
        return patch("core.auth.jwks_client.get_signing_key_from_jwt", return_value=mock_signing_key)

    def test_valid_token_returns_payload(self) -> None:
        payload = _make_valid_payload()
        token = _sign_token(self.private_key, payload)

        with self._patch_jwks():
            result = verify_jwt(token)

        assert result["sub"] == "test-user-123"

    def test_expired_token_raises(self) -> None:
        payload = _make_valid_payload(exp=int(time.time()) - 100)
        token = _sign_token(self.private_key, payload)

        with self._patch_jwks(), pytest.raises(ValueError, match="(?i)expired"):
            verify_jwt(token)

    def test_invalid_signature_raises(self) -> None:
        payload = _make_valid_payload()
        token = _sign_token(self.private_key, payload)

        # 別の鍵ペアの公開鍵を返す → 署名不一致
        _, wrong_public_key = _make_ed25519_keypair()
        mock_signing_key = MagicMock()
        mock_signing_key.key = wrong_public_key

        with (
            patch("core.auth.jwks_client.get_signing_key_from_jwt", return_value=mock_signing_key),
            pytest.raises(ValueError, match="(?i)invalid"),
        ):
            verify_jwt(token)

    def test_wrong_audience_raises(self) -> None:
        payload = _make_valid_payload(aud="https://wrong-audience.example.com")
        token = _sign_token(self.private_key, payload)

        with self._patch_jwks(), pytest.raises(ValueError, match="(?i)invalid"):
            verify_jwt(token)

    def test_wrong_issuer_raises(self) -> None:
        payload = _make_valid_payload(iss="https://wrong-issuer.example.com")
        token = _sign_token(self.private_key, payload)

        with self._patch_jwks(), pytest.raises(ValueError, match="(?i)invalid"):
            verify_jwt(token)
