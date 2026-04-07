"""SharedLink model for secure playlist sharing."""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Hash a password with PBKDF2-HMAC-SHA256.

    Returns ``(hex_hash, hex_salt)``.  When *salt* is ``None`` a new
    16-byte random salt is generated.
    """
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations=100_000)
    return dk.hex(), salt.hex()


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """Verify *password* against a stored hash + salt pair."""
    salt = bytes.fromhex(stored_salt)
    computed, _ = _hash_password(password, salt)
    return secrets.compare_digest(computed, stored_hash)


@dataclass
class SharedLink:
    """A shareable link to a hosted playlist.

    Each link carries a unique token, optional password protection, an
    expiry timestamp, and access-tracking counters.
    """

    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    label: str = ""
    password_hash: str = ""
    password_salt: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    access_count: int = 0
    last_accessed_at: datetime | None = None
    is_active: bool = True
    groups_filter: list[str] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.expires_at, str):
            self.expires_at = datetime.fromisoformat(self.expires_at)
        if isinstance(self.last_accessed_at, str):
            self.last_accessed_at = datetime.fromisoformat(self.last_accessed_at)

    # ------------------------------------------------------------------
    # Password helpers
    # ------------------------------------------------------------------

    @property
    def has_password(self) -> bool:
        return bool(self.password_hash)

    def set_password(self, password: str) -> None:
        """Hash and store a password for this link."""
        self.password_hash, self.password_salt = _hash_password(password)

    def check_password(self, password: str) -> bool:
        """Return ``True`` if *password* matches the stored hash."""
        if not self.has_password:
            return True
        return verify_password(password, self.password_hash, self.password_salt)

    # ------------------------------------------------------------------
    # Expiry / validity
    # ------------------------------------------------------------------

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """A link is valid when active and not expired."""
        return self.is_active and not self.is_expired

    # ------------------------------------------------------------------
    # Access tracking
    # ------------------------------------------------------------------

    def record_access(self) -> None:
        """Increment access count and update last-accessed timestamp."""
        self.access_count += 1
        self.last_accessed_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "label": self.label,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed_at": (
                self.last_accessed_at.isoformat() if self.last_accessed_at else None
            ),
            "is_active": self.is_active,
            "groups_filter": self.groups_filter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SharedLink:
        return cls(
            token=data["token"],
            label=data.get("label", ""),
            password_hash=data.get("password_hash", ""),
            password_salt=data.get("password_salt", ""),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            expires_at=data.get("expires_at"),
            access_count=data.get("access_count", 0),
            last_accessed_at=data.get("last_accessed_at"),
            is_active=data.get("is_active", True),
            groups_filter=data.get("groups_filter"),
        )
