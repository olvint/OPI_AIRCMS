#!/usr/bin/env python3
import time
import logging
from typing import Dict, Any
import multiprocessing

# Импортируем классы сенсоров
from sensors.bmp280_sensor import BMP280Sensor
from sensors.sds011_sensor import SDS011Sensor
from sensors.cpu_temperature_sensor import CPUTemperatureSensor

# Настройка логирования только для ошибок
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sensors.log')
    ]
)
logger = logging.getLogger(__name__)


class Sensors:
    """Основной класс для работы со всеми датчиками"""
    
    def __init__(self):
        # Создаем экземпляры сенсоров
        self.bmp280 = BMP280Sensor()
        self.sds011 = SDS011Sensor()
        self.cpu_temp = CPUTemperatureSensor()
        
        print("✅ Все сенсоры инициализированы")
    
    def read_all(self) -> Dict[str, Any]:
        """Чтение всех датчиков"""
        # Используем метод get_data() каждого сенсора
        temp, press = self.bmp280.get_data()
        pm25, pm10 = self.sds011.get_data()
        cpu_temp = self.cpu_temp.get_data()
        
        return {
            'timestamp': time.time(),
            'temperature': temp,
            'pressure': press,
            'pm25': pm25,
            'pm10': pm10,
            'cpu_temp': cpu_temp,
        }
    
    def close(self):
        """Закрытие ресурсов"""
        self.bmp280.close()


def get_sensors_data(shared_dict, lock):
    """Функция для multiprocessing"""
    sensors = None
    try:
        print("🚀 Запуск сенсорного процесса...")
        sensors = Sensors()
        print("✅ HW-611 BMP280 + SDS011 готов")
        
        while True:
            data = sensors.read_all()
            
            # Безопасная запись в shared_dict
            with lock:
                shared_dict.update({
                    'air': {
                        'timestamp': data['timestamp'],
                        'temperature': data['temperature'],
                        'pressure': data['pressure'],
                        'pm25': data['pm25'],
                        'pm10': data['pm10'],
                        'cpu_temp': data['cpu_temp'],
                        'status': 'ok'
                    }
                })
            
            # Форматированный вывод
            # temp_str = f"{data['temperature']:5.1f}".strip() if data['temperature'] else "---- "
            # press_str = f"{data['pressure']:6.1f}".strip() if data['pressure'] else "------ "
            # pm25_str = f"{data['pm25']:5.1f}".strip() if data['pm25'] else "---- "
            # pm10_str = f"{data['pm10']:5.1f}".strip() if data['pm10'] else "---- "
            # cpu_temp_str = f"{data['cpu_temp']:5.1f}".strip() if data['cpu_temp'] else "---- "
            
            # print(f"{time.strftime('%H:%M:%S')} | "
            #       f"T={temp_str}°C | "
            #       f"P={press_str}гПа | "
            #       f"PM2.5={pm25_str} | PM10={pm10_str} | "
            #       f"CPU={cpu_temp_str}°C | ")
            # print("-" * 60)
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("🛑 Сенсорный процесс остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка сенсора: {e}", exc_info=True)
        with lock:
            shared_dict['air'] = {'status': 'error', 'error': str(e)}
    finally:
        if sensors:
            sensors.close()


if __name__ == "__main__":
    # Пример использования (если запустить main.py напрямую)
    sensors = Sensor()
    try:
        while True:
            data = sensor.read_all()
            print(f"Данные: {data}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nЗавершение работы")
    finally:
        sensors.close()