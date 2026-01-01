# bmp280_sensor.py
import smbus2
import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class BMP280Sensor:
    """Класс для работы с BMP280 (температура и давление)"""
    
    # Константы
    BMP_ADDR = 0x77
    REG_ID = 0xD0
    REG_CTRL_MEAS = 0xF4
    REG_CONFIG = 0xF5
    REG_PRESS_MSB = 0xF7
    DIG_T1 = 0x88
    DIG_T2 = 0x8A
    DIG_T3 = 0x8C
    DIG_P1 = 0x8E
    DIG_P2 = 0x90
    DIG_P3 = 0x92
    DIG_P4 = 0x94
    DIG_P5 = 0x96
    DIG_P6 = 0x98
    DIG_P7 = 0x9A
    DIG_P8 = 0x9C
    DIG_P9 = 0x9E
    
    def __init__(self):
        self.bus = None
        self.dig_T = None
        self.dig_P = None
        self._initialize()
    
    def _initialize(self):
        """Инициализация датчика BMP280"""
        try:
            self.bus = smbus2.SMBus(1)
            chip_id = self.bus.read_byte_data(self.BMP_ADDR, self.REG_ID)
            
            if chip_id != 0x58:
                raise Exception(f"Неправильный ID чипа: 0x{chip_id:02X}")
            
            # Нормальный режим: temp oversampling x1, press oversampling x1
            self.bus.write_byte_data(self.BMP_ADDR, self.REG_CTRL_MEAS, 0x27)
            self.bus.write_byte_data(self.BMP_ADDR, self.REG_CONFIG, 0xA0)
            time.sleep(0.1)
            
            self._load_calibration()
            logger.info("BMP280 инициализирован")
            
        except Exception as e:
            logger.error(f"BMP280 ошибка инициализации: {e}")
            raise
    
    def _read_word_signed(self, reg: int) -> int:
        """Чтение 16-битного знакового значения (little-endian)"""
        data = self.bus.read_i2c_block_data(self.BMP_ADDR, reg, 2)
        value = (data[1] << 8) | data[0]
        if value > 32767:
            value -= 65536
        return value
    
    def _read_word_unsigned(self, reg: int) -> int:
        """Чтение 16-битного беззнакового значения (little-endian)"""
        data = self.bus.read_i2c_block_data(self.BMP_ADDR, reg, 2)
        return (data[1] << 8) | data[0]
    
    def _load_calibration(self):
        """Загрузка калибровочных коэффициентов"""
        self.dig_T = {}
        self.dig_P = {}
        
        self.dig_T['dig_T1'] = self._read_word_unsigned(self.DIG_T1)
        self.dig_T['dig_T2'] = self._read_word_signed(self.DIG_T2)
        self.dig_T['dig_T3'] = self._read_word_signed(self.DIG_T3)
        
        self.dig_P['dig_P1'] = self._read_word_unsigned(self.DIG_P1)
        self.dig_P['dig_P2'] = self._read_word_signed(self.DIG_P2)
        self.dig_P['dig_P3'] = self._read_word_signed(self.DIG_P3)
        self.dig_P['dig_P4'] = self._read_word_signed(self.DIG_P4)
        self.dig_P['dig_P5'] = self._read_word_signed(self.DIG_P5)
        self.dig_P['dig_P6'] = self._read_word_signed(self.DIG_P6)
        self.dig_P['dig_P7'] = self._read_word_signed(self.DIG_P7)
        self.dig_P['dig_P8'] = self._read_word_signed(self.DIG_P8)
        self.dig_P['dig_P9'] = self._read_word_signed(self.DIG_P9)
    
    def _compensate_temperature(self, adc_T: int) -> Tuple[float, float]:
        """Компенсация температуры (алгоритм Bosch)"""
        try:
            var1 = ((adc_T / 16384.0) - (self.dig_T['dig_T1'] / 1024.0)) * self.dig_T['dig_T2']
            var2 = (((adc_T / 131072.0) - (self.dig_T['dig_T1'] / 8192.0)) ** 2) * self.dig_T['dig_T3']
            t_fine = var1 + var2
            temp_C = t_fine / 5120.0
            return temp_C, t_fine
        except Exception as e:
            logger.error(f"Ошибка компенсации температуры: {e}")
            return 0.0, 0.0
    
    def _compensate_pressure(self, adc_P: int, t_fine: float) -> float:
        """Компенсация давления"""
        try:
            var1 = (t_fine / 2.0) - 64000.0
            var2 = var1 * var1 * self.dig_P['dig_P6'] / 32768.0
            var2 = var2 + var1 * self.dig_P['dig_P5'] * 2.0
            var2 = (var2 / 4.0) + (self.dig_P['dig_P4'] * 65536.0)
            
            var1 = (self.dig_P['dig_P3'] * var1 * var1 / 524288.0 + 
                   self.dig_P['dig_P2'] * var1) / 524288.0
            var1 = (1.0 + var1 / 32768.0) * self.dig_P['dig_P1']
            
            if var1 == 0:
                return 0.0
            
            p = 1048576.0 - adc_P
            p = (p - (var2 / 4096.0)) * 6250.0 / var1
            
            var1 = self.dig_P['dig_P9'] * p * p / 2147483648.0
            var2 = p * self.dig_P['dig_P8'] / 32768.0
            p = p + (var1 + var2 + self.dig_P['dig_P7']) / 16.0
            
            return p / 100.0  # hPa
        except Exception as e:
            logger.error(f"Ошибка компенсации давления: {e}")
            return 0.0
    
    def get_data(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Получение данных с BMP280
        
        Returns:
            Tuple[температура_C, давление_гПа] или (None, None) при ошибке
        """
        try:
            # Чтение 6 байт данных
            data = self.bus.read_i2c_block_data(self.BMP_ADDR, self.REG_PRESS_MSB, 6)
            
            # Преобразование сырых данных (20-битные значения)
            adc_P = ((data[0] << 12) | (data[1] << 4) | (data[2] >> 4))
            adc_T = ((data[3] << 12) | (data[4] << 4) | (data[5] >> 4))
            
            # Проверка на нулевые значения
            if adc_T == 0 or adc_P == 0:
                logger.warning("BMP280: нулевые данные ADC")
                return None, None
            
            temp_C, t_fine = self._compensate_temperature(adc_T)
            press_hPa = self._compensate_pressure(adc_P, t_fine)
            
            # Проверка на разумные значения
            if not (-40 <= temp_C <= 85) or not (300 <= press_hPa <= 1100):
                logger.warning(f"BMP280: некорректные значения T={temp_C:.1f}°C, P={press_hPa:.1f}гПа")
                return None, None
            
            return round(temp_C, 2), round(press_hPa, 2)
            
        except Exception as e:
            logger.error(f"BMP280 ошибка чтения: {e}")
            return None, None
    
    def close(self):
        """Закрытие ресурсов"""
        if self.bus:
            self.bus.close()

    def __del__(self):
        self.close()        

if __name__ == "__main__":
    # Настройка логирования для теста
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    sensor = None
    try:
        sensor = BMP280Sensor()
        print("✅ BMP280 запущен. Нажмите Ctrl+C для остановки.\n")
        
        while True:
            temp, press = sensor.get_data()
            if temp is not None and press is not None:
                print(f"🌡️ Температура: {temp:.2f} °C  |  📉 Давление: {press:.2f} гПа")
            else:
                print("⚠️ Ошибка чтения данных с BMP280")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n🛑 Остановка по запросу пользователя...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if sensor:
            sensor.close()
        print("🔌 BMP280 закрыт.")
