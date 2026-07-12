"""
test_auth.py — Unit Tests for Authentication Router
---------------------------------------------------
Tests the /register and /login endpoints using FastAPI's TestClient
and a mock MongoDB connection (mongomock_motor) so we don't need
a real database running.
"""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie

from app.main import app
from app.models.user import User
from app.core.auth.hashing import get_password_hash

# We use TestClient to make mock HTTP requests to our FastAPI app
client = TestClient(app)

@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def setup_db():
    """
    This fixture runs before every test.
    It initializes Beanie with a fake, in-memory MongoDB connection
    so the database calls inside the API routes work perfectly without a real server!
    """
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client.test_db
    await init_beanie(database=mock_db, document_models=[User])
    yield
    # We could clean up here, but mongomock_motor is in-memory anyway


@pytest.mark.asyncio
async def test_register_user_success():
    """
    Test that a valid registration request succeeds and saves to the mock DB.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "full_name": "Test User",
            "password": "strongpassword123!"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "Test User"
    assert data["role"] == "viewer"
    assert "password" not in data
    assert "hashed_password" not in data
    
    # Verify the user was actually saved in the mock database
    user_in_db = await User.find_one(User.email == "newuser@example.com")
    assert user_in_db is not None
    assert user_in_db.full_name == "Test User"


@pytest.mark.asyncio
async def test_register_user_duplicate_email():
    """
    Test that registering an email that already exists returns a 400 Bad Request.
    """
    # 1. Insert a user directly into the mock DB
    existing_user = User(
        email="existing@example.com",
        full_name="Existing User",
        hashed_password=get_password_hash("password123")
    )
    await existing_user.insert()
    
    # 2. Try to register with the same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "full_name": "Another User",
            "password": "strongpassword123!"
        }
    )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_user_invalid_credentials():
    """
    Test that a login request with a wrong password returns a 401 Unauthorized.
    """
    # 1. Insert a user
    user = User(
        email="user@example.com",
        full_name="User",
        hashed_password=get_password_hash("correctpassword")
    )
    await user.insert()
    
    # 2. Try to login with WRONG password
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "WRONG_PASSWORD"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_user_success():
    """
    Test that a successful login returns the JWT tokens.
    """
    # 1. Insert a user
    user = User(
        email="success@example.com",
        full_name="User",
        hashed_password=get_password_hash("correctpassword")
    )
    await user.insert()
    
    # 2. Try to login with correct credentials
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "success@example.com",
            "password": "correctpassword"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "success@example.com"
