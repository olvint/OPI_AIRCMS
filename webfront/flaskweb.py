#!/usr/bin/env python3
import time
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from typing import Dict, Any
import multiprocessing
import threading


app = Flask(__name__)

# Глобальные переменные для shared данных
shared_dict = None
lock = None


def init_shared_data(s_dict, s_lock):
    """Инициализация shared данных"""
    global shared_dict, lock
    shared_dict = s_dict
    lock = s_lock


def start(s_dict, s_lock):
    """Запуск Flask сервера"""
    init_shared_data(s_dict, s_lock)
    
    print("🌐 Flask сервер запущен на http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


def get_air_data() -> Dict[str, Any]:
    """Безопасное получение данных из shared_dict"""
    if shared_dict is None or lock is None:
        return {'status': 'error', 'error': 'Shared data not initialized'}
    
    with lock:
        # Создаем копию данных
        return dict(shared_dict.get('air', {}))


def format_value(value, format_str: str = '{:.1f}', default: str = '----') -> str:
    """Форматирование значения с проверкой на None"""
    if value is None:
        return default
    try:
        return format_str.format(value)
    except (ValueError, TypeError):
        return default


def get_air_quality_category(pm25: float) -> Dict[str, Any]:
    """Определение категории качества воздуха по PM2.5"""
    if pm25 is None:
        return {'category': 'Нет данных', 'color': '#888', 'emoji': '❓'}
    elif pm25 <= 15:
        return {'category': 'Отличный', 'color': '#10B981', 'emoji': '😊'}
    elif pm25 <= 30:
        return {'category': 'Хороший', 'color': '#3B82F6', 'emoji': '🙂'}
    elif pm25 <= 55:
        return {'category': 'Умеренный', 'color': '#F59E0B', 'emoji': '😐'}
    elif pm25 <= 110:
        return {'category': 'Плохой', 'color': '#EF4444', 'emoji': '😷'}
    else:
        return {'category': 'Очень плохой', 'color': '#7C3AED', 'emoji': '🤢'}


@app.route('/')
def dashboard():
    """Главная страница с дашбордом"""
    air_data = get_air_data()
    
    # Форматирование данных
    status = air_data.get('status', 'error')
    timestamp = air_data.get('timestamp', 0)
    temp = air_data.get('temperature')
    press = air_data.get('pressure')
    pm25 = air_data.get('pm25')
    pm10 = air_data.get('pm10')
    cpu_temp = air_data.get('cpu_temp')  # ← Температура процессора
    error = air_data.get('error', '')
    
    # Качество воздуха
    quality = get_air_quality_category(pm25)
    
    # Человеческий формат времени
    if timestamp:
        time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S %d.%m.%Y')
        time_ago = int(time.time() - timestamp)
        if time_ago < 60:
            ago_str = f"({time_ago} сек назад)"
        elif time_ago < 3600:
            ago_str = f"({time_ago // 60} мин назад)"
        else:
            ago_str = f"({time_ago // 3600} ч назад)"
    else:
        time_str = 'Нет данных'
        ago_str = ''
    
    # Форматирование значений
    temp_str = format_value(temp, '{:.1f}°C')
    press_str = format_value(press, '{:.1f} гПа')
    pm25_str = format_value(pm25, '{:.1f} μg/m³')
    pm10_str = format_value(pm10, '{:.1f} μg/m³')
    cpu_temp_str = format_value(cpu_temp, '{:.1f}°C')  # ← Форматирование температуры CPU


    
    # HTML шаблон с улучшениями
    html_template = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌡️ Мониторинг воздуха | HW-611 + SDS011</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 900px; 
            margin: 0 auto; 
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 30px;
        }
        .header {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .header h1 { 
            font-size: 2.2em; 
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header h2 {
            font-size: 1.2em;
            color: #666;
            font-weight: normal;
            margin-bottom: 20px;
        }
        .status {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 50px;
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 20px;
        }
        .status.ok { background: #d4edda; color: #155724; border: 2px solid #155724; }
        .status.error { background: #f8d7da; color: #721c24; border: 2px solid #721c24; }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .grid-second-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            border-top: 5px solid;
        }
        .card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 15px 30px rgba(0,0,0,0.15);
        }
        .value {
            font-size: 2.8em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .temp .value { color: #ff6b6b; }
        .press .value { color: #4ecdc4; }
        .pm25 .value { color: #45b7d1; }
        .pm10 .value { color: #f9ca24; }
        .label { 
            color: #666; 
            font-size: 1.2em;
            margin-bottom: 10px;
            font-weight: 500;
        }
        .sub-label {
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .quality-indicator {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 15px;
            color: white;
            font-size: 1.1em;
        }
        .cpu-info {
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 10px;
            margin-top: 20px;
            border-left: 4px solid #667eea;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .cpu-info-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .cpu-temp {
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }
        .cpu-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .cpu-model {
            color: #666;
            font-size: 0.9em;
        }
        .error-box {
            background: #f8d7da;
            color: #721c24;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #dc3545;
            margin: 20px 0;
        }
        .last-update {
            text-align: center;
            color: #666;
            font-size: 1em;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .last-update .time {
            font-weight: bold;
            color: #333;
        }
        .api-links {
            text-align: center;
            margin-top: 20px;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        .api-links a {
            color: #667eea;
            text-decoration: none;
            padding: 8px 15px;
            border: 1px solid #667eea;
            border-radius: 5px;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .api-links a:hover {
            background: #667eea;
            color: white;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
        }
        @media (max-width: 768px) {
            .grid, .grid-second-row { grid-template-columns: 1fr; }
            .header h1 { font-size: 1.8em; }
            .value { font-size: 2.2em; }
            .container { padding: 15px; }
            .cpu-info {
                flex-direction: column;
                gap: 10px;
                align-items: flex-start;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌡️ Мониторинг воздуха</h1>
            <h2>Датчики: BMP280 (температура/давление) + SDS011 (PM2.5/PM10)</h2>
            <div class="status {{ 'ok' if status == 'ok' else 'error' }}">
                {{ '🟢 ОНЛАЙН' if status == 'ok' else '🔴 ОШИБКА' }}
            </div>
        </div>
        
        <!-- ПЕРВАЯ СТРОКА: PM2.5 и PM10 -->
        <div class="grid">
            <div class="card pm25" style="border-color: #45b7d1;">
                <div class="label">PM2.5</div>
                <div class="value">{{ pm25_str }}</div>
                <div class="sub-label">Мелкие частицы (&lt; 2.5 мкм)</div>
                {% if pm25 is not none %}
                <div class="quality-indicator" style="background: {{ quality.color }};">
                    {{ quality.emoji }} {{ quality.category }}
                </div>
                {% endif %}
            </div>
            
            <div class="card pm10" style="border-color: #f9ca24;">
                <div class="label">PM10</div>
                <div class="value">{{ pm10_str }}</div>
                <div class="sub-label">Крупные частицы (&lt; 10 мкм)</div>
            </div>
        </div>
        
        <!-- ВТОРАЯ СТРОКА: Температура и давление -->
        <div class="grid-second-row">
            <div class="card temp" style="border-color: #ff6b6b;">
                <div class="label">Температура</div>
                <div class="value">{{ temp_str }}</div>
                <div class="sub-label">Воздух</div>
            </div>
            
            <div class="card press" style="border-color: #4ecdc4;">
                <div class="label">Давление</div>
                <div class="value">{{ press_str }}</div>
                <div class="sub-label">Атмосферное</div>
            </div>
        </div>
        
        <!-- ИНФОРМАЦИЯ О ПРОЦЕССОРЕ -->
        {% if cpu_temp is not none %}
        <div class="cpu-info">
            <div class="cpu-info-left">
                <div class="cpu-temp">
                    Температура процессора: {{ cpu_temp_str }}
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if error %}
        <div class="error-box">
            <strong>❌ Ошибка:</strong> {{ error }}
        </div>
        {% endif %}
        
        <div class="last-update">
            ⏰ Последние данные: <span class="time">{{ time_str }}</span> {{ ago_str }}
        </div>
        
        <div class="api-links">
            <a href="/api/json" target="_blank">📊 JSON API</a>
            <a href="/health" target="_blank">❤️ Health Check</a>
            <a href="/about" target="_blank">📖 О качестве воздуха</a>
            <a href="javascript:location.reload()">🔄 Обновить</a>
        </div>
        
        <div class="footer">
            <p>Система мониторинга воздуха | HW-611 + SDS011 | Данные обновляются каждые 5 сек</p>
        </div>
    </div>
    
    <script>
        // Автообновление каждые 5 секунд
        setTimeout(() => {
            if (!document.hidden) {
                location.reload();
            }
        }, 5000);
        
        // Показываем время обновления
        document.addEventListener('DOMContentLoaded', function() {
            const now = new Date();
            console.log('Страница загружена в ' + now.toLocaleTimeString());
        });
    </script>
</body>
</html>
    """
    
    return render_template_string(html_template, 
                                status=status, 
                                temp=temp,
                                temp_str=temp_str,
                                press=press,
                                press_str=press_str,
                                pm25=pm25,
                                pm25_str=pm25_str,
                                pm10=pm10,
                                pm10_str=pm10_str,
                                cpu_temp=cpu_temp,  # ← Передаем температуру CPU
                                cpu_temp_str=cpu_temp_str,  # ← Передаем форматированную температуру
                                time_str=time_str,
                                ago_str=ago_str,
                                quality=quality,
                                error=error)


@app.route('/api/json')
def api_json():
    """API для JSON данных"""
    data = get_air_data()
    return jsonify(data)


@app.route('/health')
def health():
    """Health check"""
    air_data = get_air_data()
    
    # Проверяем свежесть данных (не старше 30 секунд)
    timestamp = air_data.get('timestamp', 0)
    is_fresh = (time.time() - timestamp) < 30 if timestamp else False
    
    status = 'healthy' if air_data.get('status') == 'ok' and is_fresh else 'unhealthy'
    
    return jsonify({
        'status': status,
        'service': 'air_sensor_web',
        'timestamp': timestamp,
        'cpu_temp':air_data.get('cpu_temp', 'unknown'),
        'data_age': time.time() - timestamp if timestamp else None,
        'data_status': air_data.get('status', 'unknown')
        
    })


# Страница с информацией о качестве воздуха
@app.route('/about')
def about():
    """Страница с информацией о качестве воздуха"""
    html_template = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>О качестве воздуха</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        h1 { color: #333; margin-bottom: 20px; }
        .back-link { 
            display: inline-block; 
            margin-bottom: 20px; 
            color: #667eea; 
            text-decoration: none;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th { background: #f8f9fa; }
        .good { background: #d4edda; }
        .moderate { background: #fff3cd; }
        .poor { background: #f8d7da; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Назад к дашборду</a>
        <h1>📊 Шкала качества воздуха (по PM2.5)</h1>
        
        <table>
            <thead>
                <tr>
                    <th>Категория</th>
                    <th>PM2.5 (μg/m³)</th>
                    <th>Рекомендации</th>
                </tr>
            </thead>
            <tbody>
                <tr class="good">
                    <td><strong>😊 Отличный</strong></td>
                    <td>0 - 15</td>
                    <td>Идеальные условия, можно активно проводить время на улице</td>
                </tr>
                <tr class="good">
                    <td><strong>🙂 Хороший</strong></td>
                    <td>15.1 - 30</td>
                    <td>Воздух чистый, безопасно для большинства людей</td>
                </tr>
                <tr class="moderate">
                    <td><strong>😐 Умеренный</strong></td>
                    <td>30.1 - 55</td>
                    <td>Чувствительным группам рекомендуется ограничить активность на улице</td>
                </tr>
                <tr class="poor">
                    <td><strong>😷 Плохой</strong></td>
                    <td>55.1 - 110</td>
                    <td>Всем рекомендуется ограничить пребывание на улице, носить маску</td>
                </tr>
                <tr class="poor">
                    <td><strong>🤢 Очень плохой</strong></td>
                    <td>> 110</td>
                    <td>Опасно для здоровья, избегайте пребывания на улице</td>
                </tr>
            </tbody>
        </table>
        
        <h2>Что такое PM2.5 и PM10?</h2>
        <p><strong>PM2.5</strong> - частицы диаметром менее 2.5 микрон. Могут проникать глубоко в легкие и кровь.</p>
        <p><strong>PM10</strong> - частицы диаметром менее 10 микрон. Могут оседать в верхних дыхательных путях.</p>
        
        <h2>Источники загрязнения:</h2>
        <ul>
            <li>Транспорт (выхлопные газы)</li>
            <li>Промышленные предприятия</li>
            <li>Строительные работы</li>
            <li>Природные источники (пыль, пыльца)</li>
        </ul>
    </div>
</body>
</html>
    """
    return render_template_string(html_template)