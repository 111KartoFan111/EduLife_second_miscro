from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
import json
from typing import Dict, Any, List, Optional
import os

from .security import get_current_user, check_admin_role, check_teacher_or_admin_role

async def get_user_with_permission(permission: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Проверяет, имеет ли пользователь определенное разрешение"""
    # Если пользователь админ, то доступ есть всегда
    if current_user["role_name"] == "admin":
        return current_user
    
    # Проверяем разрешения на основе роли
    permissions = json.loads(current_user["permissions"]) if "permissions" in current_user else {}
    
    # Разбиваем permission на части, например "schedule.read" -> ["schedule", "read"]
    permission_parts = permission.split(".")
    
    # Проверяем, есть ли у пользователя соответствующее разрешение
    current_level = permissions
    for part in permission_parts:
        if isinstance(current_level, dict) and part in current_level:
            current_level = current_level[part]
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав доступа"
            )
    
    if current_level is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    
    return current_user