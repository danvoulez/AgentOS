# app/models/auth.py
from typing import Dict, List, Literal, Optional, Union, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TokenData(BaseModel):
    """JWT token payload data"""
    username: Optional[str] = None


class User(BaseModel):
    """User model for API responses"""
    id: str
    email: str
    full_name: str
    is_active: bool = True
    is_superuser: bool = False
    
    model_config = ConfigDict(
        from_attributes=True
    )


class Metadata(BaseModel):
    """Metadata for process request"""
    session_id: str = Field(..., description="Unique session identifier")
    conversation_id: Optional[str] = Field(None, description="Conversation identifier for history")
    user_id: str = Field(..., description="User identifier")
    timestamp: Optional[str] = Field(None, description="Request timestamp")


class Message(BaseModel):
    """Chat message model"""
    role: Literal["user", "assistant", "system", "function"]
    content: Optional[str] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    
    @field_validator('content')
    @classmethod
    def content_or_function_call_required(cls, v, values):
        """Validate that either content or function_call is provided"""
        if v is None and 'function_call' not in values.data:
            role = values.data.get('role')
            if role != 'function':  # function role can have null content
                raise ValueError("Either content or function_call must be provided")
        return v


class RequestPayload(BaseModel):
    """Request payload for process_request endpoint"""
    metadata: Metadata
    messages: List[Message]
    mode: Literal["chat", "completion", "function"] = "chat"
    model: Optional[str] = Field(None, description="LLM model to use")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "metadata": {
                    "session_id": "sess_123456789",
                    "conversation_id": "conv_987654321",
                    "user_id": "user_123456",
                    "timestamp": "2023-08-15T14:30:00Z"
                },
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant."
                    },
                    {
                        "role": "user",
                        "content": "What's the weather like today?"
                    }
                ],
                "mode": "chat",
                "model": "gpt-4",
                "temperature": 0.7
            }
        }
    )


class ResponsePayload(BaseModel):
    """Response payload for process_request endpoint"""
    messages: List[Message]
    metadata: Metadata
    usage: Optional[Dict[str, int]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "I don't have access to real-time weather data. To get the current weather, you could check a weather website or app, or look outside if possible."
                    }
                ],
                "metadata": {
                    "session_id": "sess_123456789",
                    "conversation_id": "conv_987654321",
                    "user_id": "user_123456",
                    "timestamp": "2023-08-15T14:30:05Z"
                },
                "usage": {
                    "prompt_tokens": 25,
                    "completion_tokens": 32,
                    "total_tokens": 57
                }
            }
        }
    )
