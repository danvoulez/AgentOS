import jwt
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from passlib.context import CryptContext
from typing import Optional, List, Annotated
from datetime import datetime, timedelta, timezone
from loguru import logger
from bson import ObjectId

from app.config import settings
from app.models import PyObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    sub: EmailStr
    uid: str
    roles: List[str] = Field(default_factory=list)
    exp: Optional[int] = None
    iat: Optional[int] = None
    nbf: Optional[int] = None

    model_config = ConfigDict(extra='allow')

class UserInDBForAuth(BaseModel):
    id: PyObjectId = Field(alias="_id")
    email: EmailStr
    username: str
    hashed_password: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now, "nbf": now})
    if "sub" not in to_encode or "uid" not in to_encode:
        raise ValueError("Missing 'sub' or 'uid' claim for JWT creation.")
    if not isinstance(to_encode["uid"], str):
        raise ValueError("'uid' claim must be a string (stringified ObjectId).")
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_jwt_and_get_claims(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}
        )
        if not payload.get("sub") or not payload.get("uid"):
            raise jwt.InvalidTokenError("Token missing essential 'sub' or 'uid' claims.")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT Verification Failed: Token has expired.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT Verification Failed: Invalid token - {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error during JWT verification: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials (internal error)")

async def get_token_data_from_header(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None
) -> TokenData:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated or invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ")[1]
    claims = verify_jwt_and_get_claims(token)
    try:
        token_data = TokenData(**claims)
        return token_data
    except Exception as e:
        logger.warning(f"Failed to parse claims into TokenData: {e}. Claims: {claims}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload structure"
        )

async def get_current_active_user(
    token_data: Annotated[TokenData, Depends(get_token_data_from_header)]
) -> UserInDBForAuth:
    user_uid_str = token_data.uid
    log = logger.bind(user_uid=user_uid_str, user_sub=token_data.sub)
    log.debug("Fetching active user from DB using UID from token...")
    from app.core.database import get_database
    db_session = await get_database()
    try:
        user_object_id = ObjectId(user_uid_str)
    except Exception:
        log.error(f"Invalid UID format in token for DB query: '{user_uid_str}'. Expected ObjectId string.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identifier in token")
    user_doc = await db_session["users"].find_one({"_id": user_object_id})
    if user_doc is None:
        log.error(f"User with UID '{user_uid_str}' (from token) NOT FOUND in DB!")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User associated with token not found")
    try:
        user_db = UserInDBForAuth(**user_doc)
    except Exception as e:
        log.error(f"Error parsing user document from DB for UID '{user_uid_str}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing user data")
    if not user_db.is_active:
        log.warning(f"User '{user_db.email}' (UID: {user_uid_str}) is INACTIVE.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    log.info(f"Authenticated active user: {user_db.email} (UID: {user_uid_str}, Roles: {user_db.roles})")
    return user_db

CurrentUser = Annotated[UserInDBForAuth, Depends(get_current_active_user)]

def require_role(required_roles: List[str]):
    async def role_checker(current_user: CurrentUser):
        log = logger.bind(user_uid=str(current_user.id), required_roles=required_roles)
        log.debug(f"Checking roles. User roles: {current_user.roles}")
        has_permission = any(role in current_user.roles for role in required_roles)
        if not has_permission:
            log.warning("Permission denied due to missing role.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(required_roles)}"
            )
        log.debug("Role permission granted.")
    return role_checker