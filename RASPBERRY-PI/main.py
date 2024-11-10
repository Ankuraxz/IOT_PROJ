import time
import RPi.GPIO as GPIO
import serial
import os, uuid
from azure.storage.queue import QueueClient
import smbus2

'''
Connect VCC on the MPU-9250 to the 3.3V pin on the Raspberry Pi.
Connect GND on the MPU-9250 to a GND pin on the Raspberry Pi.
Connect SCL on the MPU-9250 to SCL (I2C1 SCL, GPIO 3) on the Raspberry Pi.
Connect SDA on the MPU-9250 to SDA (I2C1 SDA, GPIO 2) on the Raspberry Pi.
'''

# Initialize the serial port for GPS (assuming Neo-6 GPS is connected via serial)
gps_port = "/dev/ttyAMA0"  # Adjust as needed for your setup
gps_serial = serial.Serial(gps_port, baudrate=9600, timeout=1)

queue_service_url = "https://sensorstoragequeue.queue.core.windows.net/sensor-data-queue"
storage_account_name = "sensorstoragequeue"
queue_connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

try:
    queue_service_client = QueueClient.from_connection_string(queue_connection_string, "sensor-data-queue")
    print("Successfully connected to the Azure Storage Queue")
except Exception as e:
    print("Failed to connect to the Azure Storage Queue")
    print(e)

# DHT sensor setup
# DHT_SENSOR = Adafruit_DHT.DHT11  # Assuming DHT22; use DHT11 if applicable
DHT_PIN = 4                      # GPIO pin for DHT sensor data

# GPIO setup for other sensors
FLAME_SENSOR_PIN = 17      # GPIO pin for Flame sensor
SHOCK_SENSOR_PIN = 27      # GPIO pin for Shock sensor
ALCOHOL_SENSOR_PIN = 22    # GPIO pin for MQ-3 Alcohol sensor
BUTTON_SENSOR_PIN = 23     # GPIO pin for button sensor

# Setup GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(FLAME_SENSOR_PIN, GPIO.IN)
GPIO.setup(SHOCK_SENSOR_PIN, GPIO.IN)
GPIO.setup(ALCOHOL_SENSOR_PIN, GPIO.IN)
GPIO.setup(BUTTON_SENSOR_PIN, GPIO.IN)

# MPU-9250 I2C setup
MPU9250_ADDR = 0x68
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43
PWR_MGMT_1 = 0x6B
bus = smbus2.SMBus(1)

def init_mpu9250():
    # Wake up the MPU-9250
    bus.write_byte_data(MPU9250_ADDR, PWR_MGMT_1, 0)

def read_raw_data(addr):
    # Read two bytes of data (16 bits)
    high = bus.read_byte_data(MPU9250_ADDR, addr)
    low = bus.read_byte_data(MPU9250_ADDR, addr + 1)
    value = (high << 8) | low
    if value > 32768:
        value = value - 65536
    return value

def read_mpu9250():
    # Read accelerometer and gyroscope values
    acc_x = read_raw_data(ACCEL_XOUT_H) / 16384.0
    acc_y = read_raw_data(ACCEL_XOUT_H + 2) / 16384.0
    acc_z = read_raw_data(ACCEL_XOUT_H + 4) / 16384.0
    gyro_x = read_raw_data(GYRO_XOUT_H) / 131.0
    gyro_y = read_raw_data(GYRO_XOUT_H + 2) / 131.0
    gyro_z = read_raw_data(GYRO_XOUT_H + 4) / 131.0
    return acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z

# def read_gps():
#     gps_serial.flushInput()
#     if gps_serial.inWaiting() > 0:
#         gps_data = gps_serial.readline().decode('ascii', errors='replace')
#         if gps_data.startswith("$GPGGA"):
#             gps_parts = gps_data.split(',')
#             try:
#                 lat = float(gps_parts[2]) / 100
#                 lon = float(gps_parts[4]) / 100
#                 alt = float(gps_parts[9])
#                 return lat, lon, alt
#             except (ValueError, IndexError):
#                 return None
#     return None

def read_dht():
    # humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    # if humidity is not None and temperature is not None:
    #     return temperature, humidity
    # else:
    #     return None, None
    return 25.0, 50.0  # Dummy data for testing

def read_flame_sensor():
    return GPIO.input(FLAME_SENSOR_PIN)

def read_shock_sensor():
    return GPIO.input(SHOCK_SENSOR_PIN)

def read_alcohol_sensor():
    return GPIO.input(ALCOHOL_SENSOR_PIN)

def read_button_sensor():
    return GPIO.input(BUTTON_SENSOR_PIN)

def put_data_in_queue(data:list):
    try:
        queue_service_client.send_message(''.join(data))
        print("Data added to the queue")
    except Exception as e:
        print("Failed to add data to the queue")
        print(e)

# Initialize MPU-9250
init_mpu9250()

if __name__ == "__main__":
    try:
        while True:
            # GPS data
            # gps_data = read_gps()
            # if gps_data:
            #     lat, lon, alt = gps_data
            #     print(f"GPS - Latitude: {lat}, Longitude: {lon}, Altitude: {alt}m")
            # else:
            #     print("GPS - No data")
            lat, lon, alt = 28.7041, 77.1025, 200

            # DHT sensor data
            temp, hum = read_dht()
            if temp is not None and hum is not None:
                print(f"DHT Sensor - Temperature: {temp:.1f}°C, Humidity: {hum:.1f}%")
            else:
                print("DHT Sensor - Failed to retrieve data")

            # Flame sensor data
            flame_detected = read_flame_sensor()
            print(f"Flame Sensor - Detected: {'Yes' if flame_detected == 1 else 'No'}")

            # Shock sensor data
            shock_detected = read_shock_sensor()
            print(f"Shock Sensor - Detected: {'Yes' if shock_detected == 1 else 'No'}")

            # Alcohol sensor data
            alcohol_detected = read_alcohol_sensor()
            print(f"Alcohol Sensor - Detected: {'Yes' if alcohol_detected == 1 else 'No'}")

            # Button sensor data
            button_pressed = read_button_sensor()
            print(f"Button Sensor - Pressed: {'Yes' if button_pressed == 1 else 'No'}")

            # MPU-9250 data
            acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z = read_mpu9250()
            print(f"MPU-9250 - Accel X: {acc_x:.2f} g, Y: {acc_y:.2f} g, Z: {acc_z:.2f} g")
            print(f"MPU-9250 - Gyro X: {gyro_x:.2f} °/s, Y: {gyro_y:.2f} °/s, Z: {gyro_z:.2f} °/s")

            # Send data to Azure Queue
            put_data_in_queue([[lat, lon, alt], [temp, hum], flame_detected, shock_detected, alcohol_detected, button_pressed, [acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z]])
            
            time.sleep(1)  # Adjust delay as needed

    except KeyboardInterrupt:
        print("Program stopped by user")

    finally:
        GPIO.cleanup()
