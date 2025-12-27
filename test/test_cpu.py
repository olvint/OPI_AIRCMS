import os

temp_path = '/sys/class/thermal/thermal_zone0/temp'


if os.path.exists(temp_path):
    with open(temp_path, 'r') as f:
        temp_millic = int(f.read().strip())
        temp_c = temp_millic / 1000.0
        
print (temp_c)