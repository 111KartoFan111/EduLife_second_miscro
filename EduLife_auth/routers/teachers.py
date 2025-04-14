from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from utils.security import get_current_user, check_admin_role

router = APIRouter(
    prefix="/teachers",
    tags=["teachers"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/")
async def get_teachers():
    """Получить список всех преподавателей"""
    return {"message": "Список преподавателей"}