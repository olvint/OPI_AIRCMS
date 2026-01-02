#!/usr/bin/env python3

import requests
import time
import logging
from typing import Dict
from datetime import datetime
from update_shared_dict import update_service_status

# Конфигурация
BOARD_ID = "raspi-5006471"
API_URL_SENSOR = "https://api.sensor.community/v1/push-sensor-data/"
API_URL_MADAVI = "https://api-rrd.madavi.de/data.php"
TIMEOUT = 10
SEND_INTERVAL = 180  # 3 минуты - оптимально для карт 

logger = logging.getLogger(__name__)

def send_sensor_data(url: str, headers: Dict, data: Dict) -> bool:
    """Отправка данных в API"""
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
        if resp.status_code in (200, 201) :
            return True
        else:
            logger.warning(f"✗ Ошибка {resp.status_code}: {resp.text[:100]}")
            return False
    except Exception as e:
        logger.error(f"✗ Ошибка отправки: {e}")
        return False

def push_sds011(pm10: float, pm25: float) -> bool:
    """SDS011 PM данные"""
    headers = {
        "Content-Type": "application/json",
        "X-Pin": "1",
        "X-Sensor": BOARD_ID
    }
    data = {
        "software_version": "raspi_multiprocess_1.0",
        "sensordatavalues": [
            {"value_type": "P1", "value": f"{pm10:.2f}"},  # PM10
            {"value_type": "P2", "value": f"{pm25:.2f}"}   # PM2.5
        ]
    }
    
    # Отправка в оба API
    success1 = send_sensor_data(API_URL_SENSOR, headers, data)
    success2 = send_sensor_data(API_URL_MADAVI, headers, data)
    return success1 or success2

def push_bmp280(temperature: float, pressure: float, humidity: float = None) -> bool:
    """BMP280 данные (давление в hPa -> Pa)"""
    headers = {
        "Content-Type": "application/json",
        "X-Pin": "11",
        "X-Sensor": BOARD_ID
    }
    sensordata = [
        {"value_type": "temperature", "value": f"{temperature:.2f}"}
    ]
    
    # Давление в Pa (API ожидает Паскали)
    if pressure:
        sensordata.append({"value_type": "pressure", "value": f"{pressure * 100:.0f}"})
    
    # Влажность если есть
    if humidity is not None:
        sensordata.append({"value_type": "humidity", "value": f"{humidity:.2f}"})
    
    data = {
        "software_version": "raspi_multiprocess_1.0",
        "sensordatavalues": sensordata
    }
    
    success1 = send_sensor_data(API_URL_SENSOR, headers, data)
    success2 = send_sensor_data(API_URL_MADAVI, headers, data)
    return success1 or success2

def send_data(shared_dict: Dict, lock):
    """
    Основной процесс отправки данных в sensor.community
    """
    logger.info(f"🚀 Запуск sensor_community для {BOARD_ID}")
    logger.info("Ожидание данных в shared_dict...")
    
    last_send = 0
    consecutive_errors = 0
    
    while True:
        try:
            bmp280_data=shared_dict['Sensor data'].get('BMP280')
            sds011_data=shared_dict['Sensor data'].get('SDS011')
            
            # Проверяем наличие данных
            if bmp280_data and sds011_data:

                pm10 = sds011_data['pm10']['value']
                pm25 = sds011_data['pm25']['value']

                temp = bmp280_data['Temperature']['value']
                pressure = bmp280_data['Pressure']['value']
                

                # Отправляем PM данные
                pm_success = push_sds011(pm10, pm25)
                
                # Отправляем климат данные
                climate_success = push_bmp280(temp, pressure)
                
                if pm_success and climate_success:
                    update_service_status(shared_dict, lock, 'sensor.community', 'ОК')
                else:
                    consecutive_errors += 1
                    logger.warning.error(f"❌ Ошибка отправки ({consecutive_errors})")
                    update_service_status(shared_dict, lock, f'sensor.community', 'Ошибка отправки - {consecutive_errors}')
            else:
                update_service_status(shared_dict, lock, 'sensor.community', 'Нет данных для отправки')

            time.sleep(SEND_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки")
            break
        except Exception as e:
            consecutive_errors += 1
            update_service_status(shared_dict, lock, 'sensor.community', f'Ошибка {consecutive_errors} - {e}')
            time.sleep(60)  # Дольше ждем при ошибках
    
    logger.info("👋 sensor_community остановлен")

if __name__ == "__main__":
    # Тестовый запуск
    from multiprocessing import Manager
    manager = Manager()
    shared_dict = manager.dict()
    shared_dict['air'] = {
        'timestamp': time.time(),
        'temperature': 5.56,
        'pressure': 1006.16,
        'pm25': 3.2,
        'pm10': 5.6,
        'cpu_temp': 34.3,
        'status': 'ok'
    }
    lock = manager.Lock()
    
    send_data(shared_dict, lock)
