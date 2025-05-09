from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict, EmailStr


class User(BaseModel):
    """Represents a user in the system."""
    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username (typically email)")
    email: Optional[EmailStr] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    is_active: bool = Field(True, description="Whether the user account is active")
    roles: List[str] = Field(default_factory=list, description="User roles for authorization")

    model_config = ConfigDict(from_attributes=True)


class TokenData(BaseModel):
    """Data expected to be encoded in the JWT token."""
    username: Optional[str] = Field(None, alias="sub", description="Username from token subject claim")

    model_config = ConfigDict(populate_by_name=True)


class Metadata(BaseModel):
    """Metadata for the request payload."""
    user_id: str = Field(..., description="User ID from the frontend context")
    session_id: str = Field(..., description="Unique session identifier")
    conversation_id: Optional[str] = Field(None, description="Optional conversation tracking ID")
    mode: Literal["advisor", "chat", "completion"] = Field("advisor", description="Processing mode")
    timestamp: Optional[str] = Field(None, description="Request timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_abc123",
                "session_id": "sess_xyz789",
                "conversation_id": "conv_123456",
                "mode": "advisor",
                "timestamp": "2023-08-15T14:30:00Z"
            }
        }
    )


class Message(BaseModel):
    """Schema for a single message in the request or response."""
    type: Literal["text", "structured"] = Field("text", description="Message type")
    role: Literal["ai", "user", "system", "assistant", "function"] = Field(..., description="Message role")
    content: Union[str, Dict[str, Any]] = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Name for function messages")
    function_call: Optional[Dict[str, Any]] = Field(None, description="Function call details")

    @field_validator('content')
    @classmethod
    def check_content_type(cls, value, info):
        """Validate content based on type."""
        values = info.data
        message_type = values.get('type')
        if message_type == "text" and not isinstance(value, str):
            raise ValueError("Content must be a string when type is 'text'")
        if message_type == "structured" and not isinstance(value, dict):
            raise ValueError("Content must be a dictionary when type is 'structured'")
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "text",
                "role": "user",
                "content": "What's the status of my order?"
            }
        }
    )


class RequestPayload(BaseModel):
    """Input schema for the process_request endpoint."""
    input: Optional[str] = Field(None, description="User's message text (legacy format)")
    messages: Optional[List[Message]] = Field(None, description="List of messages in the conversation")
    metadata: Metadata = Field(..., description="Request metadata")
    model: Optional[str] = Field(None, description="LLM model to use")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")

    @field_validator('messages', 'input')
    @classmethod
    def validate_input_format(cls, value, info):
        """Ensure either input or messages is provided."""
        values = info.data
        field_name = info.field_name
        
        # If validating messages and it's None, check if input exists
        if field_name == 'messages' and value is None:
            if not values.get('input'):
                raise ValueError("Either 'input' or 'messages' must be provided")
        
        # If validating input and it's None, check if messages exists
        if field_name == 'input' and value is None:
            if not values.get('messages'):
                raise ValueError("Either 'input' or 'messages' must be provided")
                
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "input": "What's the status of my order?",
                "metadata": {
                    "user_id": "user_abc123",
                    "session_id": "sess_xyz789",
                    "conversation_id": "conv_123456",
                    "mode": "advisor"
                },
                "model": "gpt-4",
                "temperature": 0.7
            }
        }
    )


class ResponsePayload(BaseModel):
    """Output schema for the process_request endpoint."""
    messages: List[Message] = Field(..., min_items=1, description="List of response messages")
    metadata: Optional[Metadata] = Field(None, description="Response metadata (echoed from request)")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
                "metadata": {
                    "user_id": "user_abc123",
                    "session_id": "sess_xyz789",
                    "conversation_id": "conv_123456",
                    "mode": "advisor"
                },
                "usage": {
                    "prompt_tokens": 25,
                    "completion_tokens": 42,
                    "total_tokens": 67
                }
            }
        }
    )


class LLMResponse(BaseModel):
    """Response from the LLM service."""
    intent: str = Field(..., description="Detected intent")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "intent": "check_order_status",
                "entities": {
                    "order_id": "12345"
                },
                "confidence": 0.95
            }
        }
    )


class ProcessRequestInput(BaseModel):
    """Input schema for the legacy process_request endpoint."""
    text: str = Field(..., min_length=1, description="User's message text")
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "What's the status of my order?",
                "user_id": "user_abc123",
                "session_id": "sess_xyz789"
            }
        }
    )


class ProcessRequestOutput(BaseModel):
    """Output schema for the legacy process_request endpoint."""
    status: str = Field(..., description="Status of the request")
    message: str = Field(..., description="Response message")
    intent: str = Field(..., description="Detected intent")
    data: Dict[str, Any] = Field(..., description="Response data")
    request_id: str = Field(..., description="Request ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Intent processed successfully",
                "intent": "check_order_status",
                "data": {
                    "order_id": "12345",
                    "status": "shipped",
                    "estimated_delivery": "2023-08-20"
                },
                "request_id": "req_abc123xyz789"
            }
        }
    )
