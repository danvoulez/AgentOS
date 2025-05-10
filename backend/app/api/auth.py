from fastapi import APIRouter, HTTPException, status, Depends
from typing import Annotated, Optional
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.utils.auth import (
    Token, TokenData, UserInDBForAuth,
    verify_password, create_access_token, get_password_hash
)

router = APIRouter()

async def get_user_from_db(db: AsyncIOMotorDatabase, email: str) -> Optional[UserInDBForAuth]:
    user_doc = await db["users"].find_one({"email": email.lower()})
    if user_doc:
        return UserInDBForAuth(**user_doc)
    return None

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    log = logger.bind(username=form_data.username)
    log.info("Access token requested.")
    user = await get_user_from_db(db, form_data.username)

    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        log.warning("Authentication failed: Incorrect email/password or no password set.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        log.warning("Authentication failed: User is inactive.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    token_payload_data = {
        "sub": user.email,
        "uid": str(user.id),
        "roles": user.roles
    }
    access_token = create_access_token(data=token_payload_data)
    log.success(f"Access token generated successfully for user: {user.email} (UID: {str(user.id)})")
    return Token(access_token=access_token, token_type="bearer")