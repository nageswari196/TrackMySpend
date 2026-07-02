"""
Authentication helpers.

Upgrade notes:
- Old scheme: unsalted SHA-256 (vulnerable to rainbow-table attacks).
- New scheme: bcrypt, which is salted and deliberately slow (resists brute force).
- Migration: existing users still have a SHA-256 hash in the DB. On their next
  successful login we detect that, re-hash their password with bcrypt, and
  overwrite the stored value -- transparent to the user, no forced reset.
"""
import hashlib
import bcrypt

def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def hash_password(password: str) -> str:
    """Bcrypt hash for new passwords (includes its own random salt)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def is_bcrypt_hash(value: str) -> bool:
    return value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify against either a bcrypt hash (new) or a legacy sha256 hash (old)."""
    if is_bcrypt_hash(stored_hash):
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except ValueError:
            return False
    # legacy fallback
    return _sha256(password) == stored_hash
