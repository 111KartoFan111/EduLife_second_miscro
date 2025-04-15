import sqlite3

# Путь к твоей базе данных SQLite
DB_PATH = "main_database.db"  # замени, если другой путь

def add_department():
    name = input("Введите название кафедры: ")
    faculty_id = input("Введите ID факультета: ")
    head_teacher_id = input("Введите ID заведующего кафедрой (можно оставить пустым): ")

    if not name or not faculty_id:
        print("Название и ID факультета обязательны.")
        return

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO departments (name, faculty_id, head_teacher_id)
                VALUES (?, ?, ?)
            """, (
                name.strip(),
                int(faculty_id),
                int(head_teacher_id) if head_teacher_id else None
            ))
            conn.commit()
            print("Кафедра успешно добавлена.")
    except sqlite3.IntegrityError as e:
        print("Ошибка целостности данных:", e)
    except Exception as e:
        print("Ошибка при добавлении:", e)

if __name__ == "__main__":
    add_department()
