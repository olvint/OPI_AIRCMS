#!/usr/bin/env python3
import smbus2
import time
import serial
import struct
import logging
from typing import Optional, Tuple, Dict, Any
import multiprocessing
import os



# I2C адрес BMP280
BMP_ADDR = 0x76


# Регистры BMP280
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


# Настройка логирования только для ошибок
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('airsensor.log')
    ]
)
logger = logging.getLogger(__name__)





class AirSensor:
    """Класс для работы с BMP280 + SDS011"""
    
    def __init__(self):
        self.bus = None
        self.dig_T = None
        self.dig_P = None
        self._init_sensors()
    
    def _read_word_signed(self, reg: int) -> int:
        """Чтение 16-битного знакового значения (little-endian)"""
        data = self.bus.read_i2c_block_data(BMP_ADDR, reg, 2)
        value = (data[1] << 8) | data[0]  # little-endian
        if value > 32767:  # Проверка на отрицательное число
            value -= 65536
        return value
    
    def _read_word_unsigned(self, reg: int) -> int:
        """Чтение 16-битного беззнакового значения (little-endian)"""
        data = self.bus.read_i2c_block_data(BMP_ADDR, reg, 2)
        return (data[1] << 8) | data[0]
    
    def _init_bmp280(self):
        """Инициализация BMP280"""
        try:
            self.bus = smbus2.SMBus(0)
            chip_id = self.bus.read_byte_data(BMP_ADDR, REG_ID)
            print(f"BMP280 ID: 0x{chip_id:02X} (ожидается 0x58)")
            
            if chip_id != 0x58:
                raise Exception(f"Неправильный ID чипа: 0x{chip_id:02X}")
            
            # Нормальный режим: temp oversampling x1, press oversampling x1
            self.bus.write_byte_data(BMP_ADDR, REG_CTRL_MEAS, 0x27)
            self.bus.write_byte_data(BMP_ADDR, REG_CONFIG, 0xA0)
            time.sleep(0.1)
            print("✅ BMP280 инициализирован")
        except Exception as e:
            logger.error(f"BMP280 ошибка инициализации: {e}")
            raise
    
    def _load_calibration(self):
        """Загрузка калибровочных коэффициентов"""
        try:
            self.dig_T = {}
            self.dig_P = {}
            
            # Чтение калибровочных данных
            self.dig_T['dig_T1'] = self._read_word_unsigned(DIG_T1)
            self.dig_T['dig_T2'] = self._read_word_signed(DIG_T2)
            self.dig_T['dig_T3'] = self._read_word_signed(DIG_T3)
            
            self.dig_P['dig_P1'] = self._read_word_unsigned(DIG_P1)
            self.dig_P['dig_P2'] = self._read_word_signed(DIG_P2)
            self.dig_P['dig_P3'] = self._read_word_signed(DIG_P3)
            self.dig_P['dig_P4'] = self._read_word_signed(DIG_P4)
            self.dig_P['dig_P5'] = self._read_word_signed(DIG_P5)
            self.dig_P['dig_P6'] = self._read_word_signed(DIG_P6)
            self.dig_P['dig_P7'] = self._read_word_signed(DIG_P7)
            self.dig_P['dig_P8'] = self._read_word_signed(DIG_P8)
            self.dig_P['dig_P9'] = self._read_word_signed(DIG_P9)
            
            print("✅ Калибровка загружена")
            print(f"dig_T1: {self.dig_T['dig_T1']}")
            print(f"dig_T2: {self.dig_T['dig_T2']}")
            print(f"dig_T3: {self.dig_T['dig_T3']}")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки калибровки: {e}")
            raise
    
    def _init_sensors(self):
        """Инициализация всех датчиков"""
        self._init_bmp280()
        self._load_calibration()
    
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
    
    def read_bmp280(self) -> Tuple[Optional[float], Optional[float]]:
        """Чтение BMP280"""
        try:
            # Чтение 6 байт данных
            data = self.bus.read_i2c_block_data(BMP_ADDR, REG_PRESS_MSB, 6)
            
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
    
    def read_sds011(self) -> Tuple[Optional[float], Optional[float]]:
        try:
            with serial.Serial('/dev/ttyS1', 9600, timeout=2) as ser:
                data = ser.read(10)
                if (len(data) == 10 and data[0] == 0xAA and data[1] == 0xC0 and 
                    data[9] == 0xAB):  # упрощенный чек
                    pm25 = struct.unpack('<H', data[2:4])[0] / 10.0
                    pm10 = struct.unpack('<H', data[4:6])[0] / 10.0
                    
                    return round(pm25, 1), round(pm10, 1)
        except Exception as e:
            logger.error(f"SDS011: {e}")
        return None, None
    
    
    def read_cpu_temperature(self) -> Optional[float]:
        """Получение температуры процессора в градусах Цельсия"""
        try:
            # Путь к файлу температуры процессора
            temp_path = '/sys/class/thermal/thermal_zone0/temp'
            

            if os.path.exists(temp_path):
                with open(temp_path, 'r') as f:
                    temp_millic = int(f.read().strip())
                    temp_c = temp_millic / 1000.0

                    # Проверка на разумные значения (обычно 0-100°C для процессора)
                    return round(temp_c, 1)
    
            return None
        except Exception as e:
            logger.error(f"cpu_temp: {e}")
        return None
    
    def read_all(self) -> Dict[str, Any]:
        """Чтение всех датчиков"""
        temp, press = self.read_bmp280()
        pm25, pm10 = self.read_sds011()
        cpu_temp=self.read_cpu_temperature()
        
        return {
            'timestamp': time.time(),
            'temperature': temp,
            'pressure': press,
            'pm25': pm25,
            'pm10': pm10,
            'cpu_temp':cpu_temp,
            
        }
    
    def close(self):
        """Закрытие ресурсов"""
        if self.bus:
            self.bus.close()


def get_air_sensor(shared_dict, lock):
    """Функция для multiprocessing"""
    sensor = None
    try:
        print("🚀 Запуск сенсорного процесса...")
        sensor = AirSensor()
        print("✅ HW-611 BMP280 + SDS011 готов")
        
        while True:
            data = sensor.read_all()
            
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
            temp_str = f"{data['temperature']:5.1f}".strip() if data['temperature'] else "---- "
            press_str = f"{data['pressure']:6.1f}".strip() if data['pressure'] else "------ "
            pm25_str = f"{data['pm25']:5.1f}".strip() if data['pm25'] else "---- "
            pm10_str = f"{data['pm10']:5.1f}".strip() if data['pm10'] else "---- "
            cpu_temp_str = f"{data['cpu_temp']:5.1f}".strip() if data['cpu_temp'] else "---- "
            
            print(f"{time.strftime('%H:%M:%S')} | "
                  f"T={temp_str}°C | "
                  f"P={press_str}гПа | "
                  f"PM2.5={pm25_str} | PM10={pm10_str} | "
                  f"CPU={cpu_temp_str}°C | ")
            print("-" * 60)
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("🛑 Сенсорный процесс остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка сенсора: {e}", exc_info=True)
        with lock:
            shared_dict['air'] = {'status': 'error', 'error': str(e)}
    finally:
        if sensor:
            sensor.close()
