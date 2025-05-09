from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional, Union

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from loguru import logger
from pydantic import ValidationError

from app.core.config import settings
from app.modules.people.models import User, UserInDB
from app.modules.people.repository import UserRepository, get_user_repository

# Token model moved to models.py
from app.models.auth import TokenData

# OAuth2 scheme for token retrieval
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False  # Don't auto-raise errors to handle them explicitly
)

# Common exceptions
CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

INACTIVE_USER_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Inactive user",
)

PERMISSION_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Operation not permitted",
)

# Contexto para Hashing de Senhas (Bcrypt)  
#pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema OAuth2 para obter token via form data no endpoint de login  
#oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login") # URL relativa ao prefixo da API

# Exceções de Autenticação/Autorização comuns  
#CredentialsException = HTTPException(  
#    status_code=status.HTTP_401_UNAUTHORIZED,  
#    detail="Could not validate credentials",  
#    headers={"WWW-Authenticate": "Bearer"},  
#)  
#InactiveUserException = HTTPException(  
#    status_code=status.HTTP_403_FORBIDDEN,  
#    detail="Inactive user",  
#)  
#PermissionException = HTTPException(  
#    status_code=status.HTTP_403_FORBIDDEN,  
#    detail="Operation not permitted"  
#)

# --- Funções de Utilidade de Senha ---

#def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:  
#    """Verifica se a senha plana corresponde ao hash armazenado."""  
#    if not hashed_password: # Não pode verificar se não há hash  
#        return False  
#    try:  
#        return pwd_context.verify(plain_password, hashed_password)  
#    except Exception as e:  
#        # Erros podem ocorrer com hashes inválidos ou antigos  
#        logger.error(f"Error verifying password (hash might be invalid): {e}")  
#        return False

#def get_password_hash(password: str) -> str:  
#    """Gera um hash seguro para a senha fornecida."""  
#    return pwd_context.hash(password)

# --- Funções de Utilidade JWT ---

#def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:  
#    """Cria um novo token de acesso JWT."""  
#    to_encode = data.copy()  
#    now = datetime.now(timezone.utc)

#    if expires_delta:  
#        expire = now + expires_delta  
#    else:  
#        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

#    # Adicionar claims padrão: exp, iat (issued at), nbf (not before)  
#    to_encode.update({"exp": expire, "iat": now, "nbf": now})

#    # Garantir que 'sub' (subject = username/email) está presente  
#    subject = to_encode.get("sub")  
#    if not subject:  
#        logger.critical("FATAL: Attempted to create JWT token without 'sub' (subject) claim.")  
#        raise ValueError("Missing 'sub' claim in token data for JWT creation")

#    try:  
#        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)  
#        logger.info(f"Access token created for subject: {subject}")  
#        logger.debug(f"Token expires at: {expire.isoformat()}")  
#        return encoded_jwt  
#    except Exception as e:  
#        logger.exception(f"Critical error encoding JWT token for subject '{subject}': {e}")  
#        # Levantar erro pois a criação do token falhou criticamente  
#        raise RuntimeError(f"Could not create access token: {e}") from e

#async def get_current_user_from_token(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenData:  
#    """  
#    Dependência FastAPI: Decodifica e valida o token JWT da requisição.  
#    Retorna o payload básico (TokenData) ou levanta HTTPException 401.  
#    """  
#    log = logger.bind(service="AuthTokenValidation")  
#    try:  
#        payload = jwt.decode(  
#            token,  
#            settings.SECRET_KEY,  
#            algorithms=[settings.ALGORITHM],  
#            options={"verify_aud": False} # Não validamos audience por padrão  
#        )  
#        username: str | None = payload.get("sub")  
#        if username is None:  
#            log.warning("Token validation failed: 'sub' (username) claim missing.")  
#            raise CredentialsException

#        # Validar payload básico (apenas username aqui)  
#        token_data = TokenData(username=username)  
#        log.debug(f"Token payload validated for username: {username}")  
#        return token_data

#    # Capturar exceções específicas do JWT  
#    except jwt.ExpiredSignatureError:  
#        log.warning("Token validation failed: Signature has expired.")  
#        raise HTTPException(  
#            status_code=status.HTTP_401_UNAUTHORIZED,  
#            detail="Token has expired",  
#            headers={"WWW-Authenticate": "Bearer error="invalid_token", error_description="The token has expired""}  
#        )  
#    except jwt.JWTClaimsError as e:  
#        log.warning(f"Token validation failed: Invalid claims - {e}")  
#        raise HTTPException(  
#            status_code=status.HTTP_401_UNAUTHORIZED,  
#            detail=f"Invalid token claims: {e}",  
#            headers={"WWW-Authenticate": "Bearer error="invalid_token", error_description="Invalid claims""}  
#        )  
#    except JWTError as e: # Outros erros JWT (formato inválido, etc.)  
#        log.warning(f"Invalid JWT token format or signature: {e}")  
#        raise CredentialsException from e  
#    except ValidationError as e: # Erro Pydantic se TokenData for mais complexo  
#        log.warning(f"Token data validation error: {e}")  
#        raise CredentialsException from e  
#    except Exception as e: # Captura geral inesperada  
#        log.exception(f"Unexpected error during token decoding/validation: {e}")  
#        raise CredentialsException from e

#async def get_current_active_user(  
#    # Depende da validação básica do token E do repositório de usuários  
#    token_data: Annotated[TokenData, Depends(get_current_user_from_token)],  
#    user_repo: Annotated[UserRepository, Depends(get_user_repository)]  
#) -> UserInDB: # Retorna o modelo completo do banco de dados  
#    """  
#    Dependência FastAPI: Busca o usuário no DB baseado no token validado  
#    e verifica se a conta está ativa. Levanta 401 ou 403 se falhar.  
#    """  
#    username = token_data.username  
#    log = logger.bind(service="AuthUserCheck", username=username)

#    if not username: # Segurança extra  
#         log.critical("FATAL: get_current_active_user called without username from token data.")  
#         raise CredentialsException # Não deveria acontecer

#    log.debug(f"Fetching user from DB and checking active status...")  
#    try:  
#        # Usar o email (armazenado no 'sub' do token) para buscar o usuário  
#        user_db = await user_repo.get_by_email(username)  
#    except Exception as db_err:  
#        log.exception(f"Database error fetching user '{username}'. Service potentially unavailable.")  
#        # Erro 5xx indica problema no servidor/DB  
#        raise HTTPException(  
#            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Usar 503 Service Unavailable  
#            detail="Failed to retrieve user data due to database error."  
#        )

#    if user_db is None:  
#        # Token válido, mas usuário não existe mais no DB? Inconsistência.  
#        log.error(f"User '{username}' from valid token NOT FOUND in database!")  
#        # Retornar 401 pois as credenciais (token) não correspondem a um usuário válido agora  
#        raise CredentialsException

#    if not user_db.is_active:  
#        # Usuário encontrado, mas inativo  
#        log.warning(f"Authentication successful, but user '{username}' (ID: {user_db.id}) is INACTIVE.")  
#        raise InactiveUserException # Levantar exceção específica 403

#    log.info(f"Authenticated and active user verified: {username} (ID: {user_db.id})")  
#    # Retorna o objeto UserInDB completo (sem a senha hash se o modelo for bem definido)  
#    return user_db

# Alias de dependência para uso simplificado nos endpoints  
# Qualquer endpoint que use 'CurrentUser' receberá o objeto UserInDB validado e ativo  
#CurrentUser = Annotated[UserInDB, Depends(get_current_active_user)]

async def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        TokenData: The decoded token data
        
    Raises:
        HTTPException: If token is invalid, expired, or has invalid claims
    """
    log = logger.bind(service="TokenVerification")
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}
        )
        
        username: str | None = payload.get("sub")
        if username is None:
            log.warning("Token validation failed: 'sub' (username) claim missing")
            raise CREDENTIALS_EXCEPTION
            
        # Validate token data
        token_data = TokenData(username=username)
        log.debug(f"Token payload validated for username: {username}")
        return token_data
        
    except jwt.ExpiredSignatureError:
        log.warning("Token validation failed: Signature has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The token has expired"'}
        )
    except jwt.JWTClaimsError as e:
        log.warning(f"Token validation failed: Invalid claims - {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token claims: {e}",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Invalid claims"'}
        )
    except JWTError as e:
        log.warning(f"Invalid JWT token format or signature: {e}")
        raise CREDENTIALS_EXCEPTION
    except ValidationError as e:
        log.warning(f"Token data validation error: {e}")
        raise CREDENTIALS_EXCEPTION
    except Exception as e:
        log.exception(f"Unexpected error during token decoding/validation: {e}")
        raise CREDENTIALS_EXCEPTION


async def get_user(username: str, user_repo: UserRepository) -> Optional[UserInDB]:
    """
    Retrieve a user by username/email from the repository.
    
    Args:
        username: The username (email) to look up
        user_repo: The user repository instance
        
    Returns:
        Optional[UserInDB]: The user if found, None otherwise
    """
    try:
        return await user_repo.get_by_email(username)
    except Exception as e:
        logger.exception(f"Error retrieving user {username}: {e}")
        return None


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)] = None
) -> User:
    """
    FastAPI dependency to get the current authenticated user from the Authorization header.
    
    Args:
        authorization: The Authorization header value
        user_repo: The user repository dependency
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    log = logger.bind(service="AuthUserCheck")
    
    if not authorization:
        log.warning("No Authorization header provided")
        raise CREDENTIALS_EXCEPTION
        
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        log.warning(f"Invalid authentication scheme: {scheme}")
        raise CREDENTIALS_EXCEPTION
        
    if not token:
        log.warning("No token provided in Authorization header")
        raise CREDENTIALS_EXCEPTION
    
    # Verify the token
    token_data = await verify_token(token)
    
    # Get the user
    username = token_data.username
    if not username:
        log.critical("Token data missing username after verification")
        raise CREDENTIALS_EXCEPTION
        
    user = await get_user(username, user_repo)
    if not user:
        log.error(f"User '{username}' from valid token NOT FOUND in database")
        raise CREDENTIALS_EXCEPTION
        
    if not user.is_active:
        log.warning(f"Authentication successful, but user '{username}' (ID: {user.id}) is INACTIVE")
        raise INACTIVE_USER_EXCEPTION
        
    log.info(f"Authenticated and active user verified: {username} (ID: {user.id})")
    return User.model_validate(user)


# Simplified dependency for use in endpoints
CurrentUser = Annotated[User, Depends(get_current_user)]
