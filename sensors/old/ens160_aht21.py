#!/usr/bin/env python3
import time
import logging
from smbus2 import SMBus

logging.basicConfig(level=logging.INFO)

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
    print("🔍 Отладка AHT21...")

    for i in range(20):
        raw = read_aht21_raw(bus)
        if raw:
            temp, hum = parse_aht21(raw)
            print(f"#{i+1:2d} Raw: {raw} | T: {temp:.1f}°C | H: {hum:.1f}%")
        else:
            print(f"#{i+1:2d} ❌ Ошибка чтения")
        time.sleep(2)

if __name__ == "__main__":
    main()