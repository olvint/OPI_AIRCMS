#!/usr/bin/env python3
"""
Полный драйвер для модуля ENS160 + AHT21 на чистом Python
Использует только smbus/smbus2
"""

import time
import struct
from smbus2 import SMBus, i2c_msg

class AHT21:
    """Драйвер датчика температуры и влажности AHT21"""
    
    # Адреса и команды
    AHT21_ADDR = 0x38
    CMD_INIT = 0xE1    # Инициализация
    CMD_MEASURE = 0xAC # Запуск измерения
    CMD_SOFTRESET = 0xBA # Мягкий сброс
    
    def __init__(self, bus_num=0):
        """Инициализация датчика AHT21"""
        self.bus = SMBus(bus_num)
        self._initialized = False
        self._init_sensor()
    
    def _init_sensor(self):
        """Инициализация датчика"""
        try:
            # Мягкий сброс
            self.bus.write_byte(self.AHT21_ADDR, self.CMD_SOFTRESET)
            time.sleep(0.02)
            
            # Инициализация калибровки
            self.bus.write_i2c_block_data(self.AHT21_ADDR, self.CMD_INIT, [0x08, 0x00])
            time.sleep(0.01)
            
            # Проверка статуса
            status = self._read_status()
            if status & 0x08:  # Бит 3 должен быть 1 после калибровки
                self._initialized = True
                print("AHT21: Инициализация успешна")
            else:
                print("AHT21: Ошибка калибровки")
        except Exception as e:
            print(f"AHT21: Ошибка инициализации: {e}")
    
    def _read_status(self):
        """Чтение статусного регистра"""
        try:
            return self.bus.read_byte(self.AHT21_ADDR)
        except:
            return 0
    
    def _trigger_measurement(self):
        """Запуск измерения"""
        # Команда измерения: 0xAC, параметры: [0x33, 0x00]
        self.bus.write_i2c_block_data(self.AHT21_ADDR, self.CMD_MEASURE, [0x33, 0x00])
    
    def _read_data(self):
        """Чтение сырых данных"""
        # Читаем 7 байт: 1 байт статус + 6 байт данных
        data = self.bus.read_i2c_block_data(self.AHT21_ADDR, 0x00, 7)
        return data
    
    def read(self):
        """
        Чтение температуры и влажности
        
        Returns:
            tuple: (temperature, humidity) или (None, None) при ошибке
        """
        if not self._initialized:
            self._init_sensor()
        
        try:
            # Запускаем измерение
            self._trigger_measurement()
            
            # Ждем завершения измерения (до 80 мс)
            timeout = time.time() + 0.1
            while time.time() < timeout:
                status = self._read_status()
                if not (status & 0x80):  # Бит 7 = 0 означает готовность
                    break
                time.sleep(0.01)
            else:
                print("AHT21: Таймаут измерения")
                return None, None
            
            # Читаем данные
            data = self._read_data()
            
            # Проверяем статус
            if data[0] & 0x80:  # Бит 7 должен быть 0
                print("AHT21: Данные не готовы")
                return None, None
            
            # Извлекаем сырые значения (20 бит каждое)
            humidity_raw = ((data[1] << 12) | (data[2] << 4) | (data[3] >> 4))
            temp_raw = (((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5])
            
            # Конвертируем в физические величины
            humidity = (humidity_raw / 1048576.0) * 100.0  # 2^20 = 1048576
            temperature = (temp_raw / 1048576.0) * 200.0 - 50.0
            
            # Проверяем на валидные значения
            if 0 <= humidity <= 100 and -50 <= temperature <= 150:
                return round(temperature, 2), round(humidity, 2)
            else:
                return None, None
                
        except Exception as e:
            print(f"AHT21: Ошибка чтения: {e}")
            return None, None
    
    def close(self):
        """Закрытие соединения с шиной"""
        self.bus.close()


class ENS160:
    """Драйвер датчика качества воздуха ENS160"""
    
    # Адрес по умолчанию (ADD к GND)
    ENS160_ADDR = 0x53
    
    # Регистры ENS160
    REG_PART_ID = 0x00    # Идентификатор чипа
    REG_OPMODE = 0x10     # Режим работы
    REG_CONFIG = 0x11     # Конфигурация
    REG_COMMAND = 0x12    # Команды
    REG_TEMP_IN = 0x13    # Входная температура
    REG_RH_IN = 0x15      # Входная влажность
    REG_DATA_STATUS = 0x20 # Статус данных
    REG_DATA_AQI = 0x21   # Индекс качества воздуха
    REG_DATA_TVOC = 0x22  # TVOC
    REG_DATA_ECO2 = 0x24  # eCO2
    REG_DATA_T = 0x30     # Температура
    REG_DATA_RH = 0x32    # Влажность
    REG_DATA_MISR = 0x38  # Проверка целостности данных
    
    # Режимы работы
    OPMODE_DEEP_SLEEP = 0x00
    OPMODE_IDLE = 0x01
    OPMODE_STANDARD = 0x02
    OPMODE_RESET = 0xF0
    
    # Команды
    CMD_NOP = 0x00
    CMD_CLRGPR = 0xCC
    CMD_GET_APPVER = 0x0E
    
    def __init__(self, bus_num=0, address=0x53):
        """Инициализация датчика ENS160"""
        self.bus = SMBus(bus_num)
        self.address = address
        self._initialized = False
        
        # Проверка подключения и инициализация
        if self._check_part_id():
            self._init_sensor()
    
    def _check_part_id(self):
        """Проверка идентификатора чипа"""
        try:
            part_id = self.bus.read_i2c_block_data(self.address, self.REG_PART_ID, 2)
            # ENS160 должен вернуть 0x0160
            expected_id = (part_id[1] << 8) | part_id[0]
            if expected_id == 0x0160:
                print(f"ENS160: Найден (ID: 0x{expected_id:04X})")
                return True
            else:
                print(f"ENS160: Неизвестный ID: 0x{expected_id:04X}")
                return False
        except Exception as e:
            print(f"ENS160: Ошибка проверки ID: {e}")
            return False
    
    def _init_sensor(self):
        """Инициализация датчика"""
        try:
            # Сброс датчика
            self.bus.write_byte_data(self.address, self.REG_OPMODE, self.OPMODE_RESET)
            time.sleep(0.02)
            
            # Проверка статуса после сброса
            status = self._get_status()
            print(f"ENS160: Статус после сброса: 0x{status:02X}")
            
            # Установка стандартного режима
            self.bus.write_byte_data(self.address, self.REG_OPMODE, self.OPMODE_STANDARD)
            time.sleep(0.05)
            
            # Проверка готовности
            for _ in range(10):
                status = self._get_status()
                if status & 0x80:  # Флаг новых данных
                    self._initialized = True
                    print("ENS160: Инициализация успешна")
                    return
                time.sleep(0.1)
            
            print("ENS160: Таймаут инициализации")
            
        except Exception as e:
            print(f"ENS160: Ошибка инициализации: {e}")
    
    def _get_status(self):
        """Чтение статусного регистра"""
        try:
            return self.bus.read_byte_data(self.address, self.REG_DATA_STATUS)
        except:
            return 0
    
    def set_temp_humidity(self, temperature, humidity):
        """
        Установка температуры и влажности для компенсации
        
        Args:
            temperature: температура в °C
            humidity: влажность в %
        
        Returns:
            bool: True если успешно
        """
        if not self._initialized:
            return False
        
        try:
            # Конвертация температуры в Кельвины * 64
            temp_k = temperature + 273.15
            temp_raw = int(temp_k * 64)
            
            # Конвертация влажности в %RH * 512
            hum_raw = int(humidity * 512)
            
            # Запись температуры (младший байт сначала)
            self.bus.write_i2c_block_data(self.address, self.REG_TEMP_IN, [
                temp_raw & 0xFF,
                (temp_raw >> 8) & 0xFF
            ])
            
            # Запись влажности
            self.bus.write_i2c_block_data(self.address, self.REG_RH_IN, [
                hum_raw & 0xFF,
                (hum_raw >> 8) & 0xFF
            ])
            
            # Небольшая задержка для обработки
            time.sleep(0.01)
            return True
            
        except Exception as e:
            print(f"ENS160: Ошибка установки T/H: {e}")
            return False
    
    def read_air_quality(self):
        """
        Чтение данных качества воздуха
        
        Returns:
            dict: Словарь с данными или None при ошибке
        """
        if not self._initialized:
            return None
        
        try:
            # Проверка статуса
            status = self._get_status()
            
            # Проверяем флаг новых данных
            if not (status & 0x80):
                # print("ENS160: Данные не готовы")
                return None
            
            # Проверяем флаг ошибки
            if status & 0x40:
                print("ENS160: Ошибка в данных")
                return None
            
            # Проверяем валидность
            if not (status & 0x08):
                print("ENS160: Данные невалидны")
                return None
            
            # Чтение AQI
            aqi = self.bus.read_byte_data(self.address, self.REG_DATA_AQI)
            
            # Чтение TVOC (2 байта, little-endian)
            tvoc_data = self.bus.read_i2c_block_data(self.address, self.REG_DATA_TVOC, 2)
            tvoc = (tvoc_data[1] << 8) | tvoc_data[0]
            
            # Чтение eCO2 (2 байта, little-endian)
            eco2_data = self.bus.read_i2c_block_data(self.address, self.REG_DATA_ECO2, 2)
            eco2 = (eco2_data[1] << 8) | eco2_data[0]
            
            # Интерпретация AQI
            aqi_descriptions = {
                1: "Отличное",
                2: "Хорошее", 
                3: "Удовлетворительное",
                4: "Низкое",
                5: "Очень низкое"
            }
            
            aqi_desc = aqi_descriptions.get(aqi, "Неизвестно")
            
            return {
                'status': status,
                'aqi': aqi,
                'aqi_description': aqi_desc,
                'tvoc_ppb': tvoc,
                'eco2_ppm': eco2,
                'valid': bool(status & 0x08),
                'new_data': bool(status & 0x80)
            }
            
        except Exception as e:
            print(f"ENS160: Ошибка чтения: {e}")
            return None
    
    def read_all(self):
        """Чтение всех доступных данных"""
        data = self.read_air_quality()
        if data:
            # Чтение температуры и влажности (если нужны)
            try:
                temp_data = self.bus.read_i2c_block_data(self.address, self.REG_DATA_T, 2)
                rh_data = self.bus.read_i2c_block_data(self.address, self.REG_DATA_RH, 2)
                
                temp = ((temp_data[1] << 8) | temp_data[0]) / 64.0 - 273.15
                rh = ((rh_data[1] << 8) | rh_data[0]) / 512.0
                
                data['temperature_c'] = round(temp, 2)
                data['humidity_percent'] = round(rh, 2)
            except:
                pass
        
        return data
    
    def reset(self):
        """Сброс датчика"""
        try:
            self.bus.write_byte_data(self.address, self.REG_OPMODE, self.OPMODE_RESET)
            time.sleep(0.1)
            self._initialized = False
            self._init_sensor()
            return True
        except:
            return False
    
    def close(self):
        """Закрытие соединения"""
        try:
            # Переход в спящий режим
            self.bus.write_byte_data(self.address, self.REG_OPMODE, self.OPMODE_DEEP_SLEEP)
            self.bus.close()
        except:
            pass


class ENS160_AHT21_Combo:
    """Объединенный класс для работы с модулем ENS160 + AHT21"""
    
    def __init__(self, bus_num=0, ens160_addr=0x53):
        """Инициализация комбинированного модуля"""
        print(f"Инициализация модуля ENS160 + AHT21 на шине I2C-{bus_num}")
        
        # Инициализация датчиков
        self.aht21 = AHT21(bus_num)
        self.ens160 = ENS160(bus_num, ens160_addr)
        
        # Флаг готовности
        self.ready = self.ens160._initialized
        
        if self.ready:
            print("Модуль готов к работе")
        else:
            print("Модуль не инициализирован")
    
    def read_all(self):
        """
        Чтение всех данных с модуля
        
        Returns:
            dict: Все данные или None при ошибке
        """
        if not self.ready:
            print("Модуль не готов")
            return None
        
        # Чтение температуры и влажности с AHT21
        temp, hum = self.aht21.read()
        
        if temp is None or hum is None:
            print("Ошибка чтения AHT21")
            return None
        
        # Обновление данных в ENS160
        if not self.ens160.set_temp_humidity(temp, hum):
            print("Ошибка обновления данных в ENS160")
            return None
        
        # Небольшая задержка для обработки
        time.sleep(0.05)
        
        # Чтение данных качества воздуха
        air_data = self.ens160.read_air_quality()
        
        if air_data is None:
            # Если данных нет, ждем и пробуем еще раз
            time.sleep(0.1)
            air_data = self.ens160.read_air_quality()
        
        if air_data:
            # Добавляем данные AHT21
            air_data['temperature_c'] = temp
            air_data['humidity_percent'] = hum
            return air_data
        
        return None
    
    def continuous_read(self, interval=2, max_readings=None):
        """
        Непрерывное чтение данных
        
        Args:
            interval: интервал между измерениями в секундах
            max_readings: максимальное количество измерений (None для бесконечного)
        """
        count = 0
        
        try:
            while True:
                if max_readings and count >= max_readings:
                    break
                
                data = self.read_all()
                
                if data:
                    print("\n" + "="*50)
                    print(f"Измерение #{count + 1}")
                    print("="*50)
                    print(f"Температура: {data['temperature_c']}°C")
                    print(f"Влажность: {data['humidity_percent']}%")
                    print(f"AQI: {data['aqi']} ({data['aqi_description']})")
                    print(f"TVOC: {data['tvoc_ppb']} ppb")
                    print(f"eCO2: {data['eco2_ppm']} ppm")
                    print(f"Статус: 0x{data['status']:02X}")
                    print("="*50)
                else:
                    print("Нет данных...")
                
                count += 1
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nИзмерение остановлено пользователем")
    
    def close(self):
        """Корректное закрытие соединений"""
        self.aht21.close()
        self.ens160.close()
        print("Соединения закрыты")


# Простой пример использования
if __name__ == "__main__":
    print("Тестирование модуля ENS160 + AHT21")
    print("Подключение к шине I2C-0...")
    
    # Создаем объект модуля
    sensor_module = ENS160_AHT21_Combo(bus_num=0)
    
    if sensor_module.ready:
        print("\nНачинаем измерения...")
        print("Для остановки нажмите Ctrl+C\n")
        
        # Простое чтение одного измерения
        data = sensor_module.read_all()
        if data:
            print(f"Температура: {data['temperature_c']}°C")
            print(f"Влажность: {data['humidity_percent']}%")
            print(f"AQI: {data['aqi']} ({data['aqi_description']})")
            print(f"TVOC: {data['tvoc_ppb']} ppb")
            print(f"eCO2: {data['eco2_ppm']} ppm")
        
        # Или непрерывное чтение (5 измерений для примера)
        # sensor_module.continuous_read(interval=2, max_readings=5)
        
        # Или бесконечное чтение
        # sensor_module.continuous_read(interval=2)
    else:
        print("Не удалось инициализировать модуль")
    
    # Корректное завершение
    sensor_module.close()