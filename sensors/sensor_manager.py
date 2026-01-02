# import sys
# import os
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)  # На уровень выше
# sys.path.append(parent_dir)


#!/usr/bin/env python3
import time
import logging
from typing import Dict, Any
import multiprocessing

# Импортируем классы сенсоров

from sensors.aht20_bmp280 import AHT20_BMP280
from sensors.ens160 import ENS160
from sensors.sds011 import SDS011
from sensors.cpu_temperature import CPUTemperature

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
        # self.aht20_bmp280 = AHT20_BMP280()
        self.ens160 = ENS160()
        self.sds011 = SDS011()
        self.cpu_temp = CPUTemperature()
        
        print("✅ Все сенсоры инициализированы")
    
    def read_all(self) -> Dict[str, Any]:
        """Чтение всех датчиков"""
        data = {
            'Sensor data': {},
            'Service data': {}
        }
        
        # # 1. Читаем AHT20+BMP280
        # aht_data = self.aht20_bmp280.get_data()
        # if aht_data:
        #     data['Sensor data'].update(aht_data)
        
        # 2. Читаем SDS011
        sds_data = self.sds011.get_data()
        if sds_data:
            data['Sensor data'].update(sds_data)
        
        # 3. Читаем ENS160 (с проверкой наличия данных AHT20)
        temperature = 4
        humidity = 40
        
        if 'AHT20' in data['Sensor data']:
            temp_obj = data['Sensor data']['AHT20'].get('Temperature')
            hum_obj = data['Sensor data']['AHT20'].get('Humidity')
            
            if temp_obj:
                temperature = temp_obj.get('value') 
            else:
                temperature=3       
            if hum_obj:
                humidity = hum_obj.get('value')
            else:
                humidity=50
        
        ens_data = self.ens160.get_data(temperature=temperature, humidity=humidity)
        if ens_data:
            data['Sensor data'].update(ens_data)
        
        # 4. Читаем CPU температуру
        cpu_data = self.cpu_temp.get_data()
        if cpu_data:
            data['Service data'].update(cpu_data)
        
        # 5. Добавляем timestamp
        data['Service data']['timestamp'] = time.time()
        
        return data

    def close(self):
        """Закрытие ресурсов"""
        # self.aht20_bmp280.close()
        self.ens160.close()

    def __del__(self):
        self.close()



def get_sensors_data(shared_dict, lock):
    """Функция для multiprocessing"""
    sensors = None
    try:
        print("🚀 Запуск сенсорного процесса...")
        sensors = Sensors()
      
        while True:
            data = sensors.read_all()
            
            # Безопасная запись в shared_dict
            with lock:
                shared_dict.update(data)
                shared_dict['sensor status'] = {
                    'status': 'OK',
                    'text':'Сенсоры работают штатно',
                    'timestamp': time.time()
                    }
            
            # print(shared_dict)
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("Сенсорный процесс остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка сенсора: {e}", exc_info=True)
        with lock:
            shared_dict['sensnor status'] = {
                    'status': 'Error',
                    'text':'str(e)',
                    'timestamp': time.time()
                    }
    finally:
        if sensors:
            sensors.close()


if __name__ == "__main__":
    # Пример использования (если запустить main.py напрямую)
    sensors = Sensors()
    try:
        while True:
            data = sensors.read_all()
            print(data)
            print(data['Sensor data'])
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nЗавершение работы")
    finally:
        sensors.close()