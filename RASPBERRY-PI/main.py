import time
import RPi.GPIO as GPIO
import serial
import os, uuid
from azure.cosmos import CosmosClient
import smbus2
import urllib3
import json
import pynmea2

'''
Connect VCC on the MPU-9250 to the 3.3V pin on the Raspberry Pi.
Connect GND on the MPU-9250 to a GND pin on the Raspberry Pi.
Connect SCL on the MPU-9250 to SCL (I2C1 SCL, GPIO 3) on the Raspberry Pi.
Connect SDA on the MPU-9250 to SDA (I2C1 SDA, GPIO 2) on the Raspberry Pi.
'''

# Initialize the serial port for GPS (assuming Neo-6 GPS is connected via serial)
gps_port = "/dev/ttyAMA0"  # Adjust as needed for your setup
gps_serial = serial.Serial(gps_port, baudrate=9600, timeout=1)
dataout = pynmea2.NMEAStreamReader()

# queue_service_url = "https://sensorstoragequeue.queue.core.windows.net/sensor-data-queue"
# storage_account_name = "sensorstoragequeue"
# queue_connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

# try:
#     queue_service_client = QueueClient.from_connection_string(queue_connection_string, "sensor-data-queue")
#     print("Successfully connected to the Azure Storage Queue")
# except Exception as e:
#     print("Failed to connect to the Azure Storage Queue")
#     print(e)

cosmos_connection_string = os.getenv('COSMOS_CONNECTION_STRING')
cosmos_client = CosmosClient.from_connection_string(cosmos_connection_string)
database = cosmos_client.get_database_client('iotsensorbackup')
container = database.get_container_client('sensordata')

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

def read_gps():
    try:
        newdata = gps_serial.readline()
        if newdata[0:6] == b'$GPGGA':
            newmsg = pynmea2.parse(newdata.decode('utf-8'))
            print(f"GPS MESSAGE: {newmsg}")
            # lat = newmsg.latitude
            # lon = newmsg.longitude
            # alt = newmsg.altitude
            # return newmsg.latitude, newmsg.longitude, newmsg.altitude
            return 28.7041, 77.1025, 200
    except Exception as e:
        print("Failed to read GPS data")
    return None

def read_dht():
    return 25, 50  # Placeholder for DHT sensor data


def read_flame_sensor():
    return GPIO.input(FLAME_SENSOR_PIN)

def read_shock_sensor():
    return 1 - GPIO.input(SHOCK_SENSOR_PIN)

def read_alcohol_sensor():
    return GPIO.input(ALCOHOL_SENSOR_PIN)

def read_button_sensor():
    return 1 - GPIO.input(BUTTON_SENSOR_PIN)

def notify_with_novu(message:str):
    try:
        novu_key = os.getenv('NOVU_KEY')

        url = 'https://api.novu.co/v1/events/trigger'
        headers = {
            'Authorization': 'ApiKey ' + novu_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        data = {
            "name": "emailerworkflow",
            "to":{
                "subscriberId": str(uuid.uuid4()),
                "email": "ankurvermaaxz@gmail.com"
            },
            "payload": ({'Message': f"Hi User ! Alert for {message} ",})
        }
        http = urllib3.PoolManager()
        encoded_data = json.dumps(data).encode('utf-8')
        response = http.request('POST', url, headers=headers, body=encoded_data)

        return response
    except Exception as e:
        print("Failed to send notification to Novu")
        pass

def put_data_in_cosmos(data:list):
    try:
        document = {
            "id": str(uuid.uuid4()),
            "location": {
                "type": "Point",
                "coordinates": [float(data[0][0]), float(data[0][1]), float(data[0][2])]
            },
            "temperature": float(data[1][0]),
            "humidity": float(data[1][1]),
            "flame_detected": bool(data[2]),
            "shock_detected": bool(data[3]),
            "alcohol_detected": bool(data[4]),
            "button_pressed": bool(data[5]),
            "accelerometer": {
                "type": "Point",
                "x": float(data[6][0]),
                "y": float(data[6][1]),
                "z": float(data[6][2])
            },
            "gyroscope": {
                "type": "Point",
                "x": float(data[6][3]),
                "y": float(data[6][4]),
                "z": float(data[6][5])
            }
        }

        container.upsert_item(document)
        print("Data added to the Cosmos")

        # Notifications for specific conditions
        if document["flame_detected"]:
            notify_with_novu("Flame detected!")
        elif document["shock_detected"]:
            notify_with_novu("Shock detected!")
        elif document["alcohol_detected"]:
            notify_with_novu("Alcohol detected!")
        elif document["button_pressed"]:
            notify_with_novu("Button pressed!")
        elif document["location"]["coordinates"] == [0, 0, 0]:
            notify_with_novu("No GPS signal!")
        elif document["temperature"] > 40:
            notify_with_novu("High temperature!")
        elif document["humidity"] > 80:
            notify_with_novu("High humidity!")
        elif document["accelerometer"]["x"] > 3 or document["accelerometer"]["y"] > 3 or document["accelerometer"]["z"] > 3:
            notify_with_novu("High acceleration!")
        return document
    except Exception as e:
        print("Failed to add data to the db")
        print(e)

# Initialize MPU-9250
init_mpu9250()

if __name__ == "__main__":
    try:
        while True:
            # GPS data
            lat, lon, alt = read_gps()
            print(f"GPS - Latitude: {lat}, Longitude: {lon}, Altitude: {alt}")

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
            put_data_in_cosmos([[lat, lon, alt], [temp, hum], flame_detected, shock_detected, alcohol_detected, button_pressed, [acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z]])
            
            time.sleep(1)  # Adjust delay as needed

    except KeyboardInterrupt:
        print("Program stopped by user")
    except Exception as e:
        print(e)

    finally:
        GPIO.cleanup()

