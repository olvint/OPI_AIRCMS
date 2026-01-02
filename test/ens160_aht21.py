#!/usr/bin/env python3
import time
import logging
from smbus2 import SMBus

logging.basicConfig(level=logging.INFO)

class BMP280:
    def __init__(self, bus, addr=0x77):
        self.bus = bus
        self.addr = addr
        self.calib = {}
        self._init()
    
    def _init(self):
        """Инициализация BMP280 и чтение калибровочных коэффициентов"""
        try:
            # Чтение калибровочных коэффициентов
            calib_data = self.bus.read_i2c_block_data(self.addr, 0x88, 24)
            
            # Преобразование коэффициентов (согласно datasheet)
            self.calib['dig_T1'] = calib_data[0] + (calib_data[1] << 8)
            self.calib['dig_T2'] = self._to_signed(calib_data[2] + (calib_data[3] << 8))
            self.calib['dig_T3'] = self._to_signed(calib_data[4] + (calib_data[5] << 8))
            
            self.calib['dig_P1'] = calib_data[6] + (calib_data[7] << 8)
            self.calib['dig_P2'] = self._to_signed(calib_data[8] + (calib_data[9] << 8))
            self.calib['dig_P3'] = self._to_signed(calib_data[10] + (calib_data[11] << 8))
            self.calib['dig_P4'] = self._to_signed(calib_data[12] + (calib_data[13] << 8))
            self.calib['dig_P5'] = self._to_signed(calib_data[14] + (calib_data[15] << 8))
            self.calib['dig_P6'] = self._to_signed(calib_data[16] + (calib_data[17] << 8))
            self.calib['dig_P7'] = self._to_signed(calib_data[18] + (calib_data[19] << 8))
            self.calib['dig_P8'] = self._to_signed(calib_data[20] + (calib_data[21] << 8))
            self.calib['dig_P9'] = self._to_signed(calib_data[22] + (calib_data[23] << 8))
            
            # Настройка режима работы
            # osrs_t = 1 (x2 oversampling), osrs_p = 1 (x2), mode = 3 (normal)
            config = 0b01010011  # t_sb=0 (0.5ms), filter=0 (off), spi3w_en=0
            ctrl_meas = 0b00100111  # osrs_t=1, osrs_p=1, mode=3
            
            self.bus.write_byte_data(self.addr, 0xF4, ctrl_meas)
            self.bus.write_byte_data(self.addr, 0xF5, config)
            
            print(f"✅ BMP280 инициализирован (адрес 0x{self.addr:02X})")
            
        except Exception as e:
            print(f"❌ Ошибка инициализации BMP280: {e}")
            self.calib = None
    
    def _to_signed(self, val):
        """Преобразование unsigned в signed (16-bit)"""
        if val >= 0x8000:
            return val - 0x10000
        return val
    
    def _compensate_temperature(self, raw_temp):
        """Компенсация температуры (согласно datasheet)"""
        if not self.calib:
            return 0, 0
        
        var1 = ((raw_temp / 16384.0) - (self.calib['dig_T1'] / 1024.0)) * self.calib['dig_T2']
        var2 = ((raw_temp / 131072.0) - (self.calib['dig_T1'] / 8192.0)) ** 2 * self.calib['dig_T3']
        t_fine = var1 + var2
        temperature = (var1 + var2) / 5120.0
        return temperature, t_fine
    
    def _compensate_pressure(self, raw_press, t_fine):
        """Компенсация давления (согласно datasheet)"""
        if not self.calib:
            return 0
        
        var1 = (t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * self.calib['dig_P6'] / 32768.0
        var2 = var2 + var1 * self.calib['dig_P5'] * 2.0
        var2 = (var2 / 4.0) + (self.calib['dig_P4'] * 65536.0)
        var1 = (self.calib['dig_P3'] * var1 * var1 / 524288.0 + self.calib['dig_P2'] * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.calib['dig_P1']
        
        if var1 == 0:
            return 0
        
        pressure = 1048576.0 - raw_press
        pressure = (pressure - (var2 / 4096.0)) * 6250.0 / var1
        var1 = self.calib['dig_P9'] * pressure * pressure / 2147483648.0
        var2 = pressure * self.calib['dig_P8'] / 32768.0
        pressure = pressure + (var1 + var2 + self.calib['dig_P7']) / 16.0
        
        return pressure / 100.0  # Преобразование в гПа
    
    def read(self):
        """Чтение температуры и давления"""
        try:
            # Чтение сырых данных (6 байт)
            data = self.bus.read_i2c_block_data(self.addr, 0xF7, 6)
            
            # Преобразование сырых значений
            press_raw = (data[0] << 12) + (data[1] << 4) + (data[2] >> 4)
            temp_raw = (data[3] << 12) + (data[4] << 4) + (data[5] >> 4)
            
            # Компенсация
            temperature, t_fine = self._compensate_temperature(temp_raw)
            pressure = self._compensate_pressure(press_raw, t_fine)
            
            return temperature, pressure
            
        except Exception as e:
            print(f"❌ Ошибка чтения BMP280: {e}")
            return None, None

def read_aht21_raw(bus, addr=0x38):
    try:
        # Запуск измерения
        bus.write_i2c_block_data(addr, 0xAC, [0x33, 0x00])
        time.sleep(0.08)  # >= 7.5ms
        data = bus.read_i2c_block_data(addr, 0x00, 6)
        return data
    except Exception as e:
        print(f"❌ Ошибка чтения AHT21: {e}")
        return None

def parse_aht21(data):
    hum_raw = ((data[1] << 12) + (data[2] << 4) + (data[3] >> 4))
    temp_raw = (((data[3] & 0x0F) << 16) + (data[4] << 8) + data[5])

    hum = hum_raw / 1048576.0 * 100.0
    temp = temp_raw / 1048576.0 * 200.0 - 50.0
    return temp, hum

def main():
    bus = SMBus(1)
    print("🔍 Отладка AHT21 и BMP280...")
    
    # Инициализация BMP280
    bmp280 = BMP280(bus, addr=0x77)
    
    print("\n" + "="*60)
    print("Начинаем чтение датчиков...")
    print("="*60 + "\n")
    
    for i in range(50):
        print(f"\n📊 Итерация #{i+1:2d}")
        print("-" * 40)
        
        # Чтение AHT21
        raw_aht = read_aht21_raw(bus)
        if raw_aht:
            temp_aht, hum_aht = parse_aht21(raw_aht)
            print(f"AHT21: T={temp_aht:5.1f}°C  H={hum_aht:5.1f}%")
        else:
            print("AHT21: ❌ Ошибка чтения")
        
        # Чтение BMP280
        temp_bmp, press_bmp = bmp280.read()
        if temp_bmp is not None and press_bmp is not None:
            print(f"BMP280: T={temp_bmp:5.1f}°C  P={press_bmp:6.1f} гПа")
        else:
            print("BMP280: ❌ Ошибка чтения")
        
        time.sleep(2)

if __name__ == "__main__":
    main()