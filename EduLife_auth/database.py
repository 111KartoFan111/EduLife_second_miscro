import sqlite3
import os
from datetime import datetime
import json

db_path = os.path.join(os.path.dirname(__file__), "main_database.db")

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Таблица ролей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            permissions TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            disabled BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
    """)

    # Таблица факультетов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица кафедр
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            faculty_id INTEGER NOT NULL,
            head_teacher_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculties(id),
            FOREIGN KEY (head_teacher_id) REFERENCES teachers(id)
        )
    """)

    # Таблица групп
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            faculty_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculties(id)
        )
    """)

    # Таблица учителей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            department_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            contact_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)

    # Таблица студентов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            group_id INTEGER NOT NULL,
            student_id TEXT NOT NULL UNIQUE,
            enrollment_year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (group_id) REFERENCES groups(id)
        )
    """)

    # Таблица предметов (для связи с учителями)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица связи учителей и предметов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(teacher_id, subject_id),
            FOREIGN KEY (teacher_id) REFERENCES teachers(id),
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    """)

    # Таблица токенов аутентификации
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Таблица сброса пароля
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reset_token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Таблица настроек пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            notification_preferences TEXT NOT NULL,
            theme TEXT DEFAULT 'default',
            language TEXT DEFAULT 'ru',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Создаем базовые роли, если их нет
    cursor.execute("SELECT COUNT(*) FROM roles")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO roles (name, permissions) VALUES
            ('admin', '{"all": true}'),
            ('teacher', '{"schedule": {"read": true, "create": true, "update": true}, "attendance": {"read": true, "create": true, "update": true}}'),
            ('student', '{"schedule": {"read": true}, "attendance": {"read": true}}')
        """)

    conn.commit()
    conn.close()

# Функции для работы с пользователями
def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            u.id, u.username, u.email, u.full_name, u.password_hash, 
            u.role_id, r.name as role_name, u.disabled, u.created_at
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.username = ?
    """, (username,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            u.id, u.username, u.email, u.full_name, 
            u.role_id, r.name as role_name, u.disabled, u.created_at
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.id = ?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def create_user(user_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (username, email, full_name, password_hash, role_id, disabled)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_data["username"],
            user_data["email"],
            user_data["full_name"],
            user_data["password_hash"],
            user_data["role_id"],
            user_data.get("disabled", False)
        ))
        user_id = cursor.lastrowid
        
        # Создаем настройки пользователя по умолчанию
        cursor.execute("""
            INSERT INTO user_settings (user_id, notification_preferences)
            VALUES (?, ?)
        """, (user_id, json.dumps({"email": True, "telegram": False})))
        
        conn.commit()
        return user_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "username" in str(e):
            raise ValueError("Пользователь с таким именем уже существует")
        elif "email" in str(e):
            raise ValueError("Пользователь с такой почтой уже существует")
        else:
            raise ValueError(str(e))
    finally:
        conn.close()

def update_user(user_id, user_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        update_fields = []
        update_values = []
        
        for field, value in user_data.items():
            if field in ["username", "email", "full_name", "role_id", "disabled"]:
                update_fields.append(f"{field} = ?")
                update_values.append(value)
        
        if not update_fields:
            return user_id
        
        update_values.append(user_id)
        cursor.execute(f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """, update_values)
        
        conn.commit()
        return user_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "username" in str(e):
            raise ValueError("Пользователь с таким именем уже существует")
        elif "email" in str(e):
            raise ValueError("Пользователь с такой почтой уже существует")
        else:
            raise ValueError(str(e))
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM password_reset WHERE user_id = ?", (user_id,))
        
        # Проверяем, есть ли связанный учитель
        cursor.execute("SELECT id FROM teachers WHERE user_id = ?", (user_id,))
        teacher = cursor.fetchone()
        if teacher:
            teacher_id = teacher["id"]
            cursor.execute("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
            cursor.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
        
        # Проверяем, есть ли связанный студент
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (user_id,))
        student = cursor.fetchone()
        if student:
            cursor.execute("DELETE FROM students WHERE id = ?", (student["id"],))
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise ValueError(f"Ошибка при удалении пользователя: {str(e)}")
    finally:
        conn.close()

# Функции для работы с группами
def get_all_groups():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.id, g.name, g.year, g.faculty_id, f.name as faculty_name
        FROM groups g
        JOIN faculties f ON g.faculty_id = f.id
        ORDER BY g.name
    """)
    groups = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return groups

def get_group_by_id(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.id, g.name, g.year, g.faculty_id, f.name as faculty_name
        FROM groups g
        JOIN faculties f ON g.faculty_id = f.id
        WHERE g.id = ?
    """, (group_id,))
    group = cursor.fetchone()
    conn.close()
    if group:
        return dict(group)
    return None

def create_group(group_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO groups (name, faculty_id, year)
            VALUES (?, ?, ?)
        """, (
            group_data["name"],
            group_data["faculty_id"],
            group_data["year"]
        ))
        group_id = cursor.lastrowid
        conn.commit()
        return group_id
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError(f"Группа с названием '{group_data['name']}' уже существует")
    finally:
        conn.close()

def update_group(group_id, group_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        update_fields = []
        update_values = []
        
        for field, value in group_data.items():
            if field in ["name", "faculty_id", "year"]:
                update_fields.append(f"{field} = ?")
                update_values.append(value)
        
        if not update_fields:
            return group_id
        
        update_values.append(group_id)
        cursor.execute(f"""
            UPDATE groups 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """, update_values)
        
        conn.commit()
        return group_id
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError(f"Группа с названием '{group_data.get('name')}' уже существует")
    finally:
        conn.close()

def delete_group(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Проверяем, есть ли студенты в этой группе
        cursor.execute("SELECT COUNT(*) FROM students WHERE group_id = ?", (group_id,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            raise ValueError("Невозможно удалить группу, в которой есть студенты")
        
        cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise ValueError(f"Ошибка при удалении группы: {str(e)}")
    finally:
        conn.close()

# Функции для работы с учителями
def get_all_teachers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            t.id, t.user_id, t.position, t.contact_info,
            u.full_name, u.email, d.id as department_id, d.name as department_name
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        JOIN departments d ON t.department_id = d.id
        ORDER BY u.full_name
    """)
    teachers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return teachers

def get_teacher_by_id(teacher_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            t.id, t.user_id, t.position, t.contact_info, t.department_id,
            u.full_name, u.email, u.username, d.name as department_name
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        JOIN departments d ON t.department_id = d.id
        WHERE t.id = ?
    """, (teacher_id,))
    teacher = cursor.fetchone()
    
    if teacher:
        teacher_dict = dict(teacher)
        
        # Получаем предметы, которые ведет учитель
        cursor.execute("""
            SELECT s.id, s.name
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            WHERE ts.teacher_id = ?
        """, (teacher_id,))
        teacher_dict["subjects"] = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return teacher_dict
    conn.close()
    return None

def create_teacher(teacher_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE id = ?", (teacher_data["user_id"],))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Пользователь с ID {teacher_data['user_id']} не существует")
        # Проверяем, существует ли кафедра
        cursor.execute("SELECT id FROM departments WHERE id = ?", (teacher_data["department_id"],))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Кафедра с ID {teacher_data['department_id']} не существует")
        # Проверяем, не создан ли уже учитель для этого пользователя
        cursor.execute("SELECT id FROM teachers WHERE user_id = ?", (teacher_data["user_id"],))
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"Учитель для пользователя с ID {teacher_data['user_id']} уже существует")
        cursor.execute("""
            INSERT INTO teachers (user_id, department_id, position, contact_info)
            VALUES (?, ?, ?, ?)
        """, (
            teacher_data["user_id"],
            teacher_data["department_id"],
            teacher_data["position"],
            teacher_data.get("contact_info", "")
        ))
        teacher_id = cursor.lastrowid
        # Добавляем предметы, если они указаны
        if "subject_ids" in teacher_data and teacher_data["subject_ids"]:
            for subject_id in teacher_data["subject_ids"]:
                cursor.execute("SELECT id FROM subjects WHERE id = ?", (subject_id,))
                if not cursor.fetchone():
                    conn.rollback()
                    conn.close()
                    raise ValueError(f"Предмет с ID {subject_id} не существует")
                cursor.execute("""
                    INSERT INTO teacher_subjects (teacher_id, subject_id)
                    VALUES (?, ?)
                """, (teacher_id, subject_id))
        # Обновляем роль пользователя на учителя, если она не администратор
        cursor.execute("SELECT role_id FROM users WHERE id = ?", (teacher_data["user_id"],))
        user_role = cursor.fetchone()["role_id"]
        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_role_id = cursor.fetchone()["id"]
        if user_role != admin_role_id:
            cursor.execute("SELECT id FROM roles WHERE name = 'teacher'")
            teacher_role_id = cursor.fetchone()["id"]
            cursor.execute("UPDATE users SET role_id = ? WHERE id = ?", (teacher_role_id, teacher_data["user_id"]))
        conn.commit()
        return teacher_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Ошибка при создании учителя: {str(e)}")
    finally:
        conn.close()

def update_teacher(teacher_id, teacher_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        update_fields = []
        update_values = []
        
        for field, value in teacher_data.items():
            if field in ["department_id", "position", "contact_info"]:
                update_fields.append(f"{field} = ?")
                update_values.append(value)
        
        if update_fields:
            update_values.append(teacher_id)
            cursor.execute(f"""
                UPDATE teachers 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """, update_values)
        
        # Обновляем предметы, если они указаны
        if "subject_ids" in teacher_data:
            # Удаляем все текущие связи
            cursor.execute("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
            
            # Добавляем новые связи
            for subject_id in teacher_data["subject_ids"]:
                cursor.execute("SELECT id FROM subjects WHERE id = ?", (subject_id,))
                if not cursor.fetchone():
                    conn.rollback()
                    conn.close()
                    raise ValueError(f"Предмет с ID {subject_id} не существует")
                
                cursor.execute("""
                    INSERT INTO teacher_subjects (teacher_id, subject_id)
                    VALUES (?, ?)
                """, (teacher_id, subject_id))
        
        conn.commit()
        return teacher_id
    except Exception as e:
        conn.rollback()
        raise ValueError(f"Ошибка при обновлении учителя: {str(e)}")
    finally:
        conn.close()

def delete_teacher(teacher_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Проверяем, есть ли заведующие кафедрами с этим ID
        cursor.execute("SELECT COUNT(*) FROM departments WHERE head_teacher_id = ?", (teacher_id,))
        if cursor.fetchone()[0] > 0:
            cursor.execute("UPDATE departments SET head_teacher_id = NULL WHERE head_teacher_id = ?", (teacher_id,))
        
        # Удаляем связи с предметами
        cursor.execute("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
        
        # Получаем user_id перед удалением учителя
        cursor.execute("SELECT user_id FROM teachers WHERE id = ?", (teacher_id,))
        user_id_row = cursor.fetchone()
        if not user_id_row:
            conn.close()
            raise ValueError(f"Учитель с ID {teacher_id} не найден")
        
        user_id = user_id_row["user_id"]
        
        # Удаляем учителя
        cursor.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
        
        # Сбрасываем роль пользователя на студента, если нет другой роли
        cursor.execute("SELECT id FROM roles WHERE name = 'student'")
        student_role_id = cursor.fetchone()["id"]
        cursor.execute("UPDATE users SET role_id = ? WHERE id = ?", (student_role_id, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise ValueError(f"Ошибка при удалении учителя: {str(e)}")
    finally:
        conn.close()

# Функции для работы со студентами
def get_all_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            s.id, s.user_id, s.group_id, s.student_id, s.enrollment_year,
            u.full_name, u.email,
            g.name as group_name, g.year as group_year,
            f.id as faculty_id, f.name as faculty_name
        FROM students s
        JOIN users u ON s.user_id = u.id
        JOIN groups g ON s.group_id = g.id
        JOIN faculties f ON g.faculty_id = f.id
        ORDER BY u.full_name
    """)
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return students

def get_student_by_id(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            s.id, s.user_id, s.group_id, s.student_id, s.enrollment_year,
            u.full_name, u.email, u.username,
            g.name as group_name, g.year as group_year,
            f.id as faculty_id, f.name as faculty_name
        FROM students s
        JOIN users u ON s.user_id = u.id
        JOIN groups g ON s.group_id = g.id
        JOIN faculties f ON g.faculty_id = f.id
        WHERE s.id = ?
    """, (student_id,))
    student = cursor.fetchone()
    conn.close()
    if student:
        return dict(student)
    return None

def get_students_by_group(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            s.id, s.user_id, s.student_id, s.enrollment_year,
            u.full_name, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.group_id = ?
        ORDER BY u.full_name
    """, (group_id,))
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return students

def create_student(student_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE id = ?", (student_data["user_id"],))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Пользователь с ID {student_data['user_id']} не существует")
        
        # Проверяем, существует ли группа
        cursor.execute("SELECT id FROM groups WHERE id = ?", (student_data["group_id"],))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Группа с ID {student_data['group_id']} не существует")
        
        # Проверяем, не создан ли уже студент для этого пользователя
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (student_data["user_id"],))
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"Студент для пользователя с ID {student_data['user_id']} уже существует")
        cursor.execute("SELECT id FROM students WHERE student_id = ?", (student_data["student_id"],))
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"Студент с номером '{student_data['student_id']}' уже существует")
        cursor.execute("""
            INSERT INTO students (user_id, group_id, student_id, enrollment_year)
            VALUES (?, ?, ?, ?)
        """, (
            student_data["user_id"],
            student_data["group_id"],
            student_data["student_id"],
            student_data["enrollment_year"]
        ))
        student_id = cursor.lastrowid

        cursor.execute("SELECT role_id FROM users WHERE id = ?", (student_data["user_id"],))
        user_role = cursor.fetchone()["role_id"]

        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_role_id = cursor.fetchone()["id"]

        cursor.execute("SELECT id FROM roles WHERE name = 'teacher'")
        teacher_role_id = cursor.fetchone()["id"]

        if user_role != admin_role_id and user_role != teacher_role_id:
            cursor.execute("SELECT id FROM roles WHERE name = 'student'")
            student_role_id = cursor.fetchone()["id"]
            cursor.execute("UPDATE users SET role_id = ? WHERE id = ?", (student_role_id, student_data["user_id"]))
        conn.commit()
        return student_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Ошибка при создании студента: {str(e)}")
    finally:
        conn.close()

def update_student(student_id, student_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        update_fields = []
        update_values = []
        
        for field, value in student_data.items():
            if field in ["group_id", "student_id", "enrollment_year"]:
                update_fields.append(f"{field} = ?")
                update_values.append(value)
        
        if not update_fields:
            return student_id
        
        update_values.append(student_id)
        cursor.execute(f"""
            UPDATE students
            SET {', '.join(update_fields)}
            WHERE id = ?
        """, update_values)
        
        conn.commit()
        return student_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "student_id" in str(e):
            raise ValueError(f"Студент с номером '{student_data.get('student_id')}' уже существует")
        else:
            raise ValueError(f"Ошибка при обновлении студента: {str(e)}")
    finally:
        conn.close()


# Добавьте в database.py
def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            u.id, u.username, u.email, u.full_name,
            u.role_id, r.name as role_name, u.disabled, u.created_at
        FROM users u
        JOIN roles r ON u.role_id = r.id
        ORDER BY u.username
    """)
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM students WHERE id = ?", (student_id,))
        user_id_row = cursor.fetchone()
        if not user_id_row:
            conn.close()
            raise ValueError(f"Студент с ID {student_id} не найден")

        user_id = user_id_row["user_id"]

        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))

        cursor.execute("SELECT COUNT(*) FROM teachers WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT id FROM roles WHERE name = 'student'")
            basic_role_id = cursor.fetchone()["id"]
            cursor.execute("UPDATE users SET role_id = ? WHERE id = ?", (basic_role_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise ValueError(f"Ошибка при удалении студента: {str(e)}")
    finally:
        conn.close()