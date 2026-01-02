import time
import logging
from smbus2 import SMBus

logger = logging.getLogger(__name__)

class ENS160_AHT21Sensor:
    AHT21_ADDR = 0x38
    ENS160_ADDR = 0x52 # ADD к GND
    
    def __init__(self):
        self.bus = SMBus(1)
        self._init_ens160()
    
    def _init_ens160(self):
        """Инициализация ENS160"""
        try:
            # Сброс
            self.bus.write_byte_data(self.ENS160_ADDR, 0x10, 0xCC)
            time.sleep(0.5)
            # Normal mode
            self.bus.write_byte_data(self.ENS160_ADDR, 0x10, 0x01)
            time.sleep(0.1)
            logger.info("✅ ENS160 инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации ENS160: {e}")
    
    def read_aht21(self):
        """Чтение AHT21"""
        try:
            self.bus.write_i2c_block_data(self.AHT21_ADDR, 0xAC, [0x33, 0x00])
            time.sleep(0.08)
            data = self.bus.read_i2c_block_data(self.AHT21_ADDR, 0x00, 6)
            
            # Корректный парсинг AHT21
            hum_raw = ((data[1] << 12) + (data[2] << 4) + (data[3] >> 4))
            temp_raw = (((data[3] & 0x0F) << 16) + (data[4] << 8) + data[5])
            
            hum = hum_raw / 1048576.0 * 100.0
            temp = temp_raw / 1048576.0 * 200.0 - 50.0
            
            # Валидация
            if 0 <= hum <= 100 and -40 <= temp <= 85:
                return round(temp, 1), round(hum, 1)
            else:
                logger.warning(f"AHT21: некорректные данные temp={temp:.1f} hum={hum:.1f}")
                return None, None
                
        except Exception as e:
            logger.error(f"Ошибка чтения AHT21: {e}")
            return None, None
    
    def read_ens160(self, temp, hum):
        """Чтение ENS160 с обновлением T/H"""
        if temp is None or hum is None:
            return None, None, None
        
        try:
            # 1. Обновляем T/H данные
            temp_k = temp + 273.15
            temp_raw = int(temp_k * 64)
            hum_raw = int(hum * 512)
            
            self.bus.write_i2c_block_data(self.ENS160_ADDR, 0x13, 
                                        [temp_raw & 0xFF, (temp_raw >> 8) & 0xFF])
            self.bus.write_i2c_block_data(self.ENS160_ADDR, 0x15, 
                                        [hum_raw & 0xFF, (hum_raw >> 8) & 0xFF])
            time.sleep(0.1)
            
            # 2. Читаем данные
            aqi = self.bus.read_byte_data(self.ENS160_ADDR, 0x21)
            tvoc_data = self.bus.read_i2c_block_data(self.ENS160_ADDR, 0x22, 2)
            tvoc = (tvoc_data[1] << 8) | tvoc_data[0]
            eco2_data = self.bus.read_i2c_block_data(self.ENS160_ADDR, 0x24, 2)
            eco2 = (eco2_data[1] << 8) | eco2_data[0]
            
            # Валидация
            if aqi == 0 and tvoc == 0 and eco2 == 0:
                logger.debug("ENS160: ожидание инициализации...")
                return None, None, None
            
            logger.debug(f"AQI:{aqi} TVOC:{tvoc}ppb eCO2:{eco2}ppm")
            return aqi, tvoc, eco2
            
        except Exception as e:
            logger.error(f"Ошибка ENS160: {e}")
            return None, None, None
    
    def get_data(self):
        """Получение всех данных"""
        temp, hum = self.read_aht21()
        aqi, tvoc, eco2 = self.read_ens160(temp, hum)
        
        return {
            'temp': temp,
            'hum': hum,
            'aqi': aqi,
            'tvoc': tvoc,
            'eco2': eco2,
            'timestamp': time.time()
        }
    
    def close(self):
        """Закрытие I2C"""
        if hasattr(self, 'bus') and self.bus:
            self.bus.close()

if __name__=='__main__':
    sens=ENS160_AHT21Sensor()
    print(sens.get_data())
