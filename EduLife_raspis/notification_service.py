import database
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

# Настройки для отправки уведомлений
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.example.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "notify@example.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your-password")

# API для внешней системы с пользователями и группами
USER_API_URL = os.getenv("USER_API_URL", "https://api.example.com/users")
GROUP_API_URL = os.getenv("GROUP_API_URL", "https://api.example.com/groups")

# API токен для доступа к внешним системам
API_TOKEN = os.getenv("API_TOKEN", "your-api-token")


def format_date(date_str):
    """Форматирует дату в человекочитаемый вид"""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%d.%m.%Y")


def format_time(time_str):
    """Форматирует время в человекочитаемый вид"""
    time_obj = datetime.strptime(time_str, "%H:%M:%S")
    return time_obj.strftime("%H:%M")


def get_teacher_info(teacher_id):
    """Получает информацию о преподавателе из внешней системы"""
    try:
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        response = requests.get(f"{USER_API_URL}/{teacher_id}", headers=headers)
        if response.status_code == 200:
            return response.json()
        return {"id": teacher_id, "name": f"Преподаватель ID:{teacher_id}", "email": None}
    except Exception as e:
        print(f"Ошибка при получении информации о преподавателе: {e}")
        return {"id": teacher_id, "name": f"Преподаватель ID:{teacher_id}", "email": None}


def get_group_info(group_id):
    """Получает информацию о группе из внешней системы"""
    try:
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        response = requests.get(f"{GROUP_API_URL}/{group_id}", headers=headers)
        if response.status_code == 200:
            return response.json()
        return {"id": group_id, "name": f"Группа ID:{group_id}"}
    except Exception as e:
        print(f"Ошибка при получении информации о группе: {e}")
        return {"id": group_id, "name": f"Группа ID:{group_id}"}


def get_group_students(group_id):
    """Получает список студентов группы из внешней системы"""
    try:
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        response = requests.get(f"{GROUP_API_URL}/{group_id}/students", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Ошибка при получении списка студентов группы: {e}")
        return []


def get_subject_name(subject_id):
    """Получает название предмета из базы данных"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM subjects WHERE id = ?", (subject_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result['name'] if result else f"Предмет ID:{subject_id}"


def get_classroom_name(classroom_id):
    """Получает название аудитории из базы данных"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM classrooms WHERE id = ?", (classroom_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result['name'] if result else f"Аудитория ID:{classroom_id}"


def get_lesson_type_name(lesson_type_id):
    """Получает название типа занятия из базы данных"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM lesson_types WHERE id = ?", (lesson_type_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result['name'] if result else f"Тип занятия ID:{lesson_type_id}"


def format_schedule_data(schedule_data):
    """Форматирует данные расписания для уведомления"""
    subject_name = get_subject_name(schedule_data['subject_id'])
    classroom_name = get_classroom_name(schedule_data['classroom_id'])
    lesson_type_name = get_lesson_type_name(schedule_data['lesson_type_id'])
    
    return {
        "date": format_date(schedule_data['date']),
        "time_start": format_time(schedule_data['time_start']),
        "time_end": format_time(schedule_data['time_end']),
        "subject": subject_name,
        "classroom": classroom_name,
        "lesson_type": lesson_type_name
    }


def send_email_notification(recipient_email, subject, message):
    """Отправляет email уведомление"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'html'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Email отправлен на {recipient_email}")
        return True
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")
        return False


def send_telegram_notification(recipient_id, message):
    """Отправляет уведомление через Telegram (пример)"""
    # Здесь должна быть реализация для вашего Telegram бота
    try:
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_bot_token:
            print("Токен Telegram бота не настроен")
            return False
            
        telegram_api_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": recipient_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(telegram_api_url, json=payload)
        if response.status_code == 200:
            print(f"Telegram сообщение отправлено пользователю {recipient_id}")
            return True
        else:
            print(f"Ошибка при отправке в Telegram: {response.text}")
            return False
    except Exception as e:
        print(f"Ошибка при отправке в Telegram: {e}")
        return False


def generate_create_notification_message(schedule_data):
    """Генерирует сообщение о добавлении нового занятия"""
    formatted_data = format_schedule_data(json.loads(schedule_data) if isinstance(schedule_data, str) else schedule_data)
    
    message = f"""
    <h2>Добавлено новое занятие в расписание</h2>
    <p><b>Дата:</b> {formatted_data['date']}</p>
    <p><b>Время:</b> {formatted_data['time_start']} - {formatted_data['time_end']}</p>
    <p><b>Предмет:</b> {formatted_data['subject']}</p>
    <p><b>Тип занятия:</b> {formatted_data['lesson_type']}</p>
    <p><b>Аудитория:</b> {formatted_data['classroom']}</p>
    """
    
    return message


def generate_update_notification_message(previous_data, new_data):
    """Генерирует сообщение об изменении занятия"""
    prev_formatted = format_schedule_data(json.loads(previous_data) if isinstance(previous_data, str) else previous_data)
    new_formatted = {}
    
    new_data_dict = json.loads(new_data) if isinstance(new_data, str) else new_data
    
    # Форматируем только измененные поля
    changes = []
    
    if 'date' in new_data_dict:
        new_formatted['date'] = format_date(new_data_dict['date'])
        if new_formatted['date'] != prev_formatted['date']:
            changes.append(f"Дата: {prev_formatted['date']} → {new_formatted['date']}")
    
    if 'time_start' in new_data_dict:
        new_formatted['time_start'] = format_time(new_data_dict['time_start'])
        if new_formatted['time_start'] != prev_formatted['time_start']:
            changes.append(f"Время начала: {prev_formatted['time_start']} → {new_formatted['time_start']}")
    
    if 'time_end' in new_data_dict:
        new_formatted['time_end'] = format_time(new_data_dict['time_end'])
        if new_formatted['time_end'] != prev_formatted['time_end']:
            changes.append(f"Время окончания: {prev_formatted['time_end']} → {new_formatted['time_end']}")
    
    if 'subject_id' in new_data_dict:
        new_formatted['subject'] = get_subject_name(new_data_dict['subject_id'])
        if new_formatted['subject'] != prev_formatted['subject']:
            changes.append(f"Предмет: {prev_formatted['subject']} → {new_formatted['subject']}")
    
    if 'classroom_id' in new_data_dict:
        new_formatted['classroom'] = get_classroom_name(new_data_dict['classroom_id'])
        if new_formatted['classroom'] != prev_formatted['classroom']:
            changes.append(f"Аудитория: {prev_formatted['classroom']} → {new_formatted['classroom']}")
    
    if 'lesson_type_id' in new_data_dict:
        new_formatted['lesson_type'] = get_lesson_type_name(new_data_dict['lesson_type_id'])
        if new_formatted['lesson_type'] != prev_formatted['lesson_type']:
            changes.append(f"Тип занятия: {prev_formatted['lesson_type']} → {new_formatted['lesson_type']}")
    
    message = f"""
    <h2>Изменения в расписании</h2>
    <p><b>Занятие:</b> {prev_formatted['subject']}, {prev_formatted['date']}, {prev_formatted['time_start']} - {prev_formatted['time_end']}</p>
    <h3>Изменения:</h3>
    <ul>
    """
    
    for change in changes:
        message += f"<li>{change}</li>"
    
    message += """
    </ul>
    """
    
    return message


def generate_delete_notification_message(schedule_data):
    """Генерирует сообщение об удалении занятия"""
    formatted_data = format_schedule_data(json.loads(schedule_data) if isinstance(schedule_data, str) else schedule_data)
    
    message = f"""
    <h2>Отмена занятия</h2>
    <p>Занятие отменено:</p>
    <p><b>Дата:</b> {formatted_data['date']}</p>
    <p><b>Время:</b> {formatted_data['time_start']} - {formatted_data['time_end']}</p>
    <p><b>Предмет:</b> {formatted_data['subject']}</p>
    <p><b>Тип занятия:</b> {formatted_data['lesson_type']}</p>
    <p><b>Аудитория:</b> {formatted_data['classroom']}</p>
    """
    
    return message


def process_notifications():
    """Обрабатывает все непрочитанные уведомления и отправляет их получателям"""
    notifications = database.get_pending_notifications()
    if not notifications:
        print("Нет новых уведомлений для отправки")
        return
    
    processed_notifications = []
    
    for notification in notifications:
        try:
            schedule_id = notification['schedule_id']
            change_type = notification['change_type']
            
            # Получаем данные о расписании
            if change_type == 'create':
                # Для новых занятий
                message = generate_create_notification_message(notification['new_data'])
                subject = "Новое занятие добавлено в расписание"
                
                # Получаем данные о преподавателе и группе
                schedule_data = json.loads(notification['new_data'])
                teacher_info = get_teacher_info(schedule_data['teacher_id'])
                group_info = get_group_info(schedule_data['group_id'])
                
                # Отправляем уведомление преподавателю
                if teacher_info.get('email'):
                    send_email_notification(teacher_info['email'], subject, message)
                
                # Отправляем уведомления студентам группы
                students = get_group_students(schedule_data['group_id'])
                for student in students:
                    if student.get('email'):
                        send_email_notification(student['email'], subject, message)
                    
                    # Если у студентов есть Telegram ID, отправляем им тоже
                    if student.get('telegram_id'):
                        send_telegram_notification(student['telegram_id'], message)
                
            elif change_type == 'update':
                # Для обновленных занятий
                message = generate_update_notification_message(
                    notification['previous_data'], 
                    notification['new_data']
                )
                subject = "Изменения в расписании"
                
                # Получаем данные о преподавателе и группе из предыдущих данных
                prev_data = json.loads(notification['previous_data'])
                teacher_info = get_teacher_info(prev_data['teacher_id'])
                group_info = get_group_info(prev_data['group_id'])
                
                # Отправляем уведомление преподавателю
                if teacher_info.get('email'):
                    send_email_notification(teacher_info['email'], subject, message)
                
                # Отправляем уведомления студентам группы
                students = get_group_students(prev_data['group_id'])
                for student in students:
                    if student.get('email'):
                        send_email_notification(student['email'], subject, message)
                    
                    # Если у студентов есть Telegram ID, отправляем им тоже
                    if student.get('telegram_id'):
                        send_telegram_notification(student['telegram_id'], message)
                
            elif change_type == 'delete':
                # Для удаленных занятий
                message = generate_delete_notification_message(notification['previous_data'])
                subject = "Отмена занятия"
                
                # Получаем данные о преподавателе и группе из предыдущих данных
                prev_data = json.loads(notification['previous_data'])
                teacher_info = get_teacher_info(prev_data['teacher_id'])
                group_info = get_group_info(prev_data['group_id'])
                
                # Отправляем уведомление преподавателю
                if teacher_info.get('email'):
                    send_email_notification(teacher_info['email'], subject, message)
                
                # Отправляем уведомления студентам группы
                students = get_group_students(prev_data['group_id'])
                for student in students:
                    if student.get('email'):
                        send_email_notification(student['email'], subject, message)
                    
                    # Если у студентов есть Telegram ID, отправляем им тоже
                    if student.get('telegram_id'):
                        send_telegram_notification(student['telegram_id'], message)
            
            # Добавляем ID уведомления в список обработанных
            processed_notifications.append(notification['id'])
            
        except Exception as e:
            print(f"Ошибка при обработке уведомления #{notification['id']}: {e}")
    
    # Отмечаем обработанные уведомления как отправленные
    if processed_notifications:
        database.mark_notifications_as_sent(processed_notifications)
        print(f"Успешно обработано и отправлено {len(processed_notifications)} уведомлений")


if __name__ == "__main__":
    # Этот скрипт можно запускать отдельно для обработки всех непрочитанных уведомлений
    process_notifications()