import time

def update_sensor_data(shared_dict, lock, data: dict):
    """Обновляет данные одного сенсора"""
    with lock:
        current_dict = dict(shared_dict['Sensor data'])
        current_dict.update(data)                      
        shared_dict['Sensor data'] = current_dict     

def update_service_status(shared_dict, lock, process_name: str, message: str):
    """Обновляет служебное сообщение"""
    with lock:
        current_dict = dict(shared_dict['Service data'])
        current_dict.update({
            process_name:{
                'message':message,
                'timestamp':time.time()
            }
        })                      
        shared_dict['Service data'] = current_dict     