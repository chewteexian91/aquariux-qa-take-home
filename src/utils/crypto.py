"""Encrypt and decrypt test credentials with Fernet (AES + HMAC-SHA256).

The key is read from the AQX_ENCRYPTION_KEY environment variable, which is
loaded from the git-ignored .env file at the project root.

Usage:
    python -m src.utils.crypto genkey               # print a new key for .env
    python -m src.utils.crypto encrypt "<password>"  # print the encrypted value for user.json
"""
import os
import sys

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

KEY_ENV_VAR = "AQX_ENCRYPTION_KEY"


def _fernet() -> Fernet:
    load_dotenv()
    key = os.getenv(KEY_ENV_VAR)
    if not key:
        raise RuntimeError(
            f"{KEY_ENV_VAR} is missing. Add it to .env (see .env.example) "
            f"or generate one with: python -m src.utils.crypto genkey"
        )
    return Fernet(key.encode())


def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError(
            f"Could not decrypt value. Check that {KEY_ENV_VAR} matches the key "
            f"used to encrypt it."
        ) from exc


def _main(argv: list[str]) -> None:
    if argv[:1] == ["genkey"]:
        print(Fernet.generate_key().decode())
    elif argv[:1] == ["encrypt"] and len(argv) == 2:
        print(encrypt(argv[1]))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    _main(sys.argv[1:])
