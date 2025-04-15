import os
import database
from fastapi import FastAPI, Body, HTTPException, Depends, Header, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, time, datetime
import json
from api_integration import verify_token, get_teacher_info, get_group_info, send_schedule_notifications, enrich_schedule_data

# Настройка порта
PORT = int(os.getenv("PORT", "8090"))

app = FastAPI(
    title="EduLife Расписание API", 
    description="API для управления расписанием занятий", 
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

class ScheduleBase(BaseModel):
    date: date
    time_start: time
    time_end: time
    subject_id: int
    teacher_id: int
    group_id: int
    classroom_id: int
    lesson_type_id: int


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    date: Optional[date] = None
    time_start: Optional[time] = None
    time_end: Optional[time] = None
    subject_id: Optional[int] = None
    teacher_id: Optional[int] = None
    group_id: Optional[int] = None
    classroom_id: Optional[int] = None
    lesson_type_id: Optional[int] = None


class ScheduleRead(ScheduleBase):
    id: int
    subject_name: str
    classroom_name: str
    lesson_type: str
    teacher_name: Optional[str] = None
    group_name: Optional[str] = None


class NotificationBase(BaseModel):
    id: int
    schedule_id: int
    change_type: str
    previous_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    created_at: datetime


class SubjectBase(BaseModel):
    name: str


class SubjectRead(BaseModel):
    id: int
    name: str


class ClassroomBase(BaseModel):
    name: str


class ClassroomRead(BaseModel):
    id: int
    name: str


class LessonTypeRead(BaseModel):
    id: int
    name: str

# Функция для проверки авторизации
async def get_current_user(authorization: str = Header(None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Не предоставлен токен авторизации")
    
    token = authorization.replace("Bearer ", "")
    user = verify_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Недействительный токен авторизации")
    
    return user

# Функция для проверки прав администратора или преподавателя
async def get_admin_or_teacher(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Требуются права администратора или преподавателя")
    return current_user

# Функция для проверки прав администратора
async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return current_user

# Функция для отправки уведомлений
async def send_notifications(background_tasks: BackgroundTasks, token: str):
    notifications = database.get_pending_notifications()
    if not notifications:
        return

    # Отправляем уведомления через интеграционный слой
    for notification in notifications:
        print(f"Отправка уведомления #{notification['id']}: {notification['change_type']} для расписания #{notification['schedule_id']}")
        send_schedule_notifications(notification, token)

    # Отмечаем уведомления как отправленные
    notification_ids = [n['id'] for n in notifications]
    database.mark_notifications_as_sent(notification_ids)

    print(f"Успешно отправлено {len(notifications)} уведомлений")


@app.on_event("startup")
def startup_event():
    database.create_tables()


# Диагностический эндпоинт
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "raspis", "timestamp": datetime.now().isoformat()}


# Эндпоинты для расписания
@app.get("/schedule", response_model=List[ScheduleRead])
def get_schedule(
    date_filter: Optional[date] = None,
    teacher_id: Optional[int] = None,
    group_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    authorization: str = Header(None)
):
    filters = {}
    if date_filter:
        filters['date'] = date_filter
    if teacher_id:
        filters['teacher_id'] = teacher_id
    if group_id:
        filters['group_id'] = group_id
    
    schedules = database.get_schedule(filters)
    
    # Обогащаем данные расписания информацией о преподавателях и группах
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        enriched_schedules = []
        for schedule in schedules:
            enriched_schedules.append(enrich_schedule_data(schedule, token))
        return enriched_schedules
    
    return schedules


@app.get("/schedule/{schedule_id}", response_model=ScheduleRead)
def get_schedule_by_id(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
    authorization: str = Header(None)
):
    schedule = database.get_schedule_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Расписание с ID {schedule_id} не найдено")
    
    # Обогащаем данные расписания информацией о преподавателе и группе
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        return enrich_schedule_data(schedule, token)
    
    return schedule


@app.post("/schedule", response_model=dict)
async def create_schedule(
    schedule: ScheduleCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_admin_or_teacher),
    authorization: str = Header(None)
):
    try:
        schedule_data = schedule.dict()
        schedule_id = database.create_schedule(schedule_data)
        
        # Запуск отправки уведомлений в фоновом режиме
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            background_tasks.add_task(send_notifications, background_tasks, token)
        
        return {"id": schedule_id, "message": "Расписание успешно создано"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/schedule/{schedule_id}", response_model=dict)
async def update_schedule(
    schedule_id: int,
    schedule: ScheduleUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_admin_or_teacher),
    authorization: str = Header(None)
):
    try:
        schedule_data = {k: v for k, v in schedule.dict().items() if v is not None}
        if not schedule_data:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")
        
        database.update_schedule(schedule_id, schedule_data)
        
        # Запуск отправки уведомлений в фоновом режиме
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            background_tasks.add_task(send_notifications, background_tasks, token)
        
        return {"id": schedule_id, "message": "Расписание успешно обновлено"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/schedule/{schedule_id}", response_model=dict)
async def delete_schedule(
    schedule_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_admin_or_teacher),
    authorization: str = Header(None)
):
    try:
        database.delete_schedule(schedule_id)
        
        # Запуск отправки уведомлений в фоновом режиме
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            background_tasks.add_task(send_notifications, background_tasks, token)
        
        return {"message": f"Расписание с ID {schedule_id} успешно удалено"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Эндпоинты для управления предметами
@app.get("/subjects", response_model=List[SubjectRead])
def get_subjects(current_user: dict = Depends(get_current_user)):
    return database.get_subjects()


@app.post("/subjects", response_model=dict)
def create_subject(
    subject: SubjectBase,
    current_user: dict = Depends(get_admin_user)
):
    try:
        subject_id = database.create_subject(subject.name)
        return {"id": subject_id, "message": "Предмет успешно создан"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Эндпоинты для управления аудиториями
@app.get("/classrooms", response_model=List[ClassroomRead])
def get_classrooms(current_user: dict = Depends(get_current_user)):
    return database.get_classrooms()


@app.post("/classrooms", response_model=dict)
def create_classroom(
    classroom: ClassroomBase,
    current_user: dict = Depends(get_admin_user)
):
    try:
        classroom_id = database.create_classroom(classroom.name)
        return {"id": classroom_id, "message": "Аудитория успешно создана"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Эндпоинт для получения типов занятий
@app.get("/lesson-types", response_model=List[LessonTypeRead])
def get_lesson_types(current_user: dict = Depends(get_current_user)):
    return database.get_lesson_types()


# Эндпоинт для получения уведомлений (для администраторов)
@app.get("/notifications", response_model=List[NotificationBase])
def get_notifications(current_user: dict = Depends(get_admin_user)):
    return database.get_pending_notifications()


# Эндпоинт для ручного запуска рассылки уведомлений (для тестирования)
@app.post("/send-notifications")
async def trigger_notifications(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_admin_user),
    authorization: str = Header(None)
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        background_tasks.add_task(send_notifications, background_tasks, token)
    else:
        raise HTTPException(status_code=401, detail="Не предоставлен токен авторизации")
    
    return {"message": "Отправка уведомлений запущена в фоновом режиме"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)