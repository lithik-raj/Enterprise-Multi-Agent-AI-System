"""
core/auth.py

Authentication and Role-Based Access Control (RBAC) module for TalentGraph.
Supports standard Roles:
  - admin: Manage company settings, users, retention rules, usage & billing
  - recruiter: Create jobs, upload resumes, review shortlist, approve/reject, export
  - hiring_manager: View shortlist for own jobs, add comments
  - auditor: Read-only access to logs and decision history
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

settings = get_settings()
_bearer_security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    ADMIN = "admin"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    AUDITOR = "auditor"


class AuthUser(BaseModel):
    id: str
    tenant_id: str
    email: str
    role: UserRole
    full_name: Optional[str] = None


def hash_password(password: str) -> str:
    """Generate salted SHA-256 hash for password storage."""
    salt = settings.SECRET_KEY[:16].encode("utf-8")
    pwd_bytes = password.encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt, iterations=100_000).hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored hash."""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)


def create_access_token(user: AuthUser, expires_in_seconds: int = 86400) -> str:
    """
    Generate an HMAC-SHA256 signed JWT-style access token containing tenant and user metadata.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "role": user.role.value,
        "full_name": user.full_name,
        "exp": int(time.time()) + expires_in_seconds,
    }

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    msg = f"{header_b64}.{payload_b64}".encode()

    secret = settings.SECRET_KEY.encode("utf-8")
    sig = hmac.new(secret, msg, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode access token, enforcing expiration and cryptographic signature.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format.",
        )

    header_b64, payload_b64, sig_b64 = parts
    msg = f"{header_b64}.{payload_b64}".encode()
    secret = settings.SECRET_KEY.encode("utf-8")

    expected_sig = hmac.new(secret, msg, hashlib.sha256).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature verification failed.",
        )

    # Pad base64 if needed
    rem = len(payload_b64) % 4
    if rem > 0:
        payload_b64 += "=" * (4 - rem)

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to decode token payload.",
        )

    if "exp" in payload and time.time() > payload["exp"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
        )

    return payload
