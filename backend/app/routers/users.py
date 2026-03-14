from fastapi import APIRouter, HTTPException, Query, status

from app.auth import require_admin, get_current_user, Depends
from app.models.user import UserCreate, UserUpdate, UserResponse, PasswordChange
from app.services import user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(search: str = Query("", description="Search by uid, cn, or mail"), _=Depends(require_admin)):
    return user_service.list_users(search)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, _=Depends(require_admin)):
    existing = user_service.get_user(data.uid)
    if existing:
        raise HTTPException(status_code=409, detail=f"User {data.uid} already exists")
    return user_service.create_user(data)


@router.get("/{uid}", response_model=UserResponse)
def get_user(uid: str, _=Depends(require_admin)):
    user = user_service.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{uid}", response_model=UserResponse)
def update_user(uid: str, data: UserUpdate, _=Depends(require_admin)):
    user = user_service.update_user(uid, data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(uid: str, _=Depends(require_admin)):
    if not user_service.delete_user(uid):
        raise HTTPException(status_code=404, detail="User not found")


@router.put("/{uid}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(uid: str, data: PasswordChange, _=Depends(require_admin)):
    if not user_service.reset_password(uid, data.new_password):
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/{uid}/disable", status_code=status.HTTP_204_NO_CONTENT)
def disable_user(uid: str, _=Depends(require_admin)):
    if not user_service.disable_user(uid):
        raise HTTPException(status_code=404, detail="User not found")
