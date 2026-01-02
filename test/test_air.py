#!/usr/bin/env python3
import smbus2
import time
import serial
import struct

# I2C адрес BMP280 (подтверждён 0x76)
BMP_ADDR = 0x76

# Регистры BMP280
REG_ID = 0xD0
REG_CTRL_MEAS = 0xF4
REG_CONFIG = 0xF5
REG_TEMP_MSB = 0xFA
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

bus = smbus2.SMBus(0)

def init_bmp280():
    """Инициализация BMP280 с проверкой"""
    chip_id = bus.read_byte_data(BMP_ADDR, REG_ID)
    print(f"BMP280 ID: 0x{chip_id:02X} (ожидается 0x58)")
    
    if chip_id != 0x58:
        raise Exception("Неправильный ID чипа!")
    
    # Нормальный режим: temp/press oversampling x1
    bus.write_byte_data(BMP_ADDR, REG_CTRL_MEAS, 0x27)
    bus.write_byte_data(BMP_ADDR, REG_CONFIG, 0xA0)  # IIR фильтр off, t_standby 62.5ms
    time.sleep(0.1)
    print("✅ BMP280 инициализирован")

def load_calibration():
    """Загрузка калибровочных коэффициентов"""
    cals = {}
    cals['dig_T1'] = bus.read_word_data(BMP_ADDR, DIG_T1)
    cals['dig_T2'] = bus.read_word_data(BMP_ADDR, DIG_T2)
    cals['dig_T3'] = bus.read_word_data(BMP_ADDR, DIG_T3)
    cals['dig_P1'] = bus.read_word_data(BMP_ADDR, DIG_P1)
    cals['dig_P2'] = bus.read_word_data(BMP_ADDR, DIG_P2)
    cals['dig_P3'] = bus.read_word_data(BMP_ADDR, DIG_P3)
    cals['dig_P4'] = bus.read_word_data(BMP_ADDR, DIG_P4)
    cals['dig_P5'] = bus.read_word_data(BMP_ADDR, DIG_P5)
    cals['dig_P6'] = bus.read_word_data(BMP_ADDR, DIG_P6)
    cals['dig_P7'] = bus.read_word_data(BMP_ADDR, DIG_P7)
    cals['dig_P8'] = bus.read_word_data(BMP_ADDR, DIG_P8)
    cals['dig_P9'] = bus.read_word_data(BMP_ADDR, DIG_P9)
    
    # Конвертация в signed int16 где нужно
    for key in ['dig_T2', 'dig_T3', 'dig_P2', 'dig_P4', 'dig_P5', 'dig_P6', 'dig_P7', 'dig_P8', 'dig_P9']:
        cals[key] = cals[key] > 32767 and cals[key] - 65536 or cals[key]
    
    return cals

def compensate_temperature(adc_T, dig_T):
    """Компенсация температуры (алгоритм Bosch)"""
    var1 = (adc_T / 16384.0 - dig_T['dig_T1'] / 1024.0) * dig_T['dig_T2']
    var2 = ((adc_T / 131072.0 - dig_T['dig_T1'] / 8192.0) * 
            (adc_T / 131072.0 - dig_T['dig_T1'] / 8192.0)) * dig_T['dig_T3']
    t_fine = var1 + var2
    temp_C = t_fine / 5120.0
    return temp_C, t_fine

def compensate_pressure(adc_P, dig_P, t_fine):
    """Компенсация давления"""
    var1 = t_fine / 2.0 - 64000.0
    var2 = var1 * var1 * dig_P['dig_P6'] / 32768.0
    var2 = var2 + var1 * dig_P['dig_P5'] * 2.0
    var2 = var2 / 4.0 + dig_P['dig_P4'] * 65536.0
    var1 = (dig_P['dig_P3'] * var1 * var1 / 524288.0 + dig_P['dig_P2'] * var1) / 524288.0
    var1 = (1.0 + var1 / 32768.0) * dig_P['dig_P1']
    
    if var1 == 0:
        return 0
    
    p = 1048576.0 - adc_P
    p = ((p - var2 / 4096.0) * 6250.0) / var1
    var1 = dig_P['dig_P9'] * p * p / 2147483648.0
    var2 = p * dig_P['dig_P8'] / 32768.0
    p = p + (var1 + var2 + dig_P['dig_P7']) / 16.0
    return p / 100.0  # hPa

def read_bmp280():
    """Чтение с полной компенсацией"""
    try:
        # Читаем 6 байт (давление + температура)
        data = bus.read_i2c_block_data(BMP_ADDR, REG_PRESS_MSB, 6)
        
        # Давление (20 бит)
        adc_P = ((data[0] << 12) | (data[1] << 4) | (data[2] >> 4))
        # Температура (20 бит)  
        adc_T = ((data[3] << 12) | (data[4] << 4) | (data[5] >> 4))
        
        temp_C, t_fine = compensate_temperature(adc_T, dig_T)
        press_hPa = compensate_pressure(adc_P, dig_P, t_fine)
        
        return temp_C, press_hPa
        
    except Exception as e:
        print(f"BMP280 ошибка: {e}")
        return None, None

def read_sds011():
    """SDS011"""
    try:
        with serial.Serial('/dev/ttyS1', 9600, timeout=2) as ser:
            data = ser.read(10)
            if len(data) == 10 and data[0] == 0xAA and data[1] == 0xC0:
                pm25 = struct.unpack('<HH', data[2:6])[0] / 10.0
                pm10 = struct.unpack('<HH', data[4:8])[0] / 10.0
                return pm25, pm10
    except:
        pass
    return None, None

# Инициализация
init_bmp280()
dig_T = load_calibration()
dig_P = load_calibration()
print("✅ Калибровка загружена")

print("🚀 HW-611 BMP280 + SDS011 (полная калибровка)")
print("=" * 60)

while True:
    try:
        temp, press = read_bmp280()
        pm25, pm10 = read_sds011()
        
        # Форматирование PM значений
        pm25_str = f"{pm25:5.1f}" if pm25 else "---- "
        pm10_str = f"{pm10:5.1f}" if pm10 else "---- "

        print(f"{time.strftime('%H:%M:%S')} | "
            f"T={temp:5.1f}°C | "
            f"P={press:6.1f}гПа | "
            f"PM2.5={pm25_str} | PM10={pm10_str}")
        print("-" * 60)
        
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n✅ Остановлено")
        break

bus.close()
