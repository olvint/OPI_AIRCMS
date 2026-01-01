#!/usr/bin/env python3
import time
from smbus2 import SMBus

# Конфигурация
bus_num = 0
ENS160_addr = 0x53

logger = logging.getLogger(__name__)

class ENS160:
    def __init__(self):
        self.bus_num = bus_num
        self.addr = ENS160_addr
        self.bus = None
        self._open_bus()
        self._initialize()

    def _open_bus(self):
        try:
            self.bus = SMBus(self.bus_num)
            print(f"✅ Шина I2C {self.bus_num} открыта")
        except Exception as e:
            print(f"❌ Не удалось открыть шину I2C {self.bus_num}: {e}")
            raise

    def _initialize(self):
        print("🔄 ENS160: инициализация...")

        # 1. HARDWARE RESET
        self.bus.write_byte_data(self.addr, 0x10, 0xCC)
        time.sleep(0.02)

        # 2. IDLE mode
        self.bus.write_byte_data(self.addr, 0x10, 0x01)
        time.sleep(0.02)

        # 3. CONFIG (PARTID = 0x02 for STANDARD mode)
        self.bus.write_byte_data(self.addr, 0x11, 0x02)
        time.sleep(0.02)

        # 4. STANDARD mode
        self.bus.write_byte_data(self.addr, 0x10, 0x02)
        time.sleep(0.1)

        print("✅ ENS160 готов")

    def get_data(self, temperature=26.0, humidity=27.8):
        try:
            # Преобразуем температуру и влажность в формат ENS160
            temp_int = int(temperature * 100)  # 26.0°C → 2600
            hum_int = int(humidity * 100)     # 27.8% → 2780

            # Упаковка в 2 байта (little-endian)
            temp_bytes = [(temp_int >> 8) & 0xFF, temp_int & 0xFF]
            hum_bytes = [(hum_int >> 8) & 0xFF, hum_int & 0xFF]

            # Установка температуры и влажности
            self.bus.write_i2c_block_data(self.addr, 0x13, temp_bytes)
            self.bus.write_i2c_block_data(self.addr, 0x15, hum_bytes)
            time.sleep(0.05)

            # Чтение статуса
            status = self.bus.read_byte_data(self.addr, 0x20)

            # Чтение данных
            aqi = self.bus.read_byte_data(self.addr, 0x21)

            tvoc_data = self.bus.read_i2c_block_data(self.addr, 0x22, 2)
            tvoc = (tvoc_data[1] << 8) | tvoc_data[0]

            eco2_data = self.bus.read_i2c_block_data(self.addr, 0x24, 2)
            eco2 = (eco2_data[1] << 8) | eco2_data[0]

            return {
                'aqi': aqi,
                'tvoc': tvoc,
                'eco2': eco2,
                'status': status
            }

        except Exception as e:
            print(f"❌ Ошибка чтения ENS160: {e}")
            return None

    def close(self):
        if self.bus:
            try:
                self.bus.close()
                print("🔌 Шина I2C закрыта")
            except Exception as e:
                print(f"⚠️ Ошибка при закрытии шины: {e}")

    def __del__(self):
        self.close()


def main():
    sensor = ENS160()
    try:
        while True:
            # Пример: передаём температуру и влажность
            data = sensor.get_data(temperature=26.5, humidity=30.0)
            if data:
                print(
                    f"AQI:{data['aqi']} TVOC:{data['tvoc']}ppb eCO2:{data['eco2']}ppm status:0x{data['status']:02X}"
                )
            else:
                print("⚠️ Ошибка получения данных")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n🛑 Остановлено пользователем")


if __name__ == "__main__":
    main()