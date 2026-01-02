#!/usr/bin/env python3
"""
Flask веб-интерфейс для отображения данных с датчиков
Обновленная версия с использованием timestamp из данных датчиков
"""

import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify

# HTML шаблон с новым форматом
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мониторинг датчиков</title>
    <style>
        :root {
            --primary: #3498db;
            --primary-dark: #2980b9;
            --secondary: #2ecc71;
            --danger: #e74c3c;
            --warning: #f39c12;
            --dark: #2c3e50;
            --light: #ecf0f1;
            --gray: #95a5a6;
            --gray-light: #bdc3c7;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: var(--dark);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* Шапка */
        .header {
            background: white;
            border-radius: 15px;
            padding: 25px 30px;
            margin-bottom: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .header-left {
            flex: 1;
        }
        
        .header-title {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
        }
        
        .header-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5rem;
        }
        
        h1 {
            color: var(--dark);
            font-size: 2rem;
            font-weight: 600;
        }
        
        .header-subtitle {
            color: var(--gray);
            font-size: 1rem;
            margin-bottom: 15px;
        }
        
        .system-status {
            background: var(--light);
            padding: 10px 20px;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            font-weight: 500;
        }
        
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--secondary);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        /* Секции */
        .sections-container {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }
        
        .section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        }
        
        .section-title {
            color: var(--dark);
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--light);
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .title-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        /* Секция 1: Датчики - 2 в ряд */
        .sensor-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 25px;
        }
        
        @media (max-width: 1100px) {
            .sensor-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .sensor-card {
            background: #f8fafc;
            border-radius: 12px;
            padding: 25px;
            border-left: 5px solid var(--primary);
            transition: all 0.3s ease;
        }
        
        .sensor-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.12);
        }
        
        .sensor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .sensor-name {
            font-size: 1.3rem;
            color: var(--dark);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .sensor-icon {
            width: 35px;
            height: 35px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        /* Параметры датчика - 2 в ряд */
        .params-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }
        
        @media (max-width: 600px) {
            .params-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .param-item {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        
        .param-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        }
        
        .param-name {
            font-size: 0.95rem;
            color: var(--gray);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 500;
        }
        
        .param-value-container {
            display: flex;
            align-items: baseline;
            margin-bottom: 8px;
        }
        
        .param-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--dark);
            line-height: 1.2;
        }
        
        .param-unit {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--dark);
            margin-left: 4px;
        }
        
        .param-timestamp {
            font-size: 0.85rem;
            color: var(--gray);
            margin-top: 5px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .param-status {
            font-size: 0.8rem;
            padding: 4px 10px;
            border-radius: 15px;
            background: var(--warning);
            color: white;
            display: inline-block;
            margin-top: 10px;
            font-weight: 500;
        }
        
        /* Секция 2: Service Data - как есть */
        .service-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }
        
        @media (max-width: 900px) {
            .service-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .service-item {
            background: #f8fafc;
            border-radius: 12px;
            padding: 25px;
            border-left: 5px solid var(--secondary);
            transition: all 0.3s ease;
        }
        
        .service-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        }
        
        .service-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .service-name {
            font-size: 1.2rem;
            color: var(--dark);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .service-icon {
            width: 30px;
            height: 30px;
            background: var(--secondary);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        .service-message {
            font-size: 1.1rem;
            color: var(--dark);
            margin-bottom: 15px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid var(--primary);
        }
        
        .service-timestamp {
            font-size: 0.9rem;
            color: var(--gray);
            display: flex;
            align-items: center;
            gap: 8px;
            padding-top: 15px;
            border-top: 1px solid var(--light);
        }
        
        .time-ago {
            background: var(--light);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        /* Футер */
        .footer {
            margin-top: 30px;
            text-align: center;
            color: var(--gray);
            font-size: 0.9rem;
            padding-top: 20px;
            border-top: 1px solid var(--light);
        }
        
        .update-info {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 20px;
        }
        
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-refresh {
            background: var(--primary);
            color: white;
        }
        
        .btn-refresh:hover {
            background: var(--primary-dark);
            transform: translateY(-2px);
        }
        
        .btn-json {
            background: var(--secondary);
            color: white;
        }
        
        .btn-json:hover {
            background: #27ae60;
            transform: translateY(-2px);
        }
        
        /* Анимации */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .fade-in {
            animation: fadeInUp 0.6s ease-out;
        }
        
        /* Таймер обновления */
        .refresh-timer {
            height: 4px;
            background: var(--light);
            border-radius: 2px;
            margin-top: 10px;
            overflow: hidden;
        }
        
        .timer-bar {
            height: 100%;
            background: var(--primary);
            width: 0%;
            transition: width 60s linear;
        }
        
        /* Цвета иконок по типам датчиков */
        .icon-temperature { color: #ff6b6b; }
        .icon-humidity { color: #4d96ff; }
        .icon-pressure { color: #9c88ff; }
        .icon-air { color: #10ac84; }
        .icon-pm { color: #ff9f43; }
        .icon-cpu { color: #8395a7; }
        .icon-generic { color: var(--gray); }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <!-- Шапка -->
        <div class="header fade-in">
            <div class="header-left">
                <div class="header-title">
                    <div class="header-icon">
                        <i class="fas fa-chart-line"></i>
                    </div>
                    <h1>Система мониторинга окружающей среды</h1>
                </div>
                <p class="header-subtitle">Реальное время • Все датчики онлайн • Автообновление</p>
                <div class="system-status">
                    <div class="status-indicator"></div>
                    <span>Система активна • Последние данные: <span id="lastDataTime">{{ latest_timestamp|datetime_format if latest_timestamp else 'загружаются...' }}</span></span>
                </div>
                <div class="refresh-timer">
                    <div class="timer-bar" id="timerBar"></div>
                </div>
            </div>
        </div>
        
        <div class="sections-container">
            <!-- Секция 1: Основные датчики -->
            <div class="section fade-in">
                <div class="section-title">
                    <div class="title-icon">
                        <i class="fas fa-microchip"></i>
                    </div>
                    Основные датчики
                </div>
                
                <div class="sensor-grid">
                    {% for sensor_name, sensor_data in sensor_data_dict.items() %}
                        <div class="sensor-card">
                            <div class="sensor-header">
                                <div class="sensor-name">
                                    <div class="sensor-icon">
                                        <i class="fas {% if 'AHT' in sensor_name %}fa-thermometer-half
                                                    {% elif 'BMP' in sensor_name %}fa-tachometer-alt
                                                    {% elif 'SDS' in sensor_name %}fa-wind
                                                    {% elif 'ENS' in sensor_name %}fa-leaf
                                                    {% else %}fa-microchip{% endif %}">
                                        </i>
                                    </div>
                                    {{ sensor_name }}
                                </div>
                            </div>
                            
                            <div class="params-grid">
                                {% for param_name, param_data in sensor_data.items() %}
                                    <div class="param-item">
                                        <div class="param-name">
                                            <i class="fas {% if 'Temperature' in param_name %}fa-thermometer-half icon-temperature
                                                        {% elif 'Humidity' in param_name %}fa-tint icon-humidity
                                                        {% elif 'Pressure' in param_name %}fa-tachometer-alt icon-pressure
                                                        {% elif 'pm25' in param_name or 'pm10' in param_name %}fa-smog icon-pm
                                                        {% elif 'AQI' in param_name %}fa-wind icon-air
                                                        {% elif 'TVOC' in param_name %}fa-industry icon-air
                                                        {% elif 'eCO2' in param_name %}fa-leaf icon-air
                                                        {% else %}fa-chart-bar icon-generic{% endif %}">
                                            </i>
                                            {{ param_data.description }}
                                        </div>
                                        <div class="param-value-container">
                                            <span class="param-value">{{ param_data.value }}</span>
                                            {% if param_data.unit %}
                                                <span class="param-unit">{{ param_data.unit }}</span>
                                            {% endif %}
                                        </div>
                                        <div class="param-timestamp">
                                            <i class="far fa-clock"></i>
                                            <span>{{ param_data.timestamp|datetime_format_short }}</span>
                                            <span class="time-ago" data-timestamp="{{ param_data.timestamp }}">
                                                <!-- Заполнится JavaScript -->
                                            </span>
                                        </div>
                                        {% if param_data.status %}
                                            <div class="param-status">
                                                <i class="fas fa-info-circle"></i> {{ param_data.status }}
                                            </div>
                                        {% endif %}
                                    </div>
                                {% endfor %}
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Секция 2: Service Data -->
            <div class="section fade-in">
                <div class="section-title">
                    <div class="title-icon">
                        <i class="fas fa-cogs"></i>
                    </div>
                    Служебная информация
                </div>
                
                <div class="service-grid">
                    {% for service_name, service_data in service_data_dict.items() %}
                        <div class="service-item">
                            <div class="service-header">
                                <div class="service-name">
                                    <div class="service-icon">
                                        <i class="fas {% if 'AHT' in service_name or 'BMP' in service_name %}fa-thermometer-half
                                                    {% elif 'ENS' in service_name %}fa-leaf
                                                    {% elif 'SDS' in service_name %}fa-wind
                                                    {% elif 'CPU' in service_name %}fa-microchip
                                                    {% elif 'sensor.community' in service_name %}fa-cloud-upload-alt
                                                    {% else %}fa-cog{% endif %}">
                                        </i>
                                    </div>
                                    {{ service_name }}
                                </div>
                            </div>
                            
                            <div class="service-message">
                                {{ service_data.message }}
                            </div>
                            
                            <div class="service-timestamp">
                                <i class="far fa-calendar-alt"></i>
                                <span>{{ service_data.timestamp|datetime_format }}</span>
                                <span class="time-ago" data-timestamp="{{ service_data.timestamp }}">
                                    <!-- Заполнится JavaScript -->
                                </span>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <!-- Футер -->
        <div class="footer">
            <div class="update-info">
                <i class="fas fa-sync-alt"></i>
                <span>Автообновление каждые 5 секунд</span>
            </div>
            
            <div class="controls">
                <button class="btn btn-refresh" onclick="refreshData()">
                    <i class="fas fa-redo"></i> Обновить сейчас
                </button>
                <button class="btn btn-json" onclick="showJsonData()">
                    <i class="fas fa-code"></i> Показать JSON
                </button>
            </div>
        </div>
    </div>
    
    <script>
        // Форматирование времени
        function formatDateTime(timestamp) {
            if (!timestamp) return 'неизвестно';
            const date = new Date(timestamp * 1000);
            return date.toLocaleString('ru-RU');
        }
        
        // Форматирование времени коротко
        function formatDateTimeShort(timestamp) {
            if (!timestamp) return '';
            const date = new Date(timestamp * 1000);
            return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        }
        
        // Расчет времени назад с округлением до целого
        function timeAgo(timestamp) {
            if (!timestamp) return '';
            const now = Math.floor(Date.now() / 1000);
            const diff = Math.round(now - timestamp); // Округляем до целого
            
            if (diff < 60) return `${diff} сек. назад`;
            if (diff < 3600) return `${Math.floor(diff / 60)} мин. назад`;
            if (diff < 86400) return `${Math.floor(diff / 3600)} час. назад`;
            return `${Math.floor(diff / 86400)} дн. назад`;
        }
        
        // Обновление времени "X сек. назад" для всех элементов
        function updateTimeAgo() {
            document.querySelectorAll('.time-ago').forEach(el => {
                const timestamp = parseFloat(el.getAttribute('data-timestamp'));
                if (timestamp) {
                    el.textContent = timeAgo(timestamp);
                }
            });
        }
        
        // Обновление времени в шапке (берем самый свежий timestamp)
        function updateHeaderTime() {
            // Находим все timestamps на странице
            const timestamps = Array.from(document.querySelectorAll('.time-ago'))
                .map(el => parseFloat(el.getAttribute('data-timestamp')))
                .filter(ts => ts && !isNaN(ts));
            
            if (timestamps.length > 0) {
                // Берем самый свежий timestamp
                const latestTimestamp = Math.max(...timestamps);
                const lastDataElement = document.getElementById('lastDataTime');
                if (lastDataElement) {
                    lastDataElement.textContent = formatDateTime(latestTimestamp);
                }
            }
        }
        
        // Обновление таймера
        function updateTimer() {
            const timerBar = document.getElementById('timerBar');
            if (timerBar) {
                timerBar.style.transition = 'none';
                timerBar.style.width = '0%';
                
                setTimeout(() => {
                    timerBar.style.transition = 'width 60s linear';
                    timerBar.style.width = '100%';
                }, 10);
            }
        }
        
        // Ручное обновление страницы
        function refreshData() {
            const btn = event.target.closest('.btn');
            if (btn) {
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обновление...';
                btn.disabled = true;
                
                location.reload();
                
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }, 2000);
            }
        }
        
        // Показать JSON данные
        function showJsonData() {
            fetch('/api')
                .then(response => response.json())
                .then(data => {
                    // Модальное окно для JSON
                    const modal = document.createElement('div');
                    modal.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background: rgba(0,0,0,0.8);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        z-index: 1000;
                        padding: 20px;
                    `;
                    
                    modal.innerHTML = `
                        <div style="
                            background: #1e1e1e;
                            color: #d4d4d4;
                            padding: 30px;
                            border-radius: 10px;
                            max-width: 90%;
                            max-height: 90%;
                            overflow: auto;
                            position: relative;
                            width: 800px;
                        ">
                            <button onclick="this.parentElement.parentElement.remove()" style="
                                position: absolute;
                                top: 15px;
                                right: 15px;
                                background: #e74c3c;
                                color: white;
                                border: none;
                                width: 30px;
                                height: 30px;
                                border-radius: 50%;
                                cursor: pointer;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: 1rem;
                            ">
                                <i class="fas fa-times"></i>
                            </button>
                            <h3 style="color: white; margin-bottom: 20px;">JSON данные</h3>
                            <pre style="
                                background: #252526;
                                padding: 20px;
                                border-radius: 5px;
                                overflow: auto;
                                font-family: 'Courier New', monospace;
                                font-size: 14px;
                                line-height: 1.5;
                                max-height: 70vh;
                            ">${JSON.stringify(data, null, 2)}</pre>
                        </div>
                    `;
                    
                    document.body.appendChild(modal);
                })
                .catch(error => {
                    console.error('Ошибка получения JSON:', error);
                    alert('Ошибка получения данных');
                });
        }
        
        // Инициализация
        document.addEventListener('DOMContentLoaded', function() {
            // Сразу обновляем время "X сек. назад"
            updateTimeAgo();
            updateHeaderTime();
            updateTimer();
            
            // Автообновление времени "X сек. назад" каждую секунду
            setInterval(() => {
                updateTimeAgo();
                updateHeaderTime();
            }, 1000);
            
            // Автообновление страницы каждые 60 секунд
            setTimeout(() => {
                location.reload();
            }, 60000);
            
            // Сброс таймера при активности пользователя
            document.addEventListener('mousemove', () => {
                clearTimeout(window.reloadTimeout);
                window.reloadTimeout = setTimeout(() => {
                    location.reload();
                }, 60000);
            });
            
            // Анимация появления элементов
            const fadeElements = document.querySelectorAll('.fade-in');
            fadeElements.forEach((el, index) => {
                setTimeout(() => {
                    el.style.opacity = '1';
                    el.style.transform = 'translateY(0)';
                }, index * 100);
            });
        });
    </script>
</body>
</html>
'''

class FlaskSensorApp:
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.shared_dict = None
        self.lock = None
        
        # Регистрируем кастомные фильтры для Jinja2
        @self.app.template_filter('datetime_format')
        def datetime_format(timestamp):
            """Фильтр для форматирования timestamp в читаемый вид"""
            try:
                if isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp)
                    return dt.strftime('%d.%m.%Y %H:%M:%S')
            except:
                pass
            return str(timestamp)
        
        @self.app.template_filter('datetime_format_short')
        def datetime_format_short(timestamp):
            """Фильтр для короткого форматирования времени"""
            try:
                if isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp)
                    return dt.strftime('%H:%M:%S')
            except:
                pass
            return ''
        
        # Настраиваем маршруты
        self.setup_routes()
    
    def setup_routes(self):
        """Настройка маршрутов Flask"""
        
        @self.app.route('/')
        def index():
            """Главная страница с данными датчиков"""
            if not self.shared_dict:
                return self._error_page("Данные датчиков недоступны")
            
            with self.lock:
                data = dict(self.shared_dict)  # Копируем данные
            
            # Подготавливаем данные для шаблона
            sensor_data = data.get('Sensor data', {})
            service_data = data.get('Service data', {})
            
            # Находим самый свежий timestamp из всех данных
            latest_timestamp = 0
            
            # Фильтруем sensor_data - только валидные словари
            filtered_sensor_data = {}
            if isinstance(sensor_data, dict):
                for sensor_name, sensor_values in sensor_data.items():
                    # Проверяем что sensor_values это словарь
                    if isinstance(sensor_values, dict):
                        filtered_params = {}
                        for param_name, param_data in sensor_values.items():
                            # Проверяем что param_data это словарь
                            if isinstance(param_data, dict):
                                filtered_params[param_name] = param_data
                                
                                # Обновляем latest_timestamp
                                if 'timestamp' in param_data:
                                    ts = param_data['timestamp']
                                    if isinstance(ts, (int, float)):
                                        latest_timestamp = max(latest_timestamp, ts)
                            else:
                                # Если param_data не словарь, логируем и пропускаем
                                print(f"⚠️  {sensor_name}.{param_name}: пропущен (не словарь: {type(param_data)})")
                        
                        if filtered_params:  # Добавляем только если есть параметры
                            filtered_sensor_data[sensor_name] = filtered_params
                    else:
                        # Если sensor_values не словарь, логируем
                        print(f"⚠️  {sensor_name}: пропущен (не словарь: {type(sensor_values)})")
            else:
                print(f"⚠️  Sensor data не словарь: {type(sensor_data)}")
            
            # Фильтруем service_data
            filtered_service_data = {}
            if isinstance(service_data, dict):
                for service_name, service_values in service_data.items():
                    if isinstance(service_values, dict):
                        filtered_service_data[service_name] = service_values
                        if 'timestamp' in service_values:
                            ts = service_values['timestamp']
                            if isinstance(ts, (int, float)):
                                latest_timestamp = max(latest_timestamp, ts)
                    else:
                        # Если service_values не словарь, преобразуем
                        filtered_service_data[service_name] = {
                            'message': str(service_values),
                            'timestamp': time.time()
                        }
            else:
                print(f"⚠️  Service data не словарь: {type(service_data)}")
            
            # Если нет timestamp, используем текущее время
            if latest_timestamp == 0:
                latest_timestamp = time.time()
            
            return render_template_string(
                HTML_TEMPLATE,
                sensor_data_dict=filtered_sensor_data,
                service_data_dict=filtered_service_data,
                latest_timestamp=latest_timestamp
            )
        
        @self.app.route('/api')
        def api_data():
            """API endpoint для получения данных в JSON формате"""
            if not self.shared_dict:
                return jsonify({'error': 'Data not available'}), 503
            
            with self.lock:
                data = dict(self.shared_dict)
            
            return jsonify(data)
        
        @self.app.route('/api/health')
        def api_health():
            """Health check endpoint"""
            if not self.shared_dict:
                return jsonify({'status': 'unhealthy', 'message': 'No data'}), 503
            
            with self.lock:
                data = dict(self.shared_dict)
            
            # Проверяем свежесть данных
            now = time.time()
            max_age = 0
            
            sensor_data = data.get('Sensor data', {})
            if isinstance(sensor_data, dict):
                for sensor_values in sensor_data.values():
                    if isinstance(sensor_values, dict):
                        for param_data in sensor_values.values():
                            if isinstance(param_data, dict) and 'timestamp' in param_data:
                                ts = param_data.get('timestamp', 0)
                                if isinstance(ts, (int, float)):
                                    age = now - ts
                                    max_age = max(max_age, age)
            
            has_data = bool(sensor_data)
            is_fresh = max_age < 30  # Данные не старше 30 секунд
            
            return jsonify({
                'status': 'healthy' if has_data and is_fresh else 'unhealthy',
                'data_age': max_age,
                'has_data': has_data,
                'timestamp': now
            })
    
    def _error_page(self, message):
        """Страница ошибки"""
        error_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ошибка</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }}
                .error-container {{
                    background: rgba(255, 255, 255, 0.95);
                    padding: 50px;
                    border-radius: 20px;
                    text-align: center;
                    max-width: 600px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                .error-icon {{
                    font-size: 4rem;
                    color: #e74c3c;
                    margin-bottom: 30px;
                }}
                h1 {{
                    color: #2c3e50;
                    margin-bottom: 20px;
                    font-size: 2.2rem;
                }}
                p {{
                    color: #7f8c8d;
                    margin-bottom: 40px;
                    font-size: 1.1rem;
                    line-height: 1.6;
                }}
                .btn {{
                    padding: 15px 35px;
                    background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    cursor: pointer;
                    font-size: 1.1rem;
                    font-weight: 600;
                    transition: all 0.3s;
                    display: inline-flex;
                    align-items: center;
                    gap: 10px;
                }}
                .btn:hover {{
                    transform: translateY(-3px);
                    box-shadow: 0 10px 25px rgba(52, 152, 219, 0.4);
                }}
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <h1>Система мониторинга</h1>
                <p>{message}</p>
                <button class="btn" onclick="location.reload()">
                    <i class="fas fa-redo"></i> Попробовать снова
                </button>
            </div>
        </body>
        </html>
        '''
        return error_html
    
    def set_shared_data(self, shared_dict, lock):
        """Установка shared данных и блокировки"""
        self.shared_dict = shared_dict
        self.lock = lock
    
    def run(self):
        """Запуск Flask сервера"""
        print(f"🌐 Запуск веб-сервера на http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True, use_reloader=False)


def start_flask_app(shared_dict, lock, host='0.0.0.0', port=5000):
    """
    Функция для запуска Flask приложения
    shared_dict - общий словарь с данными датчиков
    lock - блокировка для безопасного доступа
    """
    flask_app = FlaskSensorApp(host=host, port=port)
    flask_app.set_shared_data(shared_dict, lock)
    flask_app.run()


def start_flask_in_thread(shared_dict, lock, host='0.0.0.0', port=5000):
    """
    Запуск Flask в отдельном потоке
    Возвращает объект потока
    """
    flask_thread = threading.Thread(
        target=start_flask_app,
        args=(shared_dict, lock, host, port),
        name="FlaskWebServer",
        daemon=True
    )
    flask_thread.start()
    
    # Ждем немного чтобы сервер успел запуститься
    import time
    time.sleep(1)