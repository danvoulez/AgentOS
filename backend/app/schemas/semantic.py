# schemas/semantic.py
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class ProcessRequestInput(BaseModel):
    text: str = Field(..., description="Natural language command from the user.")
    session_id: Optional[str] = Field(None, description="Optional session ID for context.")
    user_id: Optional[str] = Field(None, description="Optional user ID initiating the request.")

class LLMResponse(BaseModel):
    intent: str = Field(..., description="The primary intent identified by the LLM.")
    entities: Dict[str, Any] = Field({}, description="Entities extracted by the LLM (key-value pairs).")
    confidence: Optional[float] = Field(None, description="Confidence score for the identified intent (0.0 to 1.0).")
    raw_llm_output: Optional[str] = Field(None, description="Raw output from the LLM for debugging.") # Optional

class ProcessRequestOutput(BaseModel):
    status: str = Field(..., description="Status of the request processing ('success', 'error', 'intent_not_found', 'llm_error').")
    message: Optional[str] = Field(None, description="A human-readable message about the result.")
    intent: Optional[str] = Field(None, description="The intent that was processed or failed.")
    data: Optional[Any] = Field(None, description="Data returned by the executed module action.")
    request_id: str = Field(..., description="Unique ID for tracing the request.")
