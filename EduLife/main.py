from fastapi import FastAPI, Body, HTTPException, Depends
from pydantic import BaseModel
import time
import database
from datetime import datetime
from typing import Dict, Optional
from token_generator import generate_qr_token, validate_qr_token

app = FastAPI()

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

@app.on_event("startup")
def startup_event():
    database.create_tables()

@app.post("/qr", response_model=QRResponse)
def qr_code(request: QRRequest):
    token = generate_qr_token(
        subject_id=request.subject_id,
        shift_id=request.shift_id,
        teacher_id=request.teacher_id
    )

    return {"qr_code": token}

@app.post("/validate_qr", response_model=ValidateResponse)
def validate_qr_code(request: ValidateRequest):
    try:
        token_data = validate_qr_token(request.qr_code)

        token_id = token_data.get("token_id")
        if token_id in used_tokens:
            raise HTTPException(status_code=400, detail="Token already used")

        used_tokens.add(token_id)

        current_time = time.time()
        if len(used_tokens) > 1000:
            used_tokens.clear()

        conn = database.get_db_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE id = ?", (request.user_id,))
            user = cursor.fetchone()
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")

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
            return {
                "success": True,
                "message": "Attendance recorded successfully",
                "session_data": {
                    "user_id": request.user_id,
                    "subject_id": token_data["subject_id"],
                    "shift_id": token_data["shift_id"],
                    "teacher_id": token_data["teacher_id"],
                    "day_of_week": token_data["day_of_week"],
                    "timestamp": datetime.now().isoformat()
                }
            }
        finally:
            conn.close()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")