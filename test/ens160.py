#!/usr/bin/env python3
import time
from smbus2 import SMBus

bus = SMBus(0)  # Orange Pi Zero = bus 1
addr = 0x53

print("ENS160: правильная инициализация")

# 1. СНАЧАЛА RESET
bus.write_byte_data(addr, 0x10, 0xCC)  # HARDWARE RESET
time.sleep(0.02)

# 2. Ждем готовности
# while bus.read_byte_data(addr, 0x20) & 0x80:
#     time.sleep(0.01)

# 3. IDLE mode
bus.write_byte_data(addr, 0x10, 0x01)
time.sleep(0.02)

# 4. CONFIG (PARTID=0x02 для standard)
bus.write_byte_data(addr, 0x11, 0x02)
time.sleep(0.02)

# 5. STANDARD mode
bus.write_byte_data(addr, 0x10, 0x02)  # 0x02 = STANDARD!
time.sleep(0.1)

print("✅ ENS160 готов")

try:
    while True:
        # T/H калибровка (26°C, 27.8%)
        bus.write_i2c_block_data(addr, 0x13, [0x40, 0x4A])  # T
     
        bus.write_i2c_block_data(addr, 0x15, [0x79, 0x37])  # Hum
        
        time.sleep(0.05)  # Обработка
        
        # # ПРОВЕРКА СТАТУСА
        status = bus.read_byte_data(addr, 0x20)
        # if status & 0x10 == 0:  # Данные готовы?
        #     print("⏳ Данные не готовы...")
        #     time.sleep(1)
        #     continue
        
        # ЧТЕНИЕ (read_i2c_block_data!)
        aqi = bus.read_byte_data(addr, 0x21)
        tvoc_data = bus.read_i2c_block_data(addr, 0x22, 2)
        tvoc = (tvoc_data[1] << 8) | tvoc_data[0]
        eco2_data = bus.read_i2c_block_data(addr, 0x24, 2)
        eco2 = (eco2_data[1] << 8) | eco2_data[0]
        
        print(f"AQI:{aqi} TVOC:{tvoc}ppb eCO2:{eco2}ppm status:0x{status:02X}")
        time.sleep(2)
        
except KeyboardInterrupt:
    print("\nСтоп")
finally:
    bus.close()
