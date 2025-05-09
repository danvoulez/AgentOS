from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Literal
import json
import os
from datetime import datetime, timezone

from fastapi import Depends
from loguru import logger
from pydantic import BaseModel

from app.core.config import settings
from app.models.semantic import Message


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def process_request(
        self,
        messages: List[Message],
        mode: Literal["chat", "completion", "function"] = "chat",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a request using the LLM.
        
        Args:
            messages: List of messages in the conversation
            mode: Processing mode (chat, completion, function)
            model: LLM model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the LLM
            
        Returns:
            Dict containing the LLM response
        """
        pass
    
    @abstractmethod
    async def get_intent_and_entities(
        self,
        text: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract intent and entities from text.
        
        Args:
            text: The text to analyze
            session_id: Session identifier
            **kwargs: Additional parameters
            
        Returns:
            Dict containing intent and entities
        """
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client implementation."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                organization=settings.OPENAI_ORG_ID if hasattr(settings, "OPENAI_ORG_ID") else None
            )
            self.default_model = settings.DEFAULT_LLM_MODEL or "gpt-4"
            logger.info(f"OpenAI client initialized with model: {self.default_model}")
        except ImportError:
            logger.error("OpenAI package not installed. Please install with 'pip install openai'")
            raise
        except Exception as e:
            logger.exception(f"Error initializing OpenAI client: {e}")
            raise
    
    async def process_request(
        self,
        messages: List[Message],
        mode: Literal["chat", "completion", "function"] = "chat",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a request using OpenAI."""
        log = logger.bind(service="OpenAIClient")
        
        try:
            # Convert our Message model to OpenAI format
            openai_messages = []
            for msg in messages:
                openai_msg = {
                    "role": msg.role if msg.role != "ai" else "assistant",
                    "content": msg.content
                }
                
                if msg.name:
                    openai_msg["name"] = msg.name
                
                if msg.function_call:
                    openai_msg["function_call"] = msg.function_call
                
                openai_messages.append(openai_msg)
            
            # Set parameters
            used_model = model or self.default_model
            used_temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
            used_max_tokens = max_tokens or settings.LLM_MAX_TOKENS
            
            log.info(f"Sending request to OpenAI: model={used_model}, temp={used_temp}, max_tokens={used_max_tokens}")
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=used_model,
                messages=openai_messages,
                temperature=used_temp,
                max_tokens=used_max_tokens,
                **kwargs
            )
            
            # Convert OpenAI response to our format
            result_messages = []
            for choice in response.choices:
                msg = choice.message
                result_msg = Message(
                    type="text",
                    role="ai",
                    content=msg.content or ""
                )
                
                if hasattr(msg, "function_call") and msg.function_call:
                    result_msg.function_call = msg.function_call
                
                result_messages.append(result_msg)
            
            # Extract usage information
            usage = None
            if hasattr(response, "usage"):
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            log.info(f"OpenAI request successful: {len(result_messages)} messages, {usage['total_tokens'] if usage else 'unknown'} tokens")
            
            return {
                "messages": result_messages,
                "usage": usage
            }
            
        except Exception as e:
            log.exception(f"Error processing OpenAI request: {e}")
            raise
    
    async def get_intent_and_entities(
        self,
        text: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Extract intent and entities using OpenAI."""
        log = logger.bind(service="OpenAIClient", session_id=session_id)
        
        try:
            # Create a system prompt for intent extraction
            system_prompt = """
            Extract the user's intent and entities from the following text.
            Return a JSON object with the following structure:
            {
                "intent": "the_intent",
                "entities": {
                    "entity_name": "entity_value"
                },
                "confidence": 0.95
            }
            """
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,  # Lower temperature for more deterministic results
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            log.info(f"Intent extraction successful: intent={result['intent']}, entities={result['entities']}")
            
            return result
            
        except Exception as e:
            log.exception(f"Error extracting intent: {e}")
            # Return a fallback intent
            return {
                "intent": "fallback",
                "entities": {},
                "confidence": 0.0
            }


class AnthropicClient(BaseLLMClient):
    """Anthropic (Claude) API client implementation."""
    
    def __init__(self):
        """Initialize the Anthropic client."""
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
            self.default_model = settings.DEFAULT_LLM_MODEL or "claude-3-opus-20240229"
            logger.info(f"Anthropic client initialized with model: {self.default_model}")
        except ImportError:
            logger.error("Anthropic package not installed. Please install with 'pip install anthropic'")
            raise
        except Exception as e:
            logger.exception(f"Error initializing Anthropic client: {e}")
            raise
    
    async def process_request(
        self,
        messages: List[Message],
        mode: Literal["chat", "completion", "function"] = "chat",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a request using Anthropic."""
        log = logger.bind(service="AnthropicClient")
        
        try:
            # Convert our Message model to Anthropic format
            anthropic_messages = []
            for msg in messages:
                role = msg.role
                if role == "ai":
                    role = "assistant"
                elif role == "function":
                    # Anthropic doesn't support function messages directly
                    # Convert to system message
                    role = "system"
                    
                anthropic_msg = {
                    "role": role,
                    "content": msg.content
                }
                anthropic_messages.append(anthropic_msg)
            
            # Set parameters
            used_model = model or self.default_model
            used_temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
            used_max_tokens = max_tokens or settings.LLM_MAX_TOKENS
            
            log.info(f"Sending request to Anthropic: model={used_model}, temp={used_temp}, max_tokens={used_max_tokens}")
            
            # Call Anthropic API
            response = await self.client.messages.create(
                model=used_model,
                messages=anthropic_messages,
                temperature=used_temp,
                max_tokens=used_max_tokens,
                **kwargs
            )
            
            # Convert Anthropic response to our format
            result_messages = [
                Message(
                    type="text",
                    role="ai",
                    content=response.content[0].text
                )
            ]
            
            # Extract usage information if available
            usage = None
            if hasattr(response, "usage"):
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            
            log.info(f"Anthropic request successful: {len(result_messages)} messages")
            
            return {
                "messages": result_messages,
                "usage": usage
            }
            
        except Exception as e:
            log.exception(f"Error processing Anthropic request: {e}")
            raise
    
    async def get_intent_and_entities(
        self,
        text: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Extract intent and entities using Anthropic."""
        log = logger.bind(service="AnthropicClient", session_id=session_id)
        
        try:
            # Create a system prompt for intent extraction
            system_prompt = """
            Extract the user's intent and entities from the following text.
            Return a JSON object with the following structure:
            {
                "intent": "the_intent",
                "entities": {
                    "entity_name": "entity_value"
                },
                "confidence": 0.95
            }
            """
            
            # Call Anthropic API
            response = await self.client.messages.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,  # Lower temperature for more deterministic results
            )
            
            # Parse the response
            content = response.content[0].text
            # Extract JSON from the response (may be wrapped in markdown code blocks)
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content.strip()
                
            result = json.loads(json_str)
            
            log.info(f"Intent extraction successful: intent={result['intent']}, entities={result['entities']}")
            
            return result
            
        except Exception as e:
            log.exception(f"Error extracting intent: {e}")
            # Return a fallback intent
            return {
                "intent": "fallback",
                "entities": {},
                "confidence": 0.0
            }


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing and development."""
    
    def __init__(self):
        """Initialize the mock client."""
        logger.info("Mock LLM client initialized")
    
    async def process_request(
        self,
        messages: List[Message],
        mode: Literal["chat", "completion", "function"] = "chat",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a request using mock responses."""
        log = logger.bind(service="MockLLMClient")
        
        try:
            # Get the last user message
            user_messages = [msg for msg in messages if msg.role == "user"]
            last_message = user_messages[-1] if user_messages else None
            
            # Generate a mock response
            if last_message:
                content = f"Mock response to: {last_message.content}"
            else:
                content = "Mock response to empty message"
            
            # Create a structured response for demonstration
            structured_content = {
                "title": "Mock Structured Data",
                "items": [
                    "This is a mock response",
                    f"Mode: {mode}",
                    f"Model: {model or 'default'}",
                    f"Temperature: {temperature or 0.7}",
                    f"Max tokens: {max_tokens or 1000}"
                ]
            }
            
            # Create response messages
            result_messages = [
                Message(
                    type="text",
                    role="ai",
                    content=content
                ),
                Message(
                    type="structured",
                    role="ai",
                    content=structured_content
                )
            ]
            
            # Simulate token usage
            usage = {
                "prompt_tokens": sum(len(str(msg.content).split()) for msg in messages),
                "completion_tokens": len(content.split()),
                "total_tokens": sum(len(str(msg.content).split()) for msg in messages) + len(content.split())
            }
            
            log.info(f"Mock request successful: {len(result_messages)} messages")
            
            return {
                "messages": result_messages,
                "usage": usage
            }
            
        except Exception as e:
            log.exception(f"Error in mock processing: {e}")
            raise
    
    async def get_intent_and_entities(
        self,
        text: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Extract intent and entities using mock logic."""
        log = logger.bind(service="MockLLMClient", session_id=session_id)
        
        try:
            # Simple keyword-based intent detection for demonstration
            text_lower = text.lower()
            
            if "status" in text_lower and ("order" in text_lower or "pedido" in text_lower):
                intent = "check_order_status"
                entities = {"order_id": "12345"}
            elif "product" in text_lower or "produto" in text_lower:
                intent = "product_info"
                entities = {"product": "sample_product"}
            elif "help" in text_lower or "ajuda" in text_lower:
                intent = "get_help"
                entities = {}
            else:
                intent = "general_query"
                entities = {"query": text}
            
            result = {
                "intent": intent,
                "entities": entities,
                "confidence": 0.9
            }
            
            log.info(f"Mock intent extraction: intent={intent}, entities={entities}")
            
            return result
            
        except Exception as e:
            log.exception(f"Error in mock intent extraction: {e}")
            # Return a fallback intent
            return {
                "intent": "fallback",
                "entities": {},
                "confidence": 0.0
            }


def get_llm_service() -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client based on configuration.
    
    Returns:
        BaseLLMClient: The configured LLM client
    """
    provider = settings.DEFAULT_LLM_PROVIDER.lower() if hasattr(settings, "DEFAULT_LLM_PROVIDER") else "openai"
    
    try:
        if provider == "openai":
            return OpenAIClient()
        elif provider == "anthropic":
            return AnthropicClient()
        elif provider == "mock":
            return MockLLMClient()
        else:
            logger.warning(f"Unknown LLM provider: {provider}, falling back to OpenAI")
            return OpenAIClient()
    except Exception as e:
        logger.exception(f"Error creating LLM client for provider {provider}: {e}")
        logger.warning("Falling back to MockLLMClient due to initialization error")
        return MockLLMClient()
