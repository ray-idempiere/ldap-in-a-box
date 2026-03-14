from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.services.ldap_service import ldap_service

security = HTTPBearer()


def create_token(uid: str, is_admin: bool = False) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": uid, "admin": is_admin, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return {"uid": payload["sub"], "admin": payload.get("admin", False)}
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def login(username: str, password: str) -> str | None:
    """Authenticate user via LDAP bind. Returns JWT if successful."""
    # Try admin bind first
    admin_dn = settings.ldap_admin_dn
    if username == "admin":
        dn = admin_dn
    else:
        dn = f"uid={username},ou=users,{settings.ldap_base_dn}"

    if ldap_service.authenticate(dn, password):
        is_admin = (dn == admin_dn)
        return create_token(username, is_admin=is_admin)
    return None
