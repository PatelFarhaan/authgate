import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import settings


class JWTHandler:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.kid = None

    def initialize(self):
        keys_dir = settings.JWT_KEYS_DIR
        os.makedirs(keys_dir, exist_ok=True)

        private_path = os.path.join(keys_dir, "private.pem")
        public_path = os.path.join(keys_dir, "public.pem")

        if os.path.exists(private_path) and os.path.exists(public_path):
            with open(private_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            with open(public_path, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(), backend=default_backend()
                )
        else:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )
            self.public_key = self.private_key.public_key()

            with open(private_path, "wb") as f:
                f.write(
                    self.private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
            with open(public_path, "wb") as f:
                f.write(
                    self.public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                )
            os.chmod(private_path, 0o600)

        pub_der = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.kid = (
            base64.urlsafe_b64encode(hashlib.sha256(pub_der).digest()[:8])
            .decode()
            .rstrip("=")
        )

    def create_token(self, user_id: str, email: str, name: str, provider: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "name": name,
            "provider": provider,
            "iat": now,
            "exp": now + timedelta(hours=settings.JWT_EXPIRY_HOURS),
            "iss": "authgate",
        }
        return jwt.encode(
            payload, self.private_key, algorithm="RS256", headers={"kid": self.kid}
        )

    def verify_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(
                token, self.public_key, algorithms=["RS256"], issuer="authgate"
            )
        except jwt.PyJWTError:
            return None

    def create_state_token(self, redirect_url: str, provider: str = "") -> str:
        payload = {
            "redirect_url": redirect_url,
            "provider": provider,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    def verify_state_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None

    def get_jwks(self) -> dict:
        numbers = self.public_key.public_numbers()
        e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, byteorder="big")
        n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, byteorder="big")

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self.kid,
                    "n": base64.urlsafe_b64encode(n).decode().rstrip("="),
                    "e": base64.urlsafe_b64encode(e).decode().rstrip("="),
                }
            ]
        }


jwt_handler = JWTHandler()
