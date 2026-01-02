# sds011_sensor.py
import serial
import struct
import logging
from typing import Optional, Tuple
import time
from update_shared_dict import update_sensor_data, update_service_status


logger = logging.getLogger(__name__)

class SDS011:
    """Класс для работы с датчиком пыли SDS011"""
    
    def __init__(self, port: str = '/dev/ttyS1', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
    
    def get_data(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Получение данных с SDS011
        
        Returns:
            Tuple[PM2.5, PM10] или (None, None) при ошибке
        """
        try:
            with serial.Serial(self.port, self.baudrate, timeout=2) as ser:
                data = ser.read(10)
                
                # Проверка структуры пакета
                if (len(data) == 10 and 
                    data[0] == 0xAA and 
                    data[1] == 0xC0 and 
                    data[9] == 0xAB):
                    
                    pm25 = struct.unpack('<H', data[2:4])[0] / 10.0
                    pm10 = struct.unpack('<H', data[4:6])[0] / 10.0
                    
                    return {'SDS011':{
                                        'pm25':{
                                            'value':round(pm25,2),
                                            'unit':'мкг/м³',
                                            'description':'PM 2.5',
                                            'timestamp':time.time(),
                                        },
                                        'pm10':{
                                            'value':round(pm10,2),
                                            'unit':'мкг/м³',
                                            'description':'PM 10',
                                            'timestamp':time.time(),
                                        }}
                    }
                    
        except Exception as e:
            print(f"SDS011 ошибка: {e}")
            logger.error(f"SDS011 ошибка: {e}")
        
        return None

def start_process(shared_dict, lock):
    process_name = 'SDS011'
    sensor = None
    
    try:
        print(f"🚀 Запуск {process_name}")
        sensor = SDS011()
        
        while True:
            data = sensor.get_data()
            if data:

                update_sensor_data(shared_dict, lock, data)
                update_service_status(shared_dict, lock, process_name,'ОК')

            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"Процесс {process_name} остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка {process_name}: {e}", exc_info=True)
        update_service_status(shared_dict, lock, process_name, e)



def main():
    sensor = SDS011()
    while True:
        data = sensor.get_data()
        print(data)
        time.sleep(2)

if __name__ == "__main__":
    main()