from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jose import jwt
from jose.backends.cryptography_backend import CryptographyECKey
from jose.constants import ALGORITHMS

from app.core import security


def _generate_es256_keypair_and_jwks(kid: str):
    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_jwk_key = CryptographyECKey(private_key.public_key(), ALGORITHMS.ES256)
    public_jwk = public_jwk_key.to_dict()
    public_jwk["kid"] = kid
    return pem, {"keys": [public_jwk]}


async def test_es256_token_verified_via_jwks():
    kid = "test-signing-key"
    private_pem, jwks = _generate_es256_keypair_and_jwks(kid)

    token = jwt.encode(
        {"sub": "abc-123", "aud": "authenticated"},
        private_pem,
        algorithm="ES256",
        headers={"kid": kid},
    )

    security._jwks_cache = None
    with patch.object(security, "_fetch_jwks", return_value=jwks) as mock_fetch:
        payload = security.decode_supabase_jwt(token)

    assert payload["sub"] == "abc-123"
    assert mock_fetch.called


async def test_es256_token_with_unknown_kid_is_rejected():
    kid = "real-key"
    private_pem, jwks = _generate_es256_keypair_and_jwks(kid)

    token = jwt.encode(
        {"sub": "abc-123", "aud": "authenticated"},
        private_pem,
        algorithm="ES256",
        headers={"kid": "some-other-kid"},
    )

    security._jwks_cache = None
    with patch.object(security, "_fetch_jwks", return_value=jwks):
        try:
            security.decode_supabase_jwt(token)
            assert False, "expected InvalidTokenError"
        except security.InvalidTokenError:
            pass
