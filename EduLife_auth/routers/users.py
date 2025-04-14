from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
import database
from utils.security import get_current_user, check_admin_role

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)]
)

class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    full_name: str | None = None
    role_id: int | None = None
    disabled: bool | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role_id: int
    role_name: str
    disabled: bool
    created_at: str

@router.get("/", response_model=List[UserResponse], dependencies=[Depends(check_admin_role)])
async def get_users():
    """Получить список всех пользователей (только для администраторов)"""
    users = database.get_all_users()
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователи не найдены"
        )
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Получить информацию о конкретном пользователе"""
    if current_user["role_name"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к информации о других пользователях"
        )
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(check_admin_role)])
async def update_user(user_id: int, user: UserUpdate):
    """Обновить информацию о пользователе (только для администраторов)"""
    try:
        user_data = {k: v for k, v in user.dict().items() if v is not None}
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указаны данные для обновления"
            )
        updated_id = database.update_user(user_id, user_data)
        user = database.get_user_by_id(updated_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{user_id}", dependencies=[Depends(check_admin_role)])
async def delete_user(user_id: int):
    """Удалить пользователя (только для администраторов)"""
    try:
        if database.delete_user(user_id):
            return {"message": "Пользователь успешно удален"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )