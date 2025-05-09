# agentos_core/app/services/mcp_service.py

from loguru import logger  
from app.core.logging_config import trace_id_var  
import uuid  
import asyncio  
import httpx  
from pydantic import BaseModel, ValidationError, Field  
from typing import Dict, Any, Optional, List, Type # Adicionar Type

# --- MCP Tool Registry ---  
# Definir ferramentas e seus schemas Pydantic para validação

# Exemplo Schemas (Definir em local apropriado ou aqui)  
class GetWeatherParams(BaseModel):  
    location: str = Field(..., description="City name (e.g., Lisbon, London)")  
    unit: Literal["celsius", "fahrenheit"] = "celsius" # Usar Literal

class GetWeatherResponse(BaseModel):  
    temperature: float  
    condition: str  
    unit: str

class ProcessPaymentParams(BaseModel):  
    amount: Decimal = Field(..., gt=Decimal(0), decimal_places=2)  
    currency: str = Field(default="BRL", pattern=r"^[A-Z]{3}$") # ISO Currency  
    user_id: str # Quem está pagando  
    order_id: Optional[str] = None  
    payment_method_token: str # Exemplo

class ProcessPaymentResponse(BaseModel):  
    transaction_id: str  
    status: Literal["approved", "declined", "pending", "error"]

class MCPRegistry:  
    """Mantém a definição das ferramentas disponíveis via MCP."""

    # Usar um tipo mais forte para a definição da ferramenta  
    class ToolDefinition(BaseModel):  
         description: str  
         endpoint: str # URL absoluto ou rota interna  
         method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "POST"  
         params_schema: Optional[Type[BaseModel]] = None # Schema para GET query params  
         body_schema: Optional[Type[BaseModel]] = None   # Schema para POST/PUT/PATCH body  
         response_schema: Optional[Type[BaseModel]] = None # Schema para validar resposta  
         auth_required: Optional[str] = None # Nome da env var da API Key, se necessário

    _tools: Dict[str, ToolDefinition] = {  
        "get_weather": ToolDefinition(  
            description="Get the current weather for a specific location.",  
            endpoint="https://api.weatherapi.com/v1/current.json", # Exemplo REAL  
            method="GET",  
            params_schema=GetWeatherParams,  
            response_schema=GetWeatherResponse,  
            auth_required="WEATHER_API_KEY" # Precisa de uma chave no .env  
        ),  
        "process_payment_internal": ToolDefinition(  
            description="Process a payment via the internal Payment Service.",  
            # Usar path relativo se for chamar outro endpoint da *nossa* API  
            # Assumindo que temos um endpoint /api/v1/payments/process  
            endpoint="/api/v1/payments/process",  
            method="POST",  
            body_schema=ProcessPaymentParams,  
            response_schema=ProcessPaymentResponse,  
            auth_required=None # Usar autenticação interna da API (JWT)  
        )  
        # Adicionar mais ferramentas...  
    }

    @classmethod  
    def get_tool_definition(cls, tool_name: str) -> Optional[ToolDefinition]:  
        return cls._tools.get(tool_name)

    @classmethod  
    def get_all_tool_info_for_llm(cls) -> List[Dict[str, Any]]:  
        """Formata a definição das ferramentas para a API de Tool Calling do LLM."""  
        tool_info = []  
        for name, definition in cls._tools.items():  
             schema_model = definition.body_schema or definition.params_schema  
             if schema_model:  
                  # Gerar JSON schema a partir do modelo Pydantic  
                  try:  
                      schema = schema_model.model_json_schema()  
                      # Ajustar para formato esperado por OpenAI/Gemini Tool spec  
                      parameters = {  
                          "type": "object",  
                          "properties": schema.get("properties", {}),  
                          "required": schema.get("required", [])  
                          }  
                      # Remover campos extras que LLM não precisa (como 'title')  
                      parameters.pop("title", None)  
                      for prop in parameters["properties"].values():  
                          prop.pop("title", None)

                      tool_info.append({  
                          "type": "function",  
                          "function": {  
                              "name": name,  
                              "description": definition.description,  
                              "parameters": parameters,  
                          }  
                      })  
                  except Exception as e:  
                       logger.error(f"Falha ao gerar schema JSON para ferramenta MCP '{name}': {e}")  
             else: # Ferramentas sem parâmetros  
                  tool_info.append({  
                       "type": "function",  
                       "function": {  
                           "name": name,  
                           "description": definition.description,  
                           "parameters": {"type": "object", "properties": {}}, # OpenAI requer isso  
                       }  
                  })  
        return tool_info

# --- MCP Client ---  
class MCPClient:  
    """Cliente para executar ferramentas MCP com validação e chamadas HTTP."""

    def __init__(self):  
        # Criar cliente HTTPX persistente para reutilizar conexões  
        # Ajustar limites conforme necessário  
        self.http_client = httpx.AsyncClient(  
            timeout=30.0, # Timeout padrão para chamadas MCP  
            follow_redirects=True,  
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),  
            http2=True  
        )  
        logger.info("MCPClient inicializado com cliente HTTPX persistente.")

    async def close(self):  
         """Fecha o cliente HTTPX."""  
         await self.http_client.aclose()  
         logger.info("Cliente HTTPX do MCPClient fechado.")

    async def execute_tool(self, tool_name: str, parameters: dict) -> Dict[str, Any]:  
        """Executa uma ferramenta MCP validada."""  
        log = logger.bind(trace_id=trace_id_var.get(), service="MCPClient", tool=tool_name)  
        log.info(f"Executando ferramenta MCP...")  
        log.debug(f"Parâmetros recebidos: {parameters}")

        tool_def = MCPRegistry.get_tool_definition(tool_name)  
        if not tool_def:  
            log.error("Ferramenta não encontrada no MCP Registry.")  
            return {"success": False, "error": f"Tool '{tool_name}' not defined."}

        # 1. Validar Parâmetros de Entrada  
        validated_data: Optional[BaseModel] = None  
        input_schema = tool_def.body_schema or tool_def.params_schema  
        if input_schema:  
            try:  
                validated_data = input_schema.model_validate(parameters)  
                log.debug("Parâmetros de entrada validados com sucesso.")  
            except ValidationError as e:  
                log.warning(f"Validação de parâmetros de entrada falhou: {e.errors()}")  
                return {"success": False, "error": f"Invalid parameters for tool '{tool_name}'.", "details": e.errors()}  
        else:  
             validated_data = parameters # Usar parâmetros brutos se não houver schema

        # 2. Preparar Requisição HTTP  
        method = tool_def.method.upper()  
        url = tool_def.endpoint # Assumir URL/path completo

        headers = {"Content-Type": "application/json", "Accept": "application/json"}  
        # Adicionar Auth se necessário  
        if tool_def.auth_required:  
             api_key = os.getenv(tool_def.auth_required)  
             if not api_key:  
                  log.error(f"API Key env var '{tool_def.auth_required}' não encontrada para a ferramenta '{tool_name}'.")  
                  return {"success": False, "error": f"Authentication required but key '{tool_def.auth_required}' not configured."}  
             # Assumir Bearer token por padrão? Ou adaptar baseado no tool_def?  
             headers['Authorization'] = f"Bearer {api_key}" # Ou outro schema

        # Preparar corpo ou query params  
        json_payload: Optional[Dict] = None  
        query_params: Optional[Dict] = None  
        if method in ["POST", "PUT", "PATCH"]:  
            json_payload = validated_data.model_dump(mode='json') if isinstance(validated_data, BaseModel) else validated_data  
        elif method == "GET":  
            query_params = validated_data.model_dump(mode='json') if isinstance(validated_data, BaseModel) else validated_data

        # 3. Executar Chamada HTTP  
        log.info(f"Executando {method} para {url}")  
        try:  
            response = await self.http_client.request(  
                method=method, url=url, headers=headers, json=json_payload, params=query_params  
            )  
            response.raise_for_status() # Levanta erro para 4xx/5xx  
            response_data = response.json()  
            log.success(f"Execução da ferramenta '{tool_name}' bem-sucedida (Status: {response.status_code}).")

            # 4. Validar Resposta (Opcional)  
            output_schema = tool_def.response_schema  
            if output_schema:  
                try:  
                    validated_response = output_schema.model_validate(response_data)  
                    log.debug("Resposta validada com sucesso.")  
                    # Retornar dados já validados/formatados pelo Pydantic  
                    return {"success": True, "data": validated_response.model_dump(mode='json')}  
                except ValidationError as e:  
                    log.warning(f"Validação da resposta falhou para '{tool_name}': {e.errors()}. Retornando dados brutos.")  
                    return {"success": True, "data": response_data, "validation_warning": "Response schema mismatch"}  
            else:  
                # Sem schema de resposta, retornar dados brutos  
                return {"success": True, "data": response_data}

        # Tratamento de Erros HTTPX  
        except httpx.HTTPStatusError as e:  
            err_body = e.response.text[:200] # Limitar tamanho  
            log.error(f"Erro HTTP {e.response.status_code} ao executar ferramenta '{tool_name}': {err_body}")  
            return {"success": False, "error": f"Tool execution failed with status {e.response.status_code}", "details": err_body}  
        except httpx.TimeoutException:  
            log.error(f"Timeout ao executar ferramenta '{tool_name}' em {url}.")  
            return {"success": False, "error": "Tool execution timed out."}  
        except httpx.RequestError as e:  
            log.error(f"Erro de rede/requisição ao executar ferramenta '{tool_name}': {e}")  
            return {"success": False, "error": f"Network or request error: {e}"}  
        except Exception as e:  
            log.exception(f"Erro inesperado ao executar ferramenta '{tool_name}': {e}")  
            return {"success": False, "error": f"Unexpected error: {e}"}

# Instância Singleton (pode ser criada no lifespan do FastAPI)  
# mcp_client_instance = MCPClient()  
# async def get_mcp_client() -> MCPClient: return mcp_client_instance

# Importar tipos necessários  
from abc import ABC, abstractmethod  
from typing import Literal  
from decimal import Decimal  
import os
