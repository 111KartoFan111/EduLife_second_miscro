from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
import database
from utils.security import get_current_user, check_admin_role

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    dependencies=[Depends(get_current_user)]
)

class GroupCreate(BaseModel):
    name: str
    faculty_id: int
    year: int

class GroupUpdate(BaseModel):
    name: str | None = None
    faculty_id: int | None = None
    year: int | None = None

class GroupResponse(BaseModel):
    id: int
    name: str
    faculty_id: int
    faculty_name: str
    year: int

@router.get("/", response_model=List[GroupResponse])
async def get_groups():
    """Получить список всех групп"""
    groups = database.get_all_groups()
    return groups

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int):
    """Получить информацию о конкретной группе"""
    group = database.get_group_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Группа не найдена"
        )
    return group

@router.post("/", response_model=GroupResponse, dependencies=[Depends(check_admin_role)])
async def create_group(group: GroupCreate):
    """Создать новую группу (только для администраторов)"""
    try:
        group_id = database.create_group({
            "name": group.name,
            "faculty_id": group.faculty_id,
            "year": group.year
        })
        return database.get_group_by_id(group_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{group_id}", response_model=GroupResponse, dependencies=[Depends(check_admin_role)])
async def update_group(group_id: int, group: GroupUpdate):
    """Обновить информацию о группе (только для администраторов)"""
    try:
        group_data = {k: v for k, v in group.dict().items() if v is not None}
        if not group_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указаны данные для обновления"
            )
        updated_id = database.update_group(group_id, group_data)
        group = database.get_group_by_id(updated_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена"
            )
        return group
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{group_id}", dependencies=[Depends(check_admin_role)])
async def delete_group(group_id: int):
    """Удалить группу (только для администраторов)"""
    try:
        if database.delete_group(group_id):
            return {"message": "Группа успешно удалена"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Группа не найдена"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )