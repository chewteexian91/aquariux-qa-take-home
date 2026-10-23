import json
from pathlib import Path

from src.models.User import User
from src.utils.crypto import decrypt

USER_FILE = Path(__file__).resolve().parents[1] / "test_data" / "user.json"


def get_user(role: str) -> User:
    """Load a test user by role from user.json, with the password decrypted."""
    users = json.loads(USER_FILE.read_text())
    if role not in users:
        raise KeyError(f"No user with role '{role}' in {USER_FILE.name}. Available: {list(users)}")
    entry = users[role]
    return User(role=role, username=entry["username"], password=decrypt(entry["password"]))
