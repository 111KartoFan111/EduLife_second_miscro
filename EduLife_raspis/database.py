import sqlite3
import os
from datetime import datetime

db_path = os.path.join(os.path.dirname(__file__), "seconddata.db")

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Создание таблицы предметов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Создание таблицы аудиторий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    
    # Создание таблицы типов занятий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lesson_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    
    # Создание таблицы расписаний
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            time_start TIME NOT NULL,
            time_end TIME NOT NULL,
            subject_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            classroom_id INTEGER NOT NULL,
            lesson_type_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (classroom_id) REFERENCES classrooms(id),
            FOREIGN KEY (lesson_type_id) REFERENCES lesson_types(id)
        )
    """)
    
    # Создание таблицы для уведомлений
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            change_type TEXT NOT NULL,  -- 'create', 'update', 'delete'
            previous_data TEXT,         -- JSON строка с предыдущими данными (для update/delete)
            new_data TEXT,              -- JSON строка с новыми данными (для create/update)
            is_sent BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (schedule_id) REFERENCES schedule(id)
        )
    """)
    
    # Заполнение таблицы типов занятий, если она пуста
    cursor.execute("SELECT COUNT(*) FROM lesson_types")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO lesson_types (name) VALUES
            ('лекция'),
            ('практика'),
            ('лаб'),
            ('дипломная работа'),
            ('курсовая работа'),
            ('экзамен'),
            ('консультация'),
            ('другой вид занятия')
        """)

    conn.commit()
    conn.close()


def get_schedule(filters=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            s.id, s.date, s.time_start, s.time_end,
            subj.name as subject_name,
            s.teacher_id, s.group_id,
            c.name as classroom_name,
            lt.name as lesson_type
        FROM schedule s
        JOIN subjects subj ON s.subject_id = subj.id
        JOIN classrooms c ON s.classroom_id = c.id
        JOIN lesson_types lt ON s.lesson_type_id = lt.id
    """

    where_clauses = []
    params = []

    if filters:
        if filters.get('date'):
            where_clauses.append("s.date = ?")
            params.append(filters['date'])

        if filters.get('teacher_id'):
            where_clauses.append("s.teacher_id = ?")
            params.append(filters['teacher_id'])

        if filters.get('group_id'):
            where_clauses.append("s.group_id = ?")
            params.append(filters['group_id'])

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY s.date, s.time_start"

    cursor.execute(query, params)
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return result

def get_schedule_by_id(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            s.id, s.date, s.time_start, s.time_end,
            s.subject_id, subj.name as subject_name,
            s.teacher_id, s.group_id,
            s.classroom_id, c.name as classroom_name,
            s.lesson_type_id, lt.name as lesson_type
        FROM schedule s
        JOIN subjects subj ON s.subject_id = subj.id
        JOIN classrooms c ON s.classroom_id = c.id
        JOIN lesson_types lt ON s.lesson_type_id = lt.id
        WHERE s.id = ?
    """

    cursor.execute(query, (schedule_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return dict(result)
    return None

def create_schedule(schedule_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM subjects WHERE id = ?", (schedule_data['subject_id'],))
    if not cursor.fetchone():
        conn.close()
        raise ValueError(f"Subject with id {schedule_data['subject_id']} does not exist")

    cursor.execute("SELECT id FROM classrooms WHERE id = ?", (schedule_data['classroom_id'],))
    if not cursor.fetchone():
        conn.close()
        raise ValueError(f"Classroom with id {schedule_data['classroom_id']} does not exist")

    cursor.execute("SELECT id FROM lesson_types WHERE id = ?", (schedule_data['lesson_type_id'],))
    if not cursor.fetchone():
        conn.close()
        raise ValueError(f"Lesson type with id {schedule_data['lesson_type_id']} does not exist")

    cursor.execute("""
        INSERT INTO schedule (
            date, time_start, time_end, subject_id, teacher_id,
            group_id, classroom_id, lesson_type_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        schedule_data['date'],
        schedule_data['time_start'],
        schedule_data['time_end'],
        schedule_data['subject_id'],
        schedule_data['teacher_id'],
        schedule_data['group_id'],
        schedule_data['classroom_id'],
        schedule_data['lesson_type_id']
    ))

    schedule_id = cursor.lastrowid

    import json
    cursor.execute("""
        INSERT INTO notifications (
            schedule_id, change_type, new_data
        ) VALUES (?, ?, ?)
    """, (
        schedule_id,
        'create',
        json.dumps(schedule_data)
    ))

    conn.commit()
    conn.close()

    return schedule_id

def update_schedule(schedule_id, schedule_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            date, time_start, time_end, subject_id, teacher_id,
            group_id, classroom_id, lesson_type_id
        FROM schedule
        WHERE id = ?
    """, (schedule_id,))

    current_data = cursor.fetchone()
    if not current_data:
        conn.close()
        raise ValueError(f"Schedule with id {schedule_id} does not exist")
    if 'subject_id' in schedule_data:
        cursor.execute("SELECT id FROM subjects WHERE id = ?", (schedule_data['subject_id'],))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Subject with id {schedule_data['subject_id']} does not exist")

    if 'classroom_id' in schedule_data:
        cursor.execute("SELECT id FROM classrooms WHERE id = ?", (schedule_data['classroom_id'],))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Classroom with id {schedule_data['classroom_id']} does not exist")

    if 'lesson_type_id' in schedule_data:
        cursor.execute("SELECT id FROM lesson_types WHERE id = ?", (schedule_data['lesson_type_id'],))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Lesson type with id {schedule_data['lesson_type_id']} does not exist")

    update_fields = []
    update_values = []

    for field in ['date', 'time_start', 'time_end', 'subject_id', 'teacher_id',
                  'group_id', 'classroom_id', 'lesson_type_id']:
        if field in schedule_data:
            update_fields.append(f"{field} = ?")
            update_values.append(schedule_data[field])

    update_fields.append("updated_at = CURRENT_TIMESTAMP")

    if not update_fields:
        conn.close()
        return schedule_id
    cursor.execute(f"""
        UPDATE schedule
        SET {', '.join(update_fields)}
        WHERE id = ?
    """, update_values + [schedule_id])

    import json
    cursor.execute("""
        INSERT INTO notifications (
            schedule_id, change_type, previous_data, new_data
        ) VALUES (?, ?, ?, ?)
    """, (
        schedule_id,
        'update',
        json.dumps(dict(current_data)),
        json.dumps(schedule_data)
    ))

    conn.commit()
    conn.close()

    return schedule_id

def delete_schedule(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            date, time_start, time_end, subject_id, teacher_id,
            group_id, classroom_id, lesson_type_id
        FROM schedule
        WHERE id = ?
    """, (schedule_id,))

    current_data = cursor.fetchone()
    if not current_data:
        conn.close()
        raise ValueError(f"Schedule with id {schedule_id} does not exist")
    import json
    cursor.execute("""
        INSERT INTO notifications (
            schedule_id, change_type, previous_data
        ) VALUES (?, ?, ?)
    """, (
        schedule_id,
        'delete',
        json.dumps(dict(current_data))
    ))
    cursor.execute("DELETE FROM schedule WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    return True

def get_pending_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id, schedule_id, change_type, previous_data, new_data, created_at
        FROM notifications
        WHERE is_sent = 0
        ORDER BY created_at
    """)

    result = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return result

def mark_notifications_as_sent(notification_ids):
    if not notification_ids:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    placeholders = ', '.join(['?' for _ in notification_ids])
    cursor.execute(f"""
        UPDATE notifications
        SET is_sent = 1
        WHERE id IN ({placeholders})
    """, notification_ids)

    conn.commit()
    conn.close()

def get_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM subjects ORDER BY name")
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result

def create_subject(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        subject_id = cursor.lastrowid
        conn.commit()
        return subject_id
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError(f"Subject with name '{name}' already exists")
    finally:
        conn.close()

def get_classrooms():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM classrooms ORDER BY name")
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result

def create_classroom(name):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO classrooms (name) VALUES (?)", (name,))
        classroom_id = cursor.lastrowid
        conn.commit()
        return classroom_id
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError(f"Classroom with name '{name}' already exists")
    finally:
        conn.close()

def get_lesson_types():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM lesson_types ORDER BY name")
    result = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return result