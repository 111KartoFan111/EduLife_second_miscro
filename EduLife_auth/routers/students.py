from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
import database
from utils.security import get_current_user, check_admin_role

router = APIRouter(
    prefix="/students",
    tags=["students"],
    dependencies=[Depends(get_current_user)]
)

class StudentCreate(BaseModel):
    user_id: int
    group_id: int
    student_id: str
    enrollment_year: int

class StudentUpdate(BaseModel):
    group_id: int | None = None
    student_id: str | None = None
    enrollment_year: int | None = None

class StudentResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    group_id: int
    group_name: str
    group_year: int
    faculty_id: int
    faculty_name: str
    student_id: str
    enrollment_year: int

@router.get("/", response_model=List[StudentResponse])
async def get_students():
    """Получить список всех студентов"""
    return database.get_all_students()

@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int):
    """Получить информацию о конкретном студенте"""
    student = database.get_student_by_id(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Студент не найден"
        )
    return student

@router.get("/by-group/{group_id}", response_model=List[StudentResponse])
async def get_students_by_group(group_id: int):
    """Получить список студентов определенной группы"""
    students = database.get_students_by_group(group_id)
    if not students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Студенты в этой группе не найдены"
        )
    return students

@router.post("/", response_model=StudentResponse, dependencies=[Depends(check_admin_role)])
async def create_student(student: StudentCreate):
    """Создать нового студента (только для администраторов)"""
    try:
        student_id = database.create_student(student.dict())
        return database.get_student_by_id(student_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{student_id}", response_model=StudentResponse, dependencies=[Depends(check_admin_role)])
async def update_student(student_id: int, student: StudentUpdate):
    """Обновить информацию о студенте (только для администраторов)"""
    try:
        student_data = {k: v for k, v in student.dict().items() if v is not None}
        if not student_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указаны данные для обновления"
            )
        updated_id = database.update_student(student_id, student_data)
        student = database.get_student_by_id(updated_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Студент не найден"
            )
        return student
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{student_id}", dependencies=[Depends(check_admin_role)])
async def delete_student(student_id: int):
    """Удалить студента (только для администраторов)"""
    try:
        if database.delete_student(student_id):
            return {"message": "Студент успешно удален"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Студент не найден"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )