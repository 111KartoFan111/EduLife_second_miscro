from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from utils.security import get_current_user, check_admin_role

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/")
async def get_users(current_user: Dict[str, Any] = Depends(check_admin_role)):
    """Получить список всех пользователей (только для администраторов)"""
    return {"message": "Список пользователей"}