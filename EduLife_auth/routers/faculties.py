from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
import database
from utils.security import get_current_user, check_admin_role

router = APIRouter(
    prefix="/faculties",
    tags=["faculties"],
    dependencies=[Depends(get_current_user)]
)

class FacultyCreate(BaseModel):
    name: str
    description: str = None

class FacultyUpdate(BaseModel):
    name: str = None
    description: str = None

class FacultyResponse(BaseModel):
    id: int
    name: str
    description: str = None
    created_at: str

@router.get("/", response_model=List[FacultyResponse])
async def get_faculties():
    """Получить список всех факультетов"""
    faculties = database.get_all_faculties()
    return faculties

@router.get("/{faculty_id}", response_model=FacultyResponse)
async def get_faculty(faculty_id: int):
    """Получить информацию о конкретном факультете"""
    faculty = database.get_faculty_by_id(faculty_id)
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Факультет не найден"
        )
    return faculty

@router.post("/", response_model=FacultyResponse, dependencies=[Depends(check_admin_role)])
async def create_faculty(faculty: FacultyCreate):
    """Создать новый факультет (только для администраторов)"""
    try:
        faculty_id = database.create_faculty({
            "name": faculty.name,
            "description": faculty.description
        })
        return database.get_faculty_by_id(faculty_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{faculty_id}", response_model=FacultyResponse, dependencies=[Depends(check_admin_role)])
async def update_faculty(faculty_id: int, faculty: FacultyUpdate):
    """Обновить информацию о факультете (только для администраторов)"""
    try:
        faculty_data = {k: v for k, v in faculty.dict().items() if v is not None}
        if not faculty_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указаны данные для обновления"
            )
        updated_id = database.update_faculty(faculty_id, faculty_data)
        faculty = database.get_faculty_by_id(updated_id)
        if not faculty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Факультет не найден"
            )
        return faculty
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{faculty_id}", dependencies=[Depends(check_admin_role)])
async def delete_faculty(faculty_id: int):
    """Удалить факультет (только для администраторов)"""
    try:
        if database.delete_faculty(faculty_id):
            return {"message": "Факультет успешно удален"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Факультет не найден"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )