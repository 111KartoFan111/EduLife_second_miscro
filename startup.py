import os
import subprocess
import sys
import time
import signal
import platform

# Конфигурация сервисов
services = [
    {
        "name": "Auth Service",
        "path": "EduLife_auth",
        "command": "..\\venv\\Scripts\\activate.bat && python main.py",
        "port": 8070,
        "process": None
    },

    {
        "name": "QR Service",
        "path": "EduLife_Qr",
        "command": "..\\venv\\Scripts\\activate.bat && python main.py",
        "port": 8080,
        "process": None
    },
    {
        "name": "Schedule Service",
        "path": "EduLife_raspis",
        "command": "..\\venv\\Scripts\\activate.bat && python main.py",
        "port": 8090,
        "process": None
    },
    {
        "name": "Document Service",
        "path": "EduLife_Dock",
        "command": "..\\venv\\Scripts\\activate.bat && python main.py",
        "port": 8100,
        "process": None
    }
]

# Определяем команду для открытия новой консоли в зависимости от ОС
def get_terminal_command(cmd, service_name):
    system = platform.system()
    if system == "Windows":
        return f'start "EduLife {service_name}" cmd /k "{cmd}"'
    elif system == "Darwin":  # macOS
        escaped_cmd = cmd.replace('"', '\\"')
        return f'osascript -e \'tell app "Terminal" to do script "{escaped_cmd}"\''
    else:  # Linux и другие
        terminals = [
            ("gnome-terminal", f'gnome-terminal -- bash -c "{cmd}; exec bash"'),
            ("xterm", f'xterm -title "EduLife {service_name}" -e bash -c "{cmd}; exec bash"'),
            ("konsole", f'konsole -e bash -c "{cmd}; exec bash"'),
            ("terminator", f'terminator -e "bash -c \'{cmd}; exec bash\'"')
        ]
        
        for term, term_cmd in terminals:
            if subprocess.call(["which", term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                return term_cmd
        
        # Если не нашли подходящий терминал, запускаем без новой консоли
        return None

# Устанавливаем переменные окружения с URL для каждого сервиса
def set_environment_variables():
    os.environ["AUTH_API_URL"] = f"http://localhost:{services[0]['port']}"
    os.environ["QR_API_URL"] = f"http://localhost:{services[1]['port']}"
    os.environ["RASPIS_API_URL"] = f"http://localhost:{services[2]['port']}"
    os.environ["DOCK_API_URL"] = f"http://localhost:{services[3]['port']}"

# Запуск всех сервисов в отдельных консолях
def start_services_in_new_terminals():
    for service in services:
        terminal_cmd = get_terminal_command(
            f"cd {service['path']} && {service['command']}",
            service['name']
        )
        
        if terminal_cmd:
            print(f"Запуск {service['name']} в новой консоли на порту {service['port']}...")
            os.system(terminal_cmd)
            time.sleep(1)  # Небольшая задержка между запусками
        else:
            print(f"Не удалось запустить {service['name']} в новой консоли")

# Запуск всех сервисов в фоне (для запуска в одной консоли)
def start_services_in_background():
    for service in services:
        print(f"Запуск {service['name']} на порту {service['port']}...")
        cmd = service['command'].split()
        process = subprocess.Popen(
            cmd,
            cwd=service['path'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        service['process'] = process
        print(f"{service['name']} запущен с PID {process.pid}")

# Остановка всех сервисов
def stop_services():
    for service in services:
        if service['process'] and service['process'].poll() is None:
            print(f"Остановка {service['name']}...")
            try:
                if platform.system() == "Windows":
                    service['process'].terminate()
                else:
                    service['process'].send_signal(signal.SIGTERM)
                service['process'].wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"Не удалось корректно остановить {service['name']}, принудительное завершение...")
                service['process'].kill()

# Обработчик сигналов для корректного завершения
def signal_handler(sig, frame):
    print("\nЗавершение работы...")
    stop_services()
    sys.exit(0)

# Мониторинг вывода всех сервисов
def monitor_outputs():
    try:
        while True:
            for service in services:
                if service['process'] and service['process'].poll() is None:
                    # Чтение stdout
                    output = service['process'].stdout.readline()
                    if output:
                        print(f"[{service['name']}] {output.strip()}")
                    
                    # Чтение stderr
                    error = service['process'].stderr.readline()
                    if error:
                        print(f"[{service['name']}] ERROR: {error.strip()}")
                
                # Если процесс завершился, выводим сообщение
                elif service['process'] and service['process'].poll() is not None:
                    return_code = service['process'].poll()
                    print(f"{service['name']} завершил работу с кодом {return_code}")
                    service['process'] = None
            
            # Небольшая задержка для снижения нагрузки на CPU
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nЗавершение работы по запросу пользователя...")
    finally:
        stop_services()

if __name__ == "__main__":
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Устанавливаем переменные окружения
    set_environment_variables()
    
    print("=== Запуск EduLife микросервисов ===")
    
    # Спрашиваем пользователя о способе запуска
    mode = input("Выберите режим запуска (1 - отдельные консоли, 2 - в одной консоли): ")
    
    if mode == "1":
        start_services_in_new_terminals()
        print("\nВсе сервисы запущены в отдельных консолях.")
        print("Для завершения работы закройте консоли сервисов.")
    else:
        start_services_in_background()
        print("\nВсе сервисы запущены в фоновом режиме.")
        print("Нажмите Ctrl+C для завершения работы всех сервисов.")
        monitor_outputs()