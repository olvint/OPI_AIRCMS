import signal
import multiprocessing
import time
import random
from typing import Dict, List
import threading

from air.sensor import get_air_sensor
from webfront import flaskweb
from senders import sensor_community

def signal_handler(sig, frame):
    print(f"\n🛑 Получен сигнал {sig}, инициируем graceful shutdown...")
    shutdown_flag.value = True
    sys.stdout.flush()


def main():
    """Основная функция, запускающая процессы"""
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


    # Создаем менеджер для разделяемой памяти
    with multiprocessing.Manager() as manager:
        # Создаем разделяемый словарь
        shared_dict = manager.dict()
        
        # Создаем блокировку для безопасного доступа к общим данным
        lock = manager.Lock()
        
        # Запускаем Flask в отдельном потоке
        flask_thread = threading.Thread(
            target=flaskweb.start, 
            args=(shared_dict, lock),
            daemon=True
        )
        flask_thread.start()
        
        # Даем Flask время на запуск
        time.sleep(2)
        
        # Создаем и запускаем процессы
        processes = [
            multiprocessing.Process(target=get_air_sensor, args=(shared_dict, lock)),
            multiprocessing.Process(target=sensor_community.send_data, args=(shared_dict, lock)),

        ]
        
        try:
            print("Запуск процессов...")
            for p in processes:
                p.start()
            
            print("Все процессы запущены")
            print("Веб-интерфейс доступен по адресу: http://localhost:5000")
            print("Нажмите Ctrl+C для остановки")
            
            # Ждем завершения процессов (по Ctrl+C)
            for p in processes:
                p.join()
                
        except Exception as e:
            print(e)
            for p in processes:
                p.terminate()
                p.join()
            print("Все процессы остановлены.")

if __name__ == "__main__":
    main()