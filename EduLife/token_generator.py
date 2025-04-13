import json
import base64
import time
import uuid
import datetime
from typing import Dict, Any

def generate_qr_token(subject_id: int, shift_id: int, teacher_id: int) -> str:
    current_time = time.time()
    expiration_time = current_time + 30

    day_of_week = datetime.datetime.now().weekday()

    token_data = {
        "day_of_week": day_of_week,
        "subject_id": subject_id,
        "shift_id": shift_id,
        "teacher_id": teacher_id,
        "exp": expiration_time,
        "token_id": str(uuid.uuid4())
    }

    token_json = json.dumps(token_data)

    token_bytes = token_json.encode('utf-8')
    token_base64 = base64.urlsafe_b64encode(token_bytes).decode('utf-8')

    return token_base64

def validate_qr_token(token_base64: str) -> Dict[str, Any]:
    try:
        token_bytes = base64.urlsafe_b64decode(token_base64)
        token_json = token_bytes.decode('utf-8')
        token_data = json.loads(token_json)

        current_time = time.time()
        if current_time > token_data.get("exp", 0):
            raise ValueError("Token has expired")
        return token_data
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")