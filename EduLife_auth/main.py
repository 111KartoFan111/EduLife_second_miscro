import os
import database
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import bcrypt

from routers import auth, users, teachers, students, groups

# Настройки JWT
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_for_development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Создание приложения FastAPI
app = FastAPI(
    title="EduLife Auth API",
    description="API для аутентификации и управления пользователями в EduLife",
    version="1.0.0"
)

# Инициализация базы данных при запуске
@app.on_event("startup")
def startup_event():
    database.create_tables()

# Подключение роутеров
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(teachers.router)
app.include_router(students.router)
app.include_router(groups.router)

@app.get("/")
def read_root():
    return {"message": "EduLife Auth API", "version": "1.0.0"}