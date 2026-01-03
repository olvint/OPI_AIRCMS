#!/usr/bin/env python3

import requests
import time
import logging
from typing import Dict

import hmac
import hashlib
import json

from update_shared_dict import update_service_status

# Конфигурация
CHIP_ID = "5006471" 
MAC_ADDR = "02:42:39:D2:02:B6" 

SEND_INTERVAL = 300  # 5 минут

logger = logging.getLogger(__name__)

def send_data_to_doiot(data_json, esp_chipid, mac_address, server_url="https://doiot.ru", endpoint_path="/php/sensors.php"):
    """
    Подготавливает и отправляет данные о качестве воздуха на сервер doiot.ru.
    Использует нетипичный метод вычисления подписи, как в Arduino коде (функция hmac1).

    :param data_json: Словарь с данными датчиков, например:
                      {"sensordatavalues": [{"value_type": "P1", "value": "15.2"}, ...]}
                      или строка JSON, если это удобнее.
    :param esp_chipid: (str) Уникальный ID чипа ESP (например, '1234567890ABCDEF').
    :param mac_address: (str) MAC-адрес устройства (например, 'AA:BB:CC:DD:EE:FF').
                         Используется как токен для генерации подписи.
    :param server_url: (str) Базовый URL сервера (по умолчанию 'https://doiot.ru').
    :param endpoint_path: (str) Путь к конечной точке API (по умолчанию '/php/sensors.php').
    :return: True, если отправка успешна (статус 200), иначе False.
    """
    try:
        # 1. Подготовка данных
        # Преобразуем в строку JSON, если передан словарь
        # В Arduino коде: jsonBuffer.prettyPrintTo(airrohr_json); -> строка может содержать пробелы
        # dumps с separators создает компактную строку, как в Arduino.
        if isinstance(data_json, dict):
            data_json_str = json.dumps(data_json, separators=(',', ':'))
        else:
            data_json_str = str(data_json)

        # Временная метка
        timestamp = str(int(time.time()))

        # Логин (используется ID чипа)
        login = esp_chipid

        # Токен (используется MAC-адрес)
        token = mac_address

        # Формирование строки our_data (L=...&t=...&airrohr=...)
        our_data = f"L={login}&t={timestamp}&airrohr={data_json_str}"
        # 2. Вычисление подписи (используя логику hmac1 из Arduino)
        # 2.1. SHA1 хэш от our_data + token
        hmac_message = our_data + token
        
        sha1_of_message = hashlib.sha1(hmac_message.encode('utf-8')).hexdigest()

        # 2.2. SHA1 хэш токена (MAC-адреса) -> это "secret" для следующего шага
        token_sha1_hex = hashlib.sha1(token.encode('utf-8')).hexdigest()

        # 2.3. Конкатенация "secret" (token_sha1_hex) и SHA1(s) (sha1_of_message)
        final_input = token_sha1_hex + sha1_of_message

        # 2.4. SHA1 от конкатенации -> это итоговая подпись
        signature_hmac = hashlib.sha1(final_input.encode('utf-8')).hexdigest()

        # 3. Формирование URL для запроса
        full_url = f"{server_url}{endpoint_path}?h={signature_hmac}"

        # 4. Подготовка тела запроса (то же, что и our_data)
        payload = our_data

        # 5. Отправка HTTP POST запроса
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Python-Doiot-Sender-Custom-HMAC'
        }

        response = requests.post(full_url, data=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            return True
        else:
            logger.error(f"Ошибка при отправке данных: HTTP {response.status_code}")
            logger.error(f"Ответ сервера: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка соединения или запроса: {e}")
        return False
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка: {e}")
        return False


def send_data(shared_dict: Dict, lock):
    """
    Основной процесс отправки данных в aircms.online
    """
    logger.info(f"🚀 Запуск aircms.online для {CHIP_ID}")

    consecutive_errors = 0
    
    while True:
        try:
            bmp280_data=shared_dict['Sensor data'].get('BMP280')
            sds011_data=shared_dict['Sensor data'].get('SDS011')
            aht20_data=shared_dict['Sensor data'].get('AHT20')

            
            # Проверяем наличие данных
            if bmp280_data and sds011_data:

                pm10 = sds011_data['pm10']['value']
                pm25 = sds011_data['pm25']['value']

                temperature = bmp280_data['Temperature']['value']
                pressure = bmp280_data['Pressure']['value']

                humidity=aht20_data['Humidity']['value']


                sensor_data = {
                "sensordatavalues": [
                    {
                    "value_type": "BME280_temperature",
                    "value": str(round(temperature,2))
                    },
                    {
                    "value_type": "BME280_humidity",
                    "value": str(round(humidity,2))
                    },
                    {
                    "value_type": "BME280_pressure",
                    "value": str(round(pressure,2))
                    },
                    {
                    "value_type": "SDS_P1",
                    "value": str(round(pm10,2))
                    },
                    {
                    "value_type": "SDS_P2",
                    "value": str(round(pm25,2))
                    }
                ]
                }

                # Отправляем PM данные
                aircms_success = send_data_to_doiot(sensor_data, CHIP_ID, MAC_ADDR)
                
                if aircms_success:
                    update_service_status(shared_dict, lock, 'aircms.online', 'ОК')
                else:
                    consecutive_errors += 1
                    logger.warning.error(f"❌ Ошибка отправки ({consecutive_errors})")
                    update_service_status(shared_dict, lock, f'aircms.online', 'Ошибка отправки - {consecutive_errors}')
            else:
                update_service_status(shared_dict, lock, 'aircms.online', 'Нет данных для отправки')

            time.sleep(SEND_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки")
            break
        except Exception as e:
            consecutive_errors += 1
            update_service_status(shared_dict, lock, 'aircms.online', f'Ошибка {consecutive_errors} - {e}')
            time.sleep(60)  # Дольше ждем при ошибках
    
    logger.info("👋 aircms.online остановлен")