# agentos_core/app/api/endpoints/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Request # Adicionar Request  
from fastapi.security import OAuth2PasswordRequestForm  
from typing import Annotated  
from datetime import timedelta  
from loguru import logger  
import uuid

# Segurança, Config, Modelos API, Auditoria, Repositório  
from app.core import security  
from app.core.config import settings  
from app.models.auth import Token # Modelo de resposta API  
from app.modules.office.services_audit import AuditService, get_audit_service  
from app.modules.people.repository import UserRepository, get_user_repository  
from app.modules.people.services import UserService # Usar UserService para autenticar  
from app.core.logging_config import trace_id_var

router = APIRouter()

@router.post("/login", response_model=Token, tags=["Authentication"])  
async def login_for_access_token(  
    request: Request, # Para auditoria (IP)  
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],  
    user_service: Annotated[UserService, Depends()], # Injetar UserService  
    user_repo: Annotated[UserRepository, Depends(get_user_repository)], # Service precisa do repo  
    audit_service: Annotated[AuditService, Depends(get_audit_service)],  
):  
    """  
    Authenticates using username (email) & password form data.  
    Returns a JWT access token on success.  
    """  
    username = form_data.username # Email do usuário  
    password = form_data.password  
    log = logger.bind(trace_id=trace_id_var.get(), api_endpoint="/auth/login", username=username)  
    log.info("Login attempt received.")

    # Usar UserService para autenticar (que usa o UserRepository)  
    user = await user_service.authenticate(email=username, password=password, user_repo=user_repo)

    log_details = {"email": username}  
    error_msg = None

    if not user:  
        error_msg = "Incorrect email or password"  
        log.warning(f"Authentication failed: {error_msg}")  
        # Logar auditoria de falha  
        await audit_service.log_audit_event(  
             action="user_login_failed", status="failure", entity_type="User", entity_id=username, # Usar email como ID aqui  
             request=request, current_user=None, error_message=error_msg, details=log_details  
        )  
        raise security.CredentialsException # Levanta 401

    # Verificar se usuário está ativo (o authenticate do service já faz isso)  
    # if not user.is_active: # Redundante se authenticate já valida  
    #     error_msg = "Inactive user"  
    #     log.warning(f"Authentication failed: {error_msg}")  
    #     await audit_service.log_audit_event(action="user_login_failed",...)  
    #     raise security.InactiveUserException # Levanta 403

    # --- Login bem-sucedido ---  
    log.success(f"Authentication successful for user: {username} (ID: {user.id})")

    # Logar auditoria de sucesso  
    await audit_service.log_audit_event(  
         action="user_login_success", status="success", entity_type="User", entity_id=user.id,  
         request=request, current_user=user, details=log_details  
    )

    # Criar token JWT  
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)  
    access_token = security.create_access_token(  
        data={"sub": user.email, "uid": str(user.id)}, # Incluir email ('sub') e ID ('uid') no token  
        expires_delta=access_token_expires  
    )

    return Token(access_token=access_token, token_type="bearer")

# O endpoint /users/me foi movido para people/routers.py
