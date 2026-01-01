# sds011_sensor.py
import serial
import struct
import logging
from typing import Optional, Tuple

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
                    
                    return round(pm25, 1), round(pm10, 1)
                    
        except Exception as e:
            logger.error(f"SDS011 ошибка: {e}")
        
        return None, None