# cpu_temperature_sensor.py
import os
import logging
from typing import Optional
import time

from update_shared_dict import update_sensor_data, update_service_status

logger = logging.getLogger(__name__)

class CPUTemp:
    """Класс для получения температуры процессора"""
    
    def __init__(self, temp_path: str = '/sys/class/thermal/thermal_zone0/temp'):
        self.temp_path = temp_path
    
    def get_data(self) -> Optional[float]:
        """
        Получение температуры процессора
        
        Returns:
            Температура в градусах Цельсия или None при ошибке
        """
        try:
            if os.path.exists(self.temp_path):
                with open(self.temp_path, 'r') as f:
                    temp_millic = int(f.read().strip())
                    temp_c = temp_millic / 1000.0
                    return round(temp_c)
                        
        except Exception as e:
            return e

def start_process(shared_dict, lock):
    process_name = 'CPU_TEMP'
    sensor = None
    
    try:
        print(f"🚀 Запуск {process_name}")
        sensor = CPUTemp()
        
        while True:
            temp_c = sensor.get_data()
            update_service_status(shared_dict, lock, process_name, f'CPU_temp = {temp_c} °C')
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"Процесс {process_name} остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка {process_name}: {e}", exc_info=True)
        update_service_status(shared_dict,lock,process_name, e)

def main():
    sensor = CPUTemperature()
    while True:
        data = sensor.get_data()
        print(data)
        time.sleep(2)

if __name__ == "__main__":
    main()