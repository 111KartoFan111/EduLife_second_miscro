from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import database
from utils.security import authenticate_user, create_access_token, hash_password, get_current_user
from database import create_user, get_user_by_username

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Не найдено"}},
)

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    created_at: datetime

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role_name"]
    }

@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    # Проверяем, не существует ли уже пользователь с таким именем
    existing_user = get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )

    hashed_password = hash_password(user_data.password)

    # Получаем роль студента
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM roles WHERE name = 'student'")
    student_role = cursor.fetchone()
    conn.close()

    if not student_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении роли студента"
        )

    # Создаем пользователя
    try:
        user_id = create_user({
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "password_hash": hashed_password,
            "role_id": student_role["id"],
            "disabled": False
        })
        # Получаем созданного пользователя
        user = database.get_user_by_id(user_id)
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role_name"],
            "created_at": datetime.fromisoformat(user["created_at"])
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role_name"],
        "created_at": datetime.fromisoformat(current_user["created_at"])
    }