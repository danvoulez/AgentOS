import json
import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from httpx import AsyncClient

from app.core.config import settings
from app.api.endpoints.semantic import router as semantic_router
from app.models.semantic import User, Message, Metadata, RequestPayload, ResponsePayload


# Setup test app
@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application"""
    app = FastAPI()
    app.include_router(semantic_router, prefix="/api/v1/semantic")
    return app


@pytest.fixture
def client(app: FastAPI) -> Generator:
    """Create a test client for the app"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncClient:
    """Create an async test client for the app"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Mock user for testing
@pytest.fixture
def test_user() -> User:
    """Create a test user"""
    return User(
        id="user123",
        username="test@example.com",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        roles=["user"]
    )


# JWT token fixtures
@pytest.fixture
def valid_token(test_user: User) -> str:
    """Create a valid JWT token for the test user"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode = {
        "sub": test_user.username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "nbf": datetime.now(timezone.utc)
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


@pytest.fixture
def expired_token(test_user: User) -> str:
    """Create an expired JWT token for the test user"""
    expire = datetime.now(timezone.utc) - timedelta(minutes=15)
    to_encode = {
        "sub": test_user.username,
        "exp": expire,
        "iat": datetime.now(timezone.utc) - timedelta(minutes=30),
        "nbf": datetime.now(timezone.utc) - timedelta(minutes=30)
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


@pytest.fixture
def invalid_token() -> str:
    """Create an invalid JWT token"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkQGV4YW1wbGUuY29tIn0.invalid_signature"


# Valid request payload fixtures
@pytest.fixture
def valid_legacy_payload(test_user: User) -> Dict:
    """Create a valid legacy request payload with 'input'"""
    return {
        "input": "What's the status of my order?",
        "metadata": {
            "user_id": test_user.id,
            "session_id": "test_session_123",
            "conversation_id": "test_conversation_456",
            "mode": "advisor",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "model": "gpt-4",
        "temperature": 0.7
    }


@pytest.fixture
def valid_messages_payload(test_user: User) -> Dict:
    """Create a valid request payload with 'messages'"""
    return {
        "messages": [
            {
                "type": "text",
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "type": "text",
                "role": "user",
                "content": "What's the status of my order?"
            }
        ],
        "metadata": {
            "user_id": test_user.id,
            "session_id": "test_session_123",
            "conversation_id": "test_conversation_456",
            "mode": "advisor",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "model": "gpt-4",
        "temperature": 0.7
    }


# Mock LLM response
@pytest.fixture
def mock_llm_response() -> Dict:
    """Create a mock LLM response"""
    return {
        "messages": [
            {
                "type": "text",
                "role": "ai",
                "content": "I've checked your order status."
            },
            {
                "type": "structured",
                "role": "ai",
                "content": {
                    "title": "Order Status",
                    "items": [
                        "Order #12345",
                        "Status: Shipped",
                        "Estimated delivery: Aug 20, 2023"
                    ]
                }
            }
        ],
        "usage": {
            "prompt_tokens": 25,
            "completion_tokens": 42,
            "total_tokens": 67
        }
    }


# Tests
@patch("app.modules.people.repository.UserRepository")
@patch("app.services.llm_client.BaseLLMClient")
def test_process_request_legacy_valid(
    mock_llm_client: MagicMock,
    mock_user_repo: MagicMock,
    client: TestClient,
    valid_token: str,
    valid_legacy_payload: Dict,
    mock_llm_response: Dict,
    test_user: User
):
    """Test valid process_request with legacy format (input field)"""
    # Setup mocks
    mock_user_repo_instance = AsyncMock()
    mock_user_repo_instance.get_by_email.return_value = test_user
    mock_user_repo.return_value = mock_user_repo_instance
    
    mock_llm_client_instance = AsyncMock()
    mock_llm_client_instance.process_request.return_value = mock_llm_response
    mock_llm_client.return_value = mock_llm_client_instance
    
    # Make request
    response = client.post(
        "/api/v1/semantic/process_request",
        headers={"Authorization": f"Bearer {valid_token}"},
        json=valid_legacy_payload
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "ai"
    assert data["messages"][0]["type"] == "text"
    assert data["messages"][1]["type"] == "structured"
    assert "metadata" in data
    assert data["metadata"]["session_id"] == valid_legacy_payload["metadata"]["session_id"]
    assert "usage" in data
    
    # Verify mocks were called correctly
    mock_user_repo_instance.get_by_email.assert_called_once_with(test_user.username)
    mock_llm_client_instance.process_request.assert_called_once()


@patch("app.modules.people.repository.UserRepository")
@patch("app.services.llm_client.BaseLLMClient")
def test_process_request_messages_valid(
    mock_llm_client: MagicMock,
    mock_user_repo: MagicMock,
    client: TestClient,
    valid_token: str,
    valid_messages_payload: Dict,
    mock_llm_response: Dict,
    test_user: User
):
    """Test valid process_request with messages format"""
    # Setup mocks
    mock_user_repo_instance = AsyncMock()
    mock_user_repo_instance.get_by_email.return_value = test_user
    mock_user_repo.return_value = mock_user_repo_instance
    
    mock_llm_client_instance = AsyncMock()
    mock_llm_client_instance.process_request.return_value = mock_llm_response
    mock_llm_client.return_value = mock_llm_client_instance
    
    # Make request
    response = client.post(
        "/api/v1/semantic/process_request",
        headers={"Authorization": f"Bearer {valid_token}"},
        json=valid_messages_payload
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) == 2
    assert "metadata" in data
    assert "usage" in data
    
    # Verify mocks were called correctly
    mock_user_repo_instance.get_by_email.assert_called_once_with(test_user.username)
    mock_llm_client_instance.process_request.assert_called_once()


@patch("app.modules.people.repository.UserRepository")
def test_process_request_no_token(
    mock_user_repo: MagicMock,
    client: TestClient,
    valid_legacy_payload: Dict
):
    """Test process_request with no JWT token"""
    # Make request without token
    response = client.post(
        "/api/v1/semantic/process_request",
        json=valid_legacy_payload
    )
    
    # Assertions
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Could not validate credentials"
    
    # Verify user repo was not called
    mock_user_repo.return_value.get_by_email.assert_not_called()


@patch("app.modules.people.repository.UserRepository")
def test_process_request_expired_token(
    mock_user_repo: MagicMock,
    client: TestClient,
    expired_token: str,
    valid_legacy_payload: Dict
):
    """Test process_request with expired JWT token"""
    # Make request with expired token
    response = client.post(
        "/api/v1/semantic/process_request",
        headers={"Authorization": f"Bearer {expired_token}"},
        json=valid_legacy_payload
    )
    
    # Assertions
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Token has expired"
    
    # Verify user repo was not called
    mock_user_repo.return_value.get_by_email.assert_not_called()


@patch("app.modules.people.repository.UserRepository")
def test_process_request_invalid_token(
    mock_user_repo: MagicMock,
    client: TestClient,
    invalid_token: str,
    valid_legacy_payload: Dict
):
    """Test process_request with invalid JWT token"""
    # Make request with invalid token
    response = client.post(
        "/api/v1/semantic/process_request",
        headers={"Authorization": f"Bearer {invalid_token}"},
        json=valid_legacy_payload
    )
    
    # Assertions
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Could not validate credentials"
    
    # Verify user repo was not called
    mock_user_repo.return_value.get_by_email.assert_not_called()


@patch("app.modules.people.repository.UserRepository")
@patch("app.services.llm_client.BaseLLMClient")
def test_process_request_invalid_payload(
    mock_llm_client: MagicMock,
    mock_user_repo: MagicMock,
    client: TestClient,
    valid_token: str,
    test_user: User
):
    """Test process_request with invalid payload"""
    # Setup mocks
    mock_user_repo_instance = AsyncMock()
    mock_user_repo_instance.get_by_email.return_value = test_user
    mock_user_repo.return_value = mock_user_repo_instance
    
    # Invalid payload (missing both input and messages)
    invalid_payload = {
        "metadata": {
            "user_id": test_user.id,
            "session_id": "test_session_123"
        }
    }
    
    # Make request
    response = client.post(
        "/api/v1/semantic/process_request",
        headers={"Authorization": f"Bearer {valid_token}"},
        json=invalid_payload
    )
    
    # Assertions
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data
    
    # Verify LLM client was not called
    mock_llm_client.return_value.process_request.assert_not_called()


@patch("app.modules.people.repository.UserRepository")
@patch("app.services.llm_client.BaseLLMClient")
def test_process_request_user_id_mismatch(
    mock_llm_client: MagicMock,
    mock_user_repo: MagicMock,
    client: TestClient,
    valid_token: str,
    valid_legacy_payload: Dict,
    test_user: User
):
    """Test process_request with user_id mismatch"""
    # Setup mocks
    mock_user_repo_instance = AsyncMock()
    mock_user_repo_instance.get_by_email.return_value = test_user
    mock_user_repo.return_value = mock_user_repo_instance
    
    # Modify payload with different user_id
    mismatched_payload = valid_legacy_payload.copy()
    mismatched_payload["metadata"]["user_id"] = "different_user_id"
    
    # Make request
    response = client.post(
        "/api/v1/semantic/process_request",
        headers={"Authorization": f"Bearer {valid_token}"},
        json=mismatched_payload
    )
    
    # Assertions
    assert response.status_code == 403  # Forbidden
    data = response.json()
    assert "detail" in data
    assert "user id" in data["detail"].lower()
    
    # Verify LLM client was not called
    mock_llm_client.return_value.process_request.assert_not_called()


@patch("app.modules.people.repository.UserRepository")
@patch("app.services.llm_client.BaseLLMClient")
def test_process_request_invalid_mode(
    mock_llm_client: MagicMock,
    mock_user_repo: MagicMock,
    client: TestClient,
    valid_token: str,
    valid_legacy_payload: Dict,
    test_user: User
):
    """Test process_request with invalid mode"""
    # Setup mocks
    mock_user_repo_instance = AsyncMock()
    mock_user_repo_instance.get_by_email.return_value = test_user
    mock_user_repo.return_value = mock_user_repo_instance
    
    # Modify payload with invalid mode
    invalid_mode_payload = valid_legacy_payload.copy()
    invalid_mode_payload["metadata"]["mode"] = "invalid_mode"  # Not in allowed literals
    
    # Make request
    response = client.post(
        "/api/v1/semantic/process_request",
        headers={"Authorization": f"Bearer {valid_token}"},
        json=invalid_mode_payload
    )
    
    # Assertions
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data
    
    # Verify LLM client was not called
    mock_llm_client.return_value.process_request.assert_not_called()


@patch("app.modules.people.repository.UserRepository")
@patch("app.services.llm_client.BaseLLMClient")
def test_process_request_llm_error(
    mock_llm_client: MagicMock,
    mock_user_repo: MagicMock,
    client: TestClient,
    valid_token: str,
    valid_legacy_payload: Dict,
    test_user: User
):
    """Test process_request with LLM service error"""
    # Setup mocks
    mock_user_repo_instance = AsyncMock()
    mock_user_repo_instance.get_by_email.return_value = test_user
    mock_user_repo.return_value = mock_user_repo_instance
    
    # Make LLM client raise an exception
    mock_llm_client_instance = AsyncMock()
    mock_llm_client_instance.process_request.side_effect = Exception("LLM service error")
    mock_llm_client.return_value = mock_llm_client_instance
    
    # Make request
    response = client.post(
        "/api/v1/semantic/process_request",
        headers={"Authorization": f"Bearer {valid_token}"},
        json=valid_legacy_payload
    )
    
    # Assertions
    assert response.status_code == 500  # Internal server error
    data = response.json()
    assert "detail" in data
    
    # Verify LLM client was called
    mock_llm_client_instance.process_request.assert_called_once()
