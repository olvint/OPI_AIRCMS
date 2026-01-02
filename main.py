import signal
import multiprocessing
import time
import sys
import logging
import threading

# Импорты модулей
from webfront import flaskweb

from sensors import aht20_bmp280
from sensors import ens160
from sensors import sds011
from sensors import cpu_temperature

from senders import sensor_community

from update_shared_dict import update_service_status

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

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
            'Service data': {},
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
        
        # Процесс сенсора aht20_bmp280
        aht20_bmp280_process = multiprocessing.Process(
            target=aht20_bmp280.start_process,
            args=(shared_dict, lock),
            name="aht20_bmp280",
            daemon=True
        )
        processes.append(aht20_bmp280_process)

        # Процесс сенсора ens160
        ens160_process = multiprocessing.Process(
            target=ens160.start_process,
            args=(shared_dict, lock),
            name="ens160",
            daemon=True
        )
        processes.append(ens160_process)


        # Процесс сенсора sds011
        sds011_process = multiprocessing.Process(
            target=sds011.start_process,
            args=(shared_dict, lock),
            name="sds011",
            daemon=True
        )
        processes.append(sds011_process)


        # Процесс Датчика температуры
        cputemp_process = multiprocessing.Process(
            target=cpu_temperature.start_process,
            args=(shared_dict, lock),
            name="cputemp",
            daemon=True
        )
        processes.append(cputemp_process)

        # Процесс отправки данных
        sensor_community_process = multiprocessing.Process(
            target=sensor_community.send_data,
            args=(shared_dict, lock),
            name="sensor_community",
            daemon=True
        )
        processes.append(sensor_community_process)


        
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
                # Выводим информацию о состоянии
                alive_processes = sum(1 for p in processes if p.is_alive())
                update_service_status(shared_dict, lock, 'Main',f"Работает процессов: {alive_processes}/{len(processes)}")
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Остановка системы...")
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            logger.error(e)
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