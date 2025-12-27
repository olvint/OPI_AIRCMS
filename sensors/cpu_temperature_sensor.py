# cpu_temperature_sensor.py
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class CPUTemperatureSensor:
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
                    
                    # Проверка на разумные значения (обычно 0-100°C для процессора)
                    if 0 <= temp_c <= 100:
                        return round(temp_c, 1)
                    else:
                        logger.warning(f"CPU temp out of range: {temp_c}°C")
                        return None
                        
            logger.warning(f"CPU temp file not found: {self.temp_path}")
            return None
            
        except Exception as e:
            logger.error(f"CPU temp ошибка: {e}")
            return None