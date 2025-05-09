from datetime import datetime, timezone
import uuid
from typing import List, Dict, Any, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.core.security import CurrentUser
from app.models.semantic import (
    User, Message, Metadata, RequestPayload, ResponsePayload,
    ProcessRequestInput, ProcessRequestOutput, LLMResponse
)
from app.services.llm_client import BaseLLMClient, get_llm_service
from app.services.dispatcher import dispatch_intent

router = APIRouter()


@router.post(
    "/process_request",
    response_model=ResponsePayload,
    summary="Process natural language or structured requests",
    description="Processes user messages using LLM and returns appropriate responses",
    tags=["Semantic Processing"],
)
async def process_request(
    payload: RequestPayload,
    current_user: User = Depends(CurrentUser),
    llm_client: BaseLLMClient = Depends(get_llm_service)
) -> ResponsePayload:
    """
    Process a natural language or structured request.
    
    Args:
        payload: The request payload containing messages and metadata
        current_user: The authenticated user (from JWT token)
        llm_client: The LLM client service
        
    Returns:
        ResponsePayload: The processed response
        
    Raises:
        HTTPException: If the request is invalid or processing fails
    """
    request_id = str(uuid.uuid4())
    log = logger.bind(
        request_id=request_id,
        user_id=current_user.id,
        session_id=payload.metadata.session_id
    )
    
    log.info(f"Processing request: mode={payload.metadata.mode}, model={payload.model or 'default'}")
    
    # Validate user ID in payload matches authenticated user
    if payload.metadata.user_id != current_user.id:
        log.warning(f"User ID mismatch: payload={payload.metadata.user_id}, token={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID in payload does not match authenticated user"
        )
    
    try:
        # Handle legacy 'input' field by converting to messages format
        messages: List[Message] = []
        if payload.messages:
            messages = payload.messages
        elif payload.input:
            # Convert legacy input to messages format
            messages = [
                Message(
                    type="text",
                    role="user",
                    content=payload.input
                )
            ]
        else:
            log.error("Request missing both 'input' and 'messages'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request must contain either 'input' or 'messages'"
            )
        
        # Process the request using LLM client
        response = await llm_client.process_request(
            messages=messages,
            mode=payload.metadata.mode,
            model=payload.model,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
        
        # Update metadata with current timestamp if not provided
        if not payload.metadata.timestamp:
            payload.metadata.timestamp = datetime.now(timezone.utc).isoformat()
        
        # Construct response
        result = ResponsePayload(
            messages=response["messages"],
            metadata=payload.metadata,
            usage=response.get("usage")
        )
        
        log.info(f"Request processed successfully: {len(result.messages)} messages returned")
        return result
        
    except ValueError as e:
        log.warning(f"Invalid request parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        log.exception(f"Error processing request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request"
        )


@router.post(
    "/legacy/process_request",
    response_model=ProcessRequestOutput,
    summary="Process Natural Language Command (Legacy)",
    description="Receives a natural language command, interprets it using an LLM, "
                "and dispatches it to the appropriate AgentOS module.",
    tags=["Semantic Gateway"],
)
async def legacy_process_request(
    request_data: ProcessRequestInput,
    current_user: User = Depends(CurrentUser),
    llm_client: BaseLLMClient = Depends(get_llm_service)
) -> ProcessRequestOutput:
    """
    Legacy endpoint for processing natural language commands.
    
    Args:
        request_data: The request data containing text and user information
        current_user: The authenticated user (from JWT token)
        llm_client: The LLM client service
        
    Returns:
        ProcessRequestOutput: The processed response
        
    Raises:
        HTTPException: If the request is invalid or processing fails
    """
    request_id = str(uuid.uuid4())
    log = logger.bind(
        request_id=request_id,
        user_id=current_user.id,
        session_id=request_data.session_id
    )
    
    log.info(f"Received legacy process_request: '{request_data.text}'")
    
    # Validate user ID in payload matches authenticated user
    if request_data.user_id != current_user.id:
        log.warning(f"User ID mismatch: payload={request_data.user_id}, token={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID in payload does not match authenticated user"
        )

    llm_response: Optional[Dict[str, Any]] = None
    dispatcher_result: Optional[Dict[str, Any]] = None

    try:
        # Extract intent and entities
        llm_response = await llm_client.get_intent_and_entities(
            text=request_data.text,
            session_id=request_data.session_id
        )
        
        log.info(f"LLM Result: Intent='{llm_response['intent']}', Entities={llm_response['entities']}")

        # Dispatch to appropriate handler
        dispatcher_result = await dispatch_intent(
            intent=llm_response["intent"],
            entities=llm_response["entities"],
            user_id=current_user.id
        )
        
        log.info(f"Dispatch successful for intent '{llm_response['intent']}'. Result: {dispatcher_result}")

        # Prepare response
        final_status = dispatcher_result.get("status", "success")
        final_message = dispatcher_result.get("message", f"Action for intent '{llm_response['intent']}' completed.")
        
        return ProcessRequestOutput(
            status=final_status,
            message=final_message,
            intent=llm_response["intent"],
            data=dispatcher_result,
            request_id=request_id
        )

    except ValueError as e:
        log.warning(f"Value Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        log.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
