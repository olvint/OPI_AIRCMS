#!/usr/bin/env python3
import time
import logging
from ens160_aht21 import ENS160_AHT21Sensor  # Убедитесь, что имя файла вашего класса совпадает

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def main():
    print("🔧 Инициализация датчиков...")
    sensor = ENS160_AHT21Sensor()

    print("📊 Начинаем опрос данных (Ctrl+C для остановки)...")
    try:
        while True:
            data = sensor.get_data()

            temp = data['temp']
            hum = data['hum']
            aqi = data['aqi']
            tvoc = data['tvoc']
            eco2 = data['eco2']

            print(f"⏱️ {time.strftime('%H:%M:%S')} | "
                  f"T: {temp}°C | "
                  f"H: {hum}% | "
                  f"AQI: {aqi or '—'} | "
                  f"TVOC: {tvoc or '—'} ppb | "
                  f"eCO2: {eco2 or '—'} ppm")

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Остановлено пользователем.")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        sensor.close()
        print("🔌 Датчики отключены.")

if __name__ == "__main__":
    main()