import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture(autouse=True)
def mock_external_llm_calls():
    with patch("app.services.llm_service.AsyncOpenAI", new_callable=MagicMock) as mock_openai_constructor:
        mock_client_instance = MagicMock()
        mock_chat_completions = MagicMock()
        mock_chat_completions_create = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = "{}"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_completion_response = MagicMock()
        mock_completion_response.choices = [mock_choice]
        mock_chat_completions_create.return_value = mock_completion_response
        mock_chat_completions.create = mock_chat_completions_create
        mock_client_instance.chat.completions = mock_chat_completions
        mock_openai_constructor.return_value = mock_client_instance
        yield mock_openai_constructor

@pytest.fixture(autouse=True)
def mock_opa_calls():
    with patch("app.utils.opa_validator.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = True
        mock_post.return_value = mock_response
        yield mock_post

@pytest.fixture(scope="function")
def mock_ws_manager_broadcast(mocker):
    return mocker.patch("app.websocket.connection_manager.manager.broadcast", new_callable=AsyncMock)