import time
import Adafruit_DHT
import RPi.GPIO as GPIO
import serial
import os, uuid
from azure.storage.queue import QueueClient

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
DHT_SENSOR = Adafruit_DHT.DHT22  # Assuming DHT22; use DHT11 if applicable
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

def read_gps():
    # Parse GPS data to extract coordinates
    gps_serial.flushInput()
    if gps_serial.inWaiting() > 0:
        gps_data = gps_serial.readline().decode('ascii', errors='replace')
        if gps_data.startswith("$GPGGA"):
            gps_parts = gps_data.split(',')
            try:
                lat = float(gps_parts[2]) / 100  # Parse latitude
                lon = float(gps_parts[4]) / 100  # Parse longitude
                alt = float(gps_parts[9])        # Parse altitude
                return lat, lon, alt
            except (ValueError, IndexError):
                return None
    return None

def read_dht():
    # Read temperature and humidity from DHT sensor
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None:
        return temperature, humidity
    else:
        return None, None

def read_flame_sensor():
    # Read binary value from flame sensor
    return GPIO.input(FLAME_SENSOR_PIN)

def read_shock_sensor():
    # Read binary value from shock sensor
    return GPIO.input(SHOCK_SENSOR_PIN)

def read_alcohol_sensor():
    # Read binary value from MQ-3 Alcohol sensor
    return GPIO.input(ALCOHOL_SENSOR_PIN)

def read_button_sensor():
    # Read binary value from button sensor
    return GPIO.input(BUTTON_SENSOR_PIN)

def put_data_in_queue(data:list):
    # Function to put data in a queue
    try:
        queue_service_client.send_message(''.join(data))
        print("Data added to the queue")
    except Exception as e:
        print("Failed to add data to the queue")
        print(e)



if __name__ == "__main__":
    try:
        while True:
            # GPS data
            gps_data = read_gps()
            if gps_data:
                lat, lon, alt = gps_data
                print(f"GPS - Latitude: {lat}, Longitude: {lon}, Altitude: {alt}m")
            else:
                print("GPS - No data")

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

            # Delay between readings
            put_data_in_queue([[lat, lon, alt], [temp, hum], flame_detected, shock_detected, alcohol_detected, button_pressed])
            time.sleep(1)  # Adjust delay as needed

    except KeyboardInterrupt:
        print("Program stopped by user")

    finally:
        # Clean up GPIO settings
        GPIO.cleanup()

