from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models import UserMeResponse, UserProfileAPI, UserInDB

router = APIRouter()

@router.get("/me", response_model=UserMeResponse)
async def read_users_me(
    current_user: UserInDB = Depends(get_current_user)
):
    # Map UserInDB.profile (UserProfileDB) to UserProfileAPI
    profile_api_data = {}
    if current_user.profile:
        profile_api_data = current_user.profile.model_dump(exclude_none=True)
    response = UserMeResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        roles=current_user.roles,
        profile=UserProfileAPI(**profile_api_data) if profile_api_data else UserProfileAPI(),
        is_active=current_user.is_active
    )
    return response