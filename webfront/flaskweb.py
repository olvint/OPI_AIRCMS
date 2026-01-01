#!/usr/bin/env python3
"""
Flask веб-интерфейс для отображения данных с датчиков
Запускается в отдельном потоке
"""

import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify

# HTML шаблон с тремя секциями
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
            --success: #27ae60;
            --warning: #f39c12;
            --danger: #e74c3c;
            --dark: #2c3e50;
            --light: #ecf0f1;
            --gray: #95a5a6;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            color: #333;
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
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .header-info {
            flex: 1;
        }
        
        h1 {
            color: var(--dark);
            font-size: 2.2rem;
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .subtitle {
            color: var(--gray);
            font-size: 1rem;
            margin-bottom: 15px;
        }
        
        .last-update {
            background: var(--light);
            padding: 10px 15px;
            border-radius: 10px;
            font-size: 0.9rem;
            color: var(--dark);
            display: inline-flex;
            align-items: center;
            gap: 8px;
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
            padding: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--light);
        }
        
        .section-title {
            color: var(--dark);
            font-size: 1.5rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .section-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary) 0%, #2980b9 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        /* Грид для датчиков (2 в ряд) */
        .sensor-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }
        
        @media (max-width: 1100px) {
            .sensor-grid {
                grid-template-columns: 1fr;
            }
        }
        
        /* Карточка датчика */
        .sensor-card {
            background: #f8fafc;
            border-radius: 12px;
            padding: 25px;
            border-left: 5px solid var(--primary);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            height: 100%;
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
            background: linear-gradient(135deg, var(--primary) 0%, #2980b9 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        /* Параметры датчика (2 в ряд) */
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
            padding: 18px;
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
        
        .param-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--dark);
            margin-bottom: 5px;
            line-height: 1.2;
        }
        
        .param-unit {
            font-size: 0.9rem;
            color: var(--primary);
            font-weight: 600;
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
        
        /* Секция статуса */
        .status-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .status-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            margin-top: 20px;
        }
        
        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }
        
        .status-title {
            font-size: 1.3rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .status-badge {
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .status-ok {
            background: var(--success);
            color: white;
        }
        
        .status-error {
            background: var(--danger);
            color: white;
        }
        
        .status-warning {
            background: var(--warning);
            color: white;
        }
        
        .status-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .status-item {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            padding: 20px;
        }
        
        .status-label {
            font-size: 0.9rem;
            opacity: 0.9;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-text {
            font-size: 1.3rem;
            font-weight: 600;
        }
        
        .timestamp {
            font-family: 'Courier New', monospace;
            background: rgba(0, 0, 0, 0.2);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9rem;
        }
        
        /* Управление */
        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 25px;
            padding-top: 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
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
            background: white;
            color: var(--dark);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0,0,0,0.15);
        }
        
        .btn-refresh {
            background: white;
            color: var(--primary);
        }
        
        .btn-json {
            background: white;
            color: var(--success);
        }
        
        /* Иконки */
        .icon-temperature { color: #ff6b6b; }
        .icon-humidity { color: #4d96ff; }
        .icon-pressure { color: #9c88ff; }
        .icon-air { color: #10ac84; }
        .icon-pm { color: #ff9f43; }
        .icon-cpu { color: #8395a7; }
        .icon-time { color: #574b90; }
        .icon-generic { color: var(--gray); }
        
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
        
        /* Прогресс бар */
        .update-progress {
            height: 4px;
            background: var(--light);
            border-radius: 2px;
            margin-top: 10px;
            overflow: hidden;
        }
        
        .progress-bar {
            height: 100%;
            background: var(--primary);
            width: 0%;
            transition: width 60s linear;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <!-- Шапка -->
        <div class="header fade-in">
            <div class="header-info">
                <h1><i class="fas fa-chart-network"></i> Система мониторинга</h1>
                <p class="subtitle">Реальное время | Все датчики онлайн</p>
                <div class="last-update" id="lastUpdate">
                    <i class="fas fa-clock"></i> Последнее обновление: <span id="updateTime">загружается...</span>
                </div>
                <div class="update-progress">
                    <div class="progress-bar" id="progressBar"></div>
                </div>
            </div>
        </div>
        
        <div class="sections-container">
            <!-- Секция 1: Основные датчики -->
            <div class="section fade-in">
                <div class="section-header">
                    <div class="section-title">
                        <div class="section-icon">
                            <i class="fas fa-microchip"></i>
                        </div>
                        Основные датчики
                    </div>
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
                                            <i class="fas {% if 'Temperature' in param_name or 'temp' in param_name.lower() %}fa-thermometer-half icon-temperature
                                                        {% elif 'Humidity' in param_name or 'hum' in param_name.lower() %}fa-tint icon-humidity
                                                        {% elif 'Pressure' in param_name or 'press' in param_name.lower() %}fa-tachometer-alt icon-pressure
                                                        {% elif 'PM' in param_name or 'pm' in param_name %}fa-smog icon-pm
                                                        {% elif 'AQI' in param_name %}fa-wind icon-air
                                                        {% elif 'TVOC' in param_name %}fa-industry icon-air
                                                        {% elif 'CO2' in param_name or 'eco2' in param_name.lower() %}fa-leaf icon-air
                                                        {% else %}fa-chart-bar icon-generic{% endif %}">
                                            </i>
                                            {{ param_data.description }}
                                        </div>
                                        <div class="param-value">{{ param_data.value }}</div>
                                        <div class="param-unit">{{ param_data.unit }}</div>
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
            
            <!-- Секция 2: Служебные датчики -->
            <div class="section fade-in">
                <div class="section-header">
                    <div class="section-title">
                        <div class="section-icon">
                            <i class="fas fa-server"></i>
                        </div>
                        Служебные датчики
                    </div>
                </div>
                
                <div class="sensor-grid">
                    {% for key, value in service_data_dict.items() %}
                        <div class="sensor-card">
                            <div class="sensor-header">
                                <div class="sensor-name">
                                    <div class="sensor-icon">
                                        <i class="fas {% if 'cpu' in key.lower() or 'temperature' in key.lower() %}fa-microchip
                                                    {% elif 'time' in key.lower() %}fa-clock
                                                    {% elif 'memory' in key.lower() %}fa-memory
                                                    {% elif 'disk' in key.lower() %}fa-hdd
                                                    {% elif 'network' in key.lower() %}fa-network-wired
                                                    {% else %}fa-cog{% endif %}">
                                        </i>
                                    </div>
                                    {{ value.description if value.description is defined else key }}
                                </div>
                            </div>
                            
                            <div class="params-grid">
                                {% if key == 'timestamp' %}
                                    <div class="param-item" style="grid-column: span 2;">
                                        <div class="param-name">
                                            <i class="fas fa-clock icon-time"></i>
                                            Время измерения
                                        </div>
                                        <div class="param-value timestamp">{{ value|datetime_format }}</div>
                                        <div class="param-unit">системное время</div>
                                    </div>
                                {% else %}
                                    <div class="param-item">
                                        <div class="param-name">
                                            <i class="fas fa-chart-bar icon-generic"></i>
                                            Значение
                                        </div>
                                        <div class="param-value">{{ value.value if value.value is defined else value }}</div>
                                        <div class="param-unit">{{ value.unit if value.unit is defined else '' }}</div>
                                    </div>
                                    
                                    {% if value.description is defined and key != value.description %}
                                        <div class="param-item">
                                            <div class="param-name">
                                                <i class="fas fa-info-circle icon-generic"></i>
                                                Описание
                                            </div>
                                            <div class="param-value" style="font-size: 1.2rem;">{{ value.description }}</div>
                                        </div>
                                    {% endif %}
                                {% endif %}
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Секция 3: Статус системы -->
            <div class="section status-section fade-in">
                <div class="section-header">
                    <div class="section-title" style="color: white;">
                        <div class="section-icon" style="background: rgba(255, 255, 255, 0.2);">
                            <i class="fas fa-heartbeat"></i>
                        </div>
                        Статус системы
                    </div>
                </div>
                
                <div class="status-card">
                    <div class="status-header">
                        <div class="status-title">
                            <i class="fas fa-shield-alt"></i>
                            Состояние мониторинга
                        </div>
                        {% if sensor_status %}
                            <div class="status-badge status-{{ sensor_status.status.lower() }}">
                                {{ sensor_status.status }}
                            </div>
                        {% endif %}
                    </div>
                    
                    <div class="status-content">
                        {% if sensor_status %}
                            <div class="status-item">
                                <div class="status-label">
                                    <i class="fas fa-comment-alt"></i>
                                    Сообщение
                                </div>
                                <div class="status-text">{{ sensor_status.text }}</div>
                            </div>
                            
                            <div class="status-item">
                                <div class="status-label">
                                    <i class="fas fa-clock"></i>
                                    Время статуса
                                </div>
                                <div class="status-text timestamp">{{ sensor_status.timestamp|datetime_format }}</div>
                            </div>
                            
                            <div class="status-item">
                                <div class="status-label">
                                    <i class="fas fa-history"></i>
                                    Активность
                                </div>
                                <div class="status-text">
                                    <i class="fas fa-circle" style="color: #2ecc71; margin-right: 8px;"></i>
                                    Система активна
                                </div>
                            </div>
                        {% else %}
                            <div class="status-item">
                                <div class="status-label">
                                    <i class="fas fa-exclamation-triangle"></i>
                                    Статус недоступен
                                </div>
                                <div class="status-text">Данные о состоянии системы не получены</div>
                            </div>
                        {% endif %}
                    </div>
                    
                    <div class="controls">
                        <button class="btn btn-refresh" onclick="refreshData()">
                            <i class="fas fa-redo"></i> Обновить данные
                        </button>
                        <button class="btn btn-json" onclick="showJsonData()">
                            <i class="fas fa-code"></i> Показать JSON
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Элементы DOM
        const lastUpdateElement = document.getElementById('lastUpdate');
        const updateTimeElement = document.getElementById('updateTime');
        const progressBar = document.getElementById('progressBar');
        
        // Форматирование времени
        function formatDateTime(timestamp) {
            if (!timestamp) return 'неизвестно';
            const date = new Date(timestamp * 1000);
            return date.toLocaleString('ru-RU');
        }
        
        // Обновление времени и прогресс-бара
        function updateTimeAndProgress() {
            fetch('/api/timestamp')
                .then(response => response.json())
                .then(data => {
                    if (data.timestamp) {
                        const formattedTime = formatDateTime(data.timestamp);
                        updateTimeElement.textContent = formattedTime;
                        
                        // Сброс и запуск прогресс-бара
                        progressBar.style.width = '0%';
                        setTimeout(() => {
                            progressBar.style.width = '100%';
                        }, 10);
                    }
                })
                .catch(error => {
                    console.error('Ошибка обновления времени:', error);
                    updateTimeElement.textContent = 'ошибка';
                });
        }
        
        // Ручное обновление страницы
        function refreshData() {
            const btn = event.target;
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обновление...';
            btn.disabled = true;
            
            // Перезагружаем страницу
            location.reload();
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 2000);
        }
        
        // Показать JSON данные
        function showJsonData() {
            fetch('/api/raw')
                .then(response => response.json())
                .then(data => {
                    // Создаем модальное окно
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
                    
                    const modalContent = document.createElement('div');
                    modalContent.style.cssText = `
                        background: #1e1e1e;
                        color: #d4d4d4;
                        padding: 30px;
                        border-radius: 10px;
                        max-width: 90%;
                        max-height: 90%;
                        overflow: auto;
                        position: relative;
                    `;
                    
                    const closeBtn = document.createElement('button');
                    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
                    closeBtn.style.cssText = `
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
                    `;
                    closeBtn.onclick = () => modal.remove();
                    
                    const pre = document.createElement('pre');
                    pre.style.cssText = `
                        font-family: 'Courier New', monospace;
                        font-size: 14px;
                        line-height: 1.5;
                    `;
                    pre.textContent = JSON.stringify(data, null, 2);
                    
                    modalContent.appendChild(closeBtn);
                    modalContent.appendChild(pre);
                    modal.appendChild(modalContent);
                    document.body.appendChild(modal);
                })
                .catch(error => {
                    console.error('Ошибка получения JSON:', error);
                    alert('Ошибка получения данных');
                });
        }
        
        // Автообновление времени каждые 5 секунд
        setInterval(() => {
            updateTimeAndProgress();
        }, 5000);
        
        // Автообновление страницы каждые 60 секунд
        let reloadTimeout = setTimeout(() => {
            location.reload();
        }, 60000);
        
        // Сброс таймера при активности пользователя
        document.addEventListener('mousemove', () => {
            clearTimeout(reloadTimeout);
            reloadTimeout = setTimeout(() => {
                location.reload();
            }, 60000);
        });
        
        // Инициализация
        updateTimeAndProgress();
        
        // Анимация при загрузке
        document.addEventListener('DOMContentLoaded', function() {
            const elements = document.querySelectorAll('.fade-in');
            elements.forEach((el, index) => {
                setTimeout(() => {
                    el.style.opacity = '1';
                    el.style.transform = 'translateY(0)';
                }, index * 200);
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
        
        # Регистрируем кастомный фильтр для Jinja2
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
            sensor_status = data.get('sensor status', {})
            
            # Унифицированная обработка Service data
            processed_service_data = {}
            for key, value in service_data.items():
                if isinstance(value, dict) and 'value' in value:
                    # Если уже словарь с value
                    processed_service_data[key] = value
                elif key == 'timestamp':
                    # Особый случай для timestamp
                    processed_service_data[key] = value
                else:
                    # Преобразуем в словарь
                    processed_service_data[key] = {
                        'value': value,
                        'description': key,
                        'unit': ''
                    }
            
            return render_template_string(
                HTML_TEMPLATE,
                sensor_data_dict=sensor_data,
                service_data_dict=processed_service_data,
                sensor_status=sensor_status
            )
        
        @self.app.route('/api/data')
        def api_data():
            """API endpoint для получения структурированных данных"""
            if not self.shared_dict:
                return jsonify({'error': 'Data not available'}), 503
            
            with self.lock:
                data = dict(self.shared_dict)
            
            return jsonify(data)
    
        
        @self.app.route('/api/timestamp')
        def api_timestamp():
            """API для получения timestamp"""
            if not self.shared_dict:
                return jsonify({'timestamp': None}), 503
            
            with self.lock:
                data = dict(self.shared_dict)
            
            timestamp = data.get('Service data', {}).get('timestamp', time.time())
            
            return jsonify({'timestamp': timestamp})
        
        @self.app.route('/api/status')
        def api_status():
            """API для получения статуса"""
            if not self.shared_dict:
                return jsonify({'status': 'ERROR', 'message': 'No data'}), 503
            
            with self.lock:
                data = dict(self.shared_dict)
            
            status_data = data.get('sensor status', {})
            
            return jsonify({
                'status': status_data.get('status', 'UNKNOWN'),
                'message': status_data.get('text', 'No status message'),
                'timestamp': status_data.get('timestamp', time.time())
            })
        
        @self.app.route('/api/health')
        def api_health():
            """Health check endpoint"""
            if not self.shared_dict:
                return jsonify({'status': 'unhealthy', 'message': 'No data'}), 503
            
            with self.lock:
                data = dict(self.shared_dict)
            
            has_data = bool(data.get('Sensor data', {}))
            status = data.get('sensor status', {}).get('status', 'UNKNOWN')
            age = time.time() - data.get('Service data', {}).get('timestamp', 0)
            
            return jsonify({
                'status': 'healthy' if has_data and status == 'OK' and age < 30 else 'unhealthy',
                'sensor_status': status,
                'data_age': age,
                'has_data': has_data,
                'timestamp': time.time()
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
    
    return flask_thread