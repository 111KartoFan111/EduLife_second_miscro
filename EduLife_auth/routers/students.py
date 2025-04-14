from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from utils.security import get_current_user, check_admin_role

router = APIRouter(
    prefix="/students",
    tags=["students"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/")
async def get_students():
    """Получить список всех студентов"""
    return {"message": "Список студентов"}