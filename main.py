import signal
import multiprocessing
import time
import sys
import logging
import threading

# Импорты модулей
from webfront import flaskweb
from sensors.sensor_manager import get_sensors_data

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)

def signal_handler(sig, frame):
    print(f"\n🛑 Получен сигнал {sig}, останавливаю процессы...")
    sys.exit(0)

def check_flask_running(port=5000, timeout=5):
    """Проверка что Flask запустился"""
    import socket
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                return True
        except:
            pass
        
        time.sleep(0.5)
    
    return False

def main():
    """Основная функция, запускающая процессы"""
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Запуск системы мониторинга...")
    
    # Создаем менеджер для разделяемой памяти
    with multiprocessing.Manager() as manager:
        # Создаем разделяемый словарь
        shared_dict = manager.dict()
        
        # Инициализируем начальные данные
        shared_dict.update({
            'Sensor data': {},
            'Service data': {'timestamp': time.time()},
            'sensor status': {
                'status': 'STARTING',
                'text': 'Система запускается',
                'timestamp': time.time()
            }
        })
        
        # Создаем блокировку для безопасного доступа к общим данным
        lock = manager.Lock()
        
        # Запускаем Flask в отдельном потоке
        flask_thread = threading.Thread(
            target=flaskweb.start_flask_in_thread, 
            args=(shared_dict, lock),
            daemon=True
        )
        flask_thread.start()
        
        # Ждем и проверяем запуск Flask
        print("🌐 Запуск веб-интерфейса...")
        time.sleep(2)
        
        if check_flask_running():
            print(f"✅ Веб-интерфейс доступен: http://localhost:5000")
        else:
            print("⚠️  Веб-интерфейс не запустился, продолжаем без него")
        
        # Создаем и запускаем процессы
        processes = []
        
        # Процесс сенсоров
        sensor_process = multiprocessing.Process(
            target=get_sensors_data,
            args=(shared_dict, lock),
            name="SensorManager",
            daemon=True
        )
        processes.append(sensor_process)
        
        # Запускаем все процессы
        print("📡 Запуск процессов сенсоров...")
        for p in processes:
            p.start()
            time.sleep(1)  # Пауза между запусками
        
        # Проверяем что процессы запустились
        for p in processes:
            if p.is_alive():
                print(f"✅ {p.name} запущен")
            else:
                print(f"❌ {p.name} не запустился")
        
        print("\n" + "="*50)
        print("СИСТЕМА ЗАПУЩЕНА")
        print("Нажмите Ctrl+C для остановки")
        print("="*50 + "\n")
        
        try:
            # Основной цикл - просто ждем
            while True:
                # Обновляем статус в shared_dict
                with lock:
                    shared_dict['system status'] = {
                        'status': 'OK',
                        'text': 'Система работает',
                        'timestamp': time.time()
                    }
                
                # Выводим информацию о состоянии
                alive_processes = sum(1 for p in processes if p.is_alive())
                print(f"[{time.strftime('%H:%M:%S')}] Работает процессов: {alive_processes}/{len(processes)}", end='\r')
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Остановка системы...")
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
        finally:
            # Останавливаем процессы
            print("⏹️  Остановка процессов...")
            for p in processes:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=2)
                    if p.is_alive():
                        p.kill()
            
            print("✅ Все процессы остановлены")

if __name__ == "__main__":
    main()