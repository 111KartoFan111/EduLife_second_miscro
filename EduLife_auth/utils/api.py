import os
import requests
from typing import Dict, Any, Optional, List
import json

# Конфигурация
API_TIMEOUT = 10  # Таймаут для API запросов (секунды)

# URL сервисов
RASPIS_API_URL = os.getenv("RASPIS_API_URL", "http://localhost:8090")
QR_API_URL = os.getenv("QR_API_URL", "http://localhost:8080")
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

# API для расписания
def get_schedule(token: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Получает расписание из сервиса расписания"""
    url = f"{RASPIS_API_URL}/schedule"
    return make_api_request("get", url, token=token, params=filters)

def get_student_schedule(token: str, student_id: int) -> List[Dict[str, Any]]:
    """Получает расписание для студента"""
    # Получаем сначала информацию о студенте, чтобы узнать его группу
    student_info = get_student_by_id(token, student_id)
    if not student_info:
        return []
    
    # Запрашиваем расписание для группы студента
    url = f"{RASPIS_API_URL}/schedule"
    params = {"group_id": student_info.get("group_id")}
    return make_api_request("get", url, token=token, params=params)

def get_teacher_schedule(token: str, teacher_id: int) -> List[Dict[str, Any]]:
    """Получает расписание для преподавателя"""
    url = f"{RASPIS_API_URL}/schedule"
    params = {"teacher_id": teacher_id}
    return make_api_request("get", url, token=token, params=params)

# API для управления документами
def get_documents(token: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Получает список документов для пользователя"""
    url = f"{DOCK_API_URL}/documents"
    params = {}
    if user_id:
        params["user_id"] = user_id
    
    return make_api_request("get", url, token=token, params=params)

def create_document(token: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
    """Создает новый документ"""
    url = f"{DOCK_API_URL}/documents"
    return make_api_request("post", url, token=token, data=document_data)

# API для студентов и преподавателей
def get_student_by_id(token: str, student_id: int) -> Dict[str, Any]:
    """Получает информацию о студенте по ID"""
    url = f"{QR_API_URL}/students/{student_id}"
    try:
        return make_api_request("get", url, token=token)
    except APIError:
        return {}

def get_teacher_by_id(token: str, teacher_id: int) -> Dict[str, Any]:
    """Получает информацию о преподавателе по ID"""
    url = f"{QR_API_URL}/teachers/{teacher_id}"
    try:
        return make_api_request("get", url, token=token)
    except APIError:
        return {}

def get_all_subjects(token: str) -> List[Dict[str, Any]]:
    """Получает информацию о всех предметах"""
    url = f"{RASPIS_API_URL}/subjects"
    return make_api_request("get", url, token=token)
