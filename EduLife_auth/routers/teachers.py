from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
import database
from utils.security import get_current_user, check_admin_role

router = APIRouter(
    prefix="/teachers",
    tags=["teachers"],
    dependencies=[Depends(get_current_user)]
)

class TeacherCreate(BaseModel):
    user_id: int
    department_id: int
    position: str
    contact_info: str | None = None
    subject_ids: List[int] | None = None

class TeacherUpdate(BaseModel):
    department_id: int | None = None
    position: str | None = None
    contact_info: str | None = None
    subject_ids: List[int] | None = None

class TeacherResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    department_id: int
    department_name: str
    position: str
    contact_info: str | None
    subjects: List[dict]

@router.get("/", response_model=List[TeacherResponse])
async def get_teachers():
    """Получить список всех преподавателей"""
    return database.get_all_teachers()

@router.get("/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(teacher_id: int):
    """Получить информацию о конкретном преподавателе"""
    teacher = database.get_teacher_by_id(teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден"
        )
    return teacher

@router.post("/", response_model=TeacherResponse, dependencies=[Depends(check_admin_role)])
async def create_teacher(teacher: TeacherCreate):
    """Создать нового преподавателя (только для администраторов)"""
    try:
        teacher_id = database.create_teacher(teacher.dict())
        return database.get_teacher_by_id(teacher_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{teacher_id}", response_model=TeacherResponse, dependencies=[Depends(check_admin_role)])
async def update_teacher(teacher_id: int, teacher: TeacherUpdate):
    """Обновить информацию о преподавателе (только для администраторов)"""
    try:
        teacher_data = {k: v for k, v in teacher.dict().items() if v is not None}
        if not teacher_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указаны данные для обновления"
            )
        updated_id = database.update_teacher(teacher_id, teacher_data)
        teacher = database.get_teacher_by_id(updated_id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Преподаватель не найден"
            )
        return teacher
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{teacher_id}", dependencies=[Depends(check_admin_role)])
async def delete_teacher(teacher_id: int):
    """Удалить преподавателя (только для администраторов)"""
    try:
        if database.delete_teacher(teacher_id):
            return {"message": "Преподаватель успешно удален"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )