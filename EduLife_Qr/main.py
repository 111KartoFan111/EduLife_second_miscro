import os
from fastapi import FastAPI, Body, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import database
from datetime import datetime
from typing import Dict, Optional, List
from token_generator import generate_qr_token, validate_qr_token
from api_integration import verify_token, get_user_info, get_user_schedule, save_attendance_with_details

# Настройка порта
PORT = int(os.getenv("PORT", "8080"))

app = FastAPI(
    title="EduLife QR API",
    description="API для генерации и проверки QR-кодов для учета посещаемости",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене следует ограничить список доменов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

used_tokens = set()

class QRRequest(BaseModel):
    subject_id: int
    shift_id: int
    teacher_id: int

class QRResponse(BaseModel):
    qr_code: str

class ValidateRequest(BaseModel):
    user_id: int
    qr_code: str

class ValidateResponse(BaseModel):
    success: bool
    message: str
    session_data: Optional[Dict] = None

class UserSessionsResponse(BaseModel):
    user_id: int
    sessions: List[Dict]

# Функции для проверки авторизации
async def get_current_user(authorization: str = Header(None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Не предоставлен токен авторизации")
    
    token = authorization.replace("Bearer ", "")
    user = verify_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Недействительный токен авторизации")
    
    return user

@app.on_event("startup")
def startup_event():
    database.create_tables()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "qr", "timestamp": datetime.now().isoformat()}

@app.post("/qr", response_model=QRResponse)
def qr_code(request: QRRequest, current_user: dict = Depends(get_current_user)):
    # Проверяем, что у пользователя есть права на создание QR-кода
    if current_user["role_name"] not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания QR-кода")
    
    token = generate_qr_token(
        subject_id=request.subject_id,
        shift_id=request.shift_id,
        teacher_id=request.teacher_id
    )

    return {"qr_code": token}

@app.post("/validate_qr", response_model=ValidateResponse)
def validate_qr_code(
    request: ValidateRequest,
    authorization: str = Header(None)
):
    # Проверяем токен авторизации
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Не предоставлен токен авторизации")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Проверяем QR-код
        token_data = validate_qr_token(request.qr_code)

        token_id = token_data.get("token_id")
        if token_id in used_tokens:
            raise HTTPException(status_code=400, detail="QR-код уже использован")

        used_tokens.add(token_id)

        # Ограничиваем размер set
        current_time = time.time()
        if len(used_tokens) > 1000:
            used_tokens.clear()

        conn = database.get_db_connection()
        try:
            cursor = conn.cursor()

            # Проверяем, существует ли пользователь
            cursor.execute("SELECT * FROM users WHERE id = ?", (request.user_id,))
            user = cursor.fetchone()
            if user is None:
                # Пробуем получить информацию о пользователе через API
                user_info = get_user_info(request.user_id, token)
                if not user_info:
                    raise HTTPException(status_code=404, detail="Пользователь не найден")
                
                # Создаем пользователя в локальной БД
                cursor.execute(
                    "INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                    (request.user_id, user_info.get("username", f"user_{request.user_id}"), "imported_user")
                )
                conn.commit()

            # Сохраняем данные о посещаемости
            cursor.execute(
                """INSERT INTO SESSION_DATA
                   (user_id, session_time, subject_id, shift_id, teacher_id, day_of_week)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    request.user_id,
                    datetime.now(),
                    token_data["subject_id"],
                    token_data["shift_id"],
                    token_data["teacher_id"],
                    token_data["day_of_week"]
                )
            )

            conn.commit()
            
            # Получаем расширенные данные с информацией из других сервисов
            session_data = save_attendance_with_details(request.user_id, token_data, token)
            
            return {
                "success": True,
                "message": "Посещение успешно зафиксировано",
                "session_data": session_data
            }
        finally:
            conn.close()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки запроса: {str(e)}")

@app.get("/sessions/{user_id}", response_model=UserSessionsResponse)
def get_user_sessions(
    user_id: int, 
    current_user: dict = Depends(get_current_user)
):
    # Проверяем права доступа (пользователь может видеть только свои данные, а админ - любые)
    if current_user["id"] != user_id and current_user["role_name"] != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра данных другого пользователя")
    
    sessions = database.get_user_sessions(user_id)
    return {"user_id": user_id, "sessions": sessions}

@app.get("/schedule/{user_id}")
def get_schedule_for_user(
    user_id: int, 
    current_user: dict = Depends(get_current_user),
    authorization: str = Header(None)
):
    # Проверяем права доступа
    if current_user["id"] != user_id and current_user["role_name"] != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра данных другого пользователя")
    
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Не предоставлен токен авторизации")
    
    token = authorization.replace("Bearer ", "")
    
    # Получаем расписание пользователя из сервиса расписания
    schedule = get_user_schedule(user_id, token)
    return {"user_id": user_id, "schedule": schedule}

@app.get("/stats", response_model=Dict)
def get_attendance_stats(
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    # Проверяем, что пользователь имеет права на просмотр статистики
    if current_user["role_name"] not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра статистики")
    
    stats = database.get_session_stats(start_date, end_date)
    return {"stats": stats}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)