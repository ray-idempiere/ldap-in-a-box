from app.auth import create_token, get_current_user
from fastapi.security import HTTPAuthorizationCredentials


def test_create_and_verify_token():
    token = create_token("testuser", is_admin=True)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds)
    assert user["uid"] == "testuser"
    assert user["admin"] is True


def test_invalid_token():
    import pytest
    from fastapi import HTTPException

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401
