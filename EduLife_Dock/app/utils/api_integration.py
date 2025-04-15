import os
import requests
from typing import Dict, Any, Optional, List
import json

# Конфигурация
API_TIMEOUT = 10  # Таймаут для API запросов (секунды)

# URL сервисов
AUTH_API_URL = os.getenv("AUTH_API_URL", "http://localhost:8070")
RASPIS_API_URL = os.getenv("RASPIS_API_URL", "http://localhost:8090")
QR_API_URL = os.getenv("QR_API_URL", "http://localhost:8080")

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

# API для получения информации о студентах и преподавателях
def get_student_info(student_id: int, token: str) -> Dict[str, Any]:
    """Получает информацию о студенте из сервиса авторизации"""
    url = f"{AUTH_API_URL}/students/{student_id}"
    try:
        return make_api_request("get", url, token=token)
    except APIError:
        return {}

def get_teacher_info(teacher_id: int, token: str) -> Dict[str, Any]:
    """Получает информацию о преподавателе из сервиса авторизации"""
    url = f"{AUTH_API_URL}/teachers/{teacher_id}"
    try:
        return make_api_request("get", url, token=token)
    except APIError:
        return {}

def get_group_info(group_id: int, token: str) -> Dict[str, Any]:
    """Получает информацию о группе из сервиса авторизации"""
    url = f"{AUTH_API_URL}/groups/{group_id}"
    try:
        return make_api_request("get", url, token=token)
    except APIError:
        return {}

# API для интеграции с расписанием
def get_schedule_for_user(user_id: int, token: str) -> List[Dict[str, Any]]:
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

# API для интеграции с посещаемостью
def get_user_attendance(user_id: int, token: str) -> List[Dict[str, Any]]:
    """Получает статистику посещаемости для пользователя из QR сервиса"""
    url = f"{QR_API_URL}/attendance/{user_id}"
    try:
        return make_api_request("get", url, token=token)
    except APIError:
        return []