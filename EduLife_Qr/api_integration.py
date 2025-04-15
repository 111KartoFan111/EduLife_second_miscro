import os
import requests
from typing import Dict, Any, Optional, List
import json

# Конфигурация
API_TIMEOUT = 10  # Таймаут для API запросов (секунды)

# URL сервисов
AUTH_API_URL = os.getenv("AUTH_API_URL", "http://localhost:8070")
RASPIS_API_URL = os.getenv("RASPIS_API_URL", "http://localhost:8090")
DOCK_API_URL = os.getenv("DOCK_API_URL", "http://localhost:8100")

class APIError(Exception):
    """Исключение для ошибок API"""
    def __init__(self, message, status_code=None, details=None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

def make_api_request(method: str, url: str, token: Optional[str] = None, 
                     data: Optional[Dict[str, Any]] = None, 
                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Выполняет API запрос к другому сервису"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, params=params, timeout=API_TIMEOUT)
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, json=data, timeout=API_TIMEOUT)
        elif method.lower() == "put":
            response = requests.put(url, headers=headers, json=data, timeout=API_TIMEOUT)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=headers, timeout=API_TIMEOUT)
        else:
            raise ValueError(f"Неподдерживаемый метод HTTP: {method}")
        
        # Проверяем статус ответа
        if response.status_code >= 400:
            try:
                details = response.json()
            except:
                details = {"raw": response.text}
            
            raise APIError(
                f"API вернул ошибку {response.status_code}",
                status_code=response.status_code,
                details=details
            )
        
        # Возвращаем данные ответа
        return response.json()
    
    except requests.RequestException as e:
        raise APIError(f"Ошибка при выполнении API запроса: {str(e)}")

# API авторизации
def verify_token(token: str) -> Dict[str, Any]:
    """Проверяет токен пользователя через сервис авторизации"""
    url = f"{AUTH_API_URL}/auth/me"
    try:
        return make_api_request("get", url, token=token)
    except APIError:
        return {}

def get_user_info(user_id: int, token: str) -> Dict[str, Any]:
    """Получает информацию о пользователе из сервиса авторизации"""
    url = f"{AUTH_API_URL}/users/{user_id}"
    try:
        return make_api_request("get", url, token=token)
    except APIError:
        return {}

# API для взаимодействия с расписанием
def get_user_schedule(user_id: int, token: str) -> List[Dict[str, Any]]:
    """Получает расписание для пользователя из сервиса расписания"""
    # Сначала определяем роль пользователя
    user_info = get_user_info(user_id, token)
    if not user_info:
        return []
    
    role = user_info.get("role_name", "").lower()
    
    if role == "teacher":
        # Получаем сначала ID преподавателя по ID пользователя
        url = f"{AUTH_API_URL}/teachers?user_id={user_id}"
        try:
            teachers = make_api_request("get", url, token=token)
            if teachers and len(teachers) > 0:
                teacher_id = teachers[0].get("id")
                url = f"{RASPIS_API_URL}/schedule"
                params = {"teacher_id": teacher_id}
                return make_api_request("get", url, token=token, params=params)
        except:
            pass
    elif role == "student":
        # Получаем сначала ID студента по ID пользователя
        url = f"{AUTH_API_URL}/students?user_id={user_id}"
        try:
            students = make_api_request("get", url, token=token)
            if students and len(students) > 0:
                student = students[0]
                group_id = student.get("group_id")
                url = f"{RASPIS_API_URL}/schedule"
                params = {"group_id": group_id}
                return make_api_request("get", url, token=token, params=params)
        except:
            pass
    
    # Если не удалось получить расписание специфично для роли,
    # или у пользователя другая роль, возвращаем пустой список
    return []

# Метод для сохранения посещаемости с дополнительной информацией
def save_attendance_with_details(user_id: int, token_data: dict, token: str) -> Dict[str, Any]:
    """
    Сохраняет информацию о посещаемости с обогащенными данными
    из сервиса расписания и авторизации.
    """
    try:
        # Получаем информацию о пользователе
        user_info = get_user_info(user_id, token)
        
        # Получаем дополнительную информацию о занятии из сервиса расписания
        # по ID предмета, учителя и группы
        schedule_info = {}
        url = f"{RASPIS_API_URL}/schedule"
        params = {
            "subject_id": token_data.get("subject_id"),
            "teacher_id": token_data.get("teacher_id"),
        }
        
        try:
            schedules = make_api_request("get", url, token=token, params=params)
            if schedules and len(schedules) > 0:
                schedule_info = schedules[0]
        except:
            pass
        
        # Сохраняем расширенные данные о посещаемости
        # Это локальное сохранение в базу данных QR сервиса
        
        return {
            "user_id": user_id,
            "user_name": user_info.get("full_name", ""),
            "subject_id": token_data.get("subject_id"),
            "subject_name": schedule_info.get("subject_name", ""),
            "teacher_id": token_data.get("teacher_id"),
            "teacher_name": schedule_info.get("teacher_name", ""),
            "day_of_week": token_data.get("day_of_week"),
            "shift_id": token_data.get("shift_id"),
            "timestamp": schedule_info.get("time_start", "")
        }
    except Exception as e:
        raise APIError(f"Ошибка при сохранении расширенных данных о посещаемости: {str(e)}")