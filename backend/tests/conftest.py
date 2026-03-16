import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_client():
    token = create_token("admin", is_admin=True)
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})
