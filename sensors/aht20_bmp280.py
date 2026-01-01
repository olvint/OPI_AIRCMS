#!/usr/bin/env python3
import time
import logging
from smbus2 import SMBus

# Конфигурация
bus_num = 1  
bmp280_addr = 0x77  
aht20_addr = 0x38

logging.basicConfig(level=logging.INFO)

class AHT20_BMP280:
    def __init__(self, bus_num=0, bmp280_addr=0x76, aht20_addr=0x38):
        self.bus_num = bus_num
        self.bmp280_addr = bmp280_addr
        self.aht20_addr = aht20_addr
        self.bus = None
        self.bmp280_calib = None
        self._open_bus()
        self._init_bmp280()
        self._init_aht20()

    def _open_bus(self):
        try:
            self.bus = SMBus(self.bus_num)
            logging.info(f"✅ Шина I2C {self.bus_num} открыта")
        except Exception as e:
            logging.error(f"❌ Не удалось открыть шину I2C {self.bus_num}: {e}")
            raise

    def _read_word_unsigned(self, reg):
        data = self.bus.read_i2c_block_data(self.bmp280_addr, reg, 2)
        return (data[1] << 8) | data[0]  # little-endian

    def _read_word_signed(self, reg):
        value = self._read_word_unsigned(reg)
        return value - 65536 if value > 32767 else value

    def _init_bmp280(self):
        try:
            # Проверка ID чипа
            chip_id = self.bus.read_byte_data(self.bmp280_addr, 0xD0)
            if chip_id != 0x58:
                raise Exception(f"Неверный ID BMP280: 0x{chip_id:02X} (ожидается 0x58)")

            # Загрузка калибровки
            self.bmp280_calib = {
                'dig_T1': self._read_word_unsigned(0x88),
                'dig_T2': self._read_word_signed(0x8A),
                'dig_T3': self._read_word_signed(0x8C),
                'dig_P1': self._read_word_unsigned(0x8E),
                'dig_P2': self._read_word_signed(0x90),
                'dig_P3': self._read_word_signed(0x92),
                'dig_P4': self._read_word_signed(0x94),
                'dig_P5': self._read_word_signed(0x96),
                'dig_P6': self._read_word_signed(0x98),
                'dig_P7': self._read_word_signed(0x9A),
                'dig_P8': self._read_word_signed(0x9C),
                'dig_P9': self._read_word_signed(0x9E),
            }

            # Настройка режима
            self.bus.write_byte_data(self.bmp280_addr, 0xF4, 0x27)  # temp x1, press x1, normal mode
            self.bus.write_byte_data(self.bmp280_addr, 0xF5, 0xA0)  # standby 1000ms, filter x16
            time.sleep(0.1)

            logging.info(f"✅ BMP280 инициализирован (адрес 0x{self.bmp280_addr:02X})")
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации BMP280: {e}")
            self.bmp280_calib = None

    def _init_aht20(self):
        try:
            # Проверка статуса и инициализация AHT20
            self.bus.write_i2c_block_data(self.aht20_addr, 0xE1, [0x00, 0x00])
            time.sleep(0.01)
            status = self.bus.read_i2c_block_data(self.aht20_addr, 0x00, 1)
            if not (status[0] & 0x18):
                # Устройство уже инициализировано
                logging.info(f"✅ AHT20 уже инициализирован (адрес 0x{self.aht20_addr:02X})")
                return
            # Инициализация
            self.bus.write_i2c_block_data(self.aht20_addr, 0xBE, [0x08, 0x00])
            time.sleep(0.01)
            logging.info(f"✅ AHT20 инициализирован (адрес 0x{self.aht20_addr:02X})")
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации AHT20: {e}")

    def _compensate_temperature(self, adc_T):
        if not self.bmp280_calib:
            return 0.0, 0.0
        var1 = ((adc_T / 16384.0) - (self.bmp280_calib['dig_T1'] / 1024.0)) * self.bmp280_calib['dig_T2']
        var2 = (((adc_T / 131072.0) - (self.bmp280_calib['dig_T1'] / 8192.0)) ** 2) * self.bmp280_calib['dig_T3']
        t_fine = var1 + var2
        temp_C = t_fine / 5120.0
        return temp_C, t_fine

    def _compensate_pressure(self, adc_P, t_fine):
        if not self.bmp280_calib:
            return 0.0
        var1 = (t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * self.bmp280_calib['dig_P6'] / 32768.0
        var2 = var2 + var1 * self.bmp280_calib['dig_P5'] * 2.0
        var2 = (var2 / 4.0) + (self.bmp280_calib['dig_P4'] * 65536.0)
        var1 = (self.bmp280_calib['dig_P3'] * var1 * var1 / 524288.0 + self.bmp280_calib['dig_P2'] * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.bmp280_calib['dig_P1']
        if var1 == 0:
            return 0.0
        p = 1048576.0 - adc_P
        p = (p - (var2 / 4096.0)) * 6250.0 / var1
        var1 = self.bmp280_calib['dig_P9'] * p * p / 2147483648.0
        var2 = p * self.bmp280_calib['dig_P8'] / 32768.0
        p = p + (var1 + var2 + self.bmp280_calib['dig_P7']) / 16.0
        return p / 100.0  # гПа

    def read_bmp280(self):
        if not self.bmp280_calib:
            return None, None
        try:
            data = self.bus.read_i2c_block_data(self.bmp280_addr, 0xF7, 6)
            adc_P = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
            adc_T = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
            
            if adc_T == 0 or adc_P == 0:
                logging.warning("BMP280: нулевые ADC-значения")
                return None, None

            temp_C, t_fine = self._compensate_temperature(adc_T)
            press_hPa = self._compensate_pressure(adc_P, t_fine)

            if not (-40 <= temp_C <= 85) or not (300 <= press_hPa <= 1100):
                logging.warning(f"BMP280: недопустимые значения T={temp_C:.1f}°C, P={press_hPa:.1f}гПа")
                return None, None

            return round(temp_C, 2), round(press_hPa, 2)
        except Exception as e:
            logging.error(f"❌ Ошибка чтения BMP280: {e}")
            return None, None

    def read_aht20(self):
        try:
            self.bus.write_i2c_block_data(self.aht20_addr, 0xAC, [0x33, 0x00])
            time.sleep(0.08)
            data = self.bus.read_i2c_block_data(self.aht20_addr, 0x00, 6)
            hum_raw = ((data[1] << 12) + (data[2] << 4) + (data[3] >> 4))
            temp_raw = (((data[3] & 0x0F) << 16) + (data[4] << 8) + data[5])
            hum = hum_raw / 1048576.0 * 100.0
            temp = temp_raw / 1048576.0 * 200.0 - 50.0
            return temp, hum
        except Exception as e:
            logging.error(f"❌ Ошибка чтения AHT20: {e}")
            return None, None

        except Exception as e:
            logging.error(f"❌ Ошибка чтения AHT20: {e}")
            return None, None

    def get_data(self):
        temp_a, hum_a = self.read_aht20()
        temp_b, press_b = self.read_bmp280()
        return {
            'aht20_temperature': temp_a,
            'aht20_humidity': hum_a,
            'bmp280_temperature': temp_b,
            'bmp280_pressure': press_b
        }

    def close(self):
        if self.bus:
            try:
                self.bus.close()
                logging.info("✅ Шина I2C закрыта")
            except Exception as e:
                logging.error(f"⚠️ Ошибка при закрытии шины I2C: {e}")

    def __del__(self):
        self.close()


def main():
    sensor = AHT20_BMP280(bus_num=bus_num, bmp280_addr=bmp280_addr, aht20_addr=aht20_addr)
    while True:
        data = sensor.get_data()
        print(data)
        time.sleep(2)

if __name__ == "__main__":
    main()