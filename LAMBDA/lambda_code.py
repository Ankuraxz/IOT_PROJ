import os
import uuid
from azure.storage.queue import QueueClient
from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
import azure.functions as func
app = func.FunctionApp()



#QUEUE
queue_service_url = "https://sensorstoragequeue.queue.core.windows.net/sensor-data-queue"
storage_account_name = "sensorstoragequeue"
queue_connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

try:
    queue_service_client = QueueClient.from_connection_string(queue_connection_string, "sensor-data-queue")
    print("Successfully connected to the Azure Storage Queue")
except Exception as e:
    print("Failed to connect to the Azure Storage Queue")
    print(e)

#COSMOS
cosmos_uri = "https://iot-sensor-data.documents.azure.com:443/"
cosmos_connection_string = os.getenv('COSMOS_DB_CONNECTION_STRING')

try:
    cosmos_client = CosmosClient.from_connection_string(cosmos_connection_string)
    database = cosmos_client.get_database_client('iotsensorbackup')
    container = database.get_container_client('sensordata')
    print("Successfully connected to the Azure Cosmos DB")
except Exception as e:
    print("Failed to connect to the Azure Cosmos DB")
    print(e)



# def read_and_delete_messages() -> str:
#     messages = queue_service_client.receive_messages(max_messages=1)
#     for message in messages:
#         print("Message: " + message.content)
#         queue_service_client.delete_message(message)
#         return message.content

def notify_with_novu(message:str):
    pass

def prepare_document_for_cosmos_db(data:str):
    #sample data - [(lat, lon, alt), (temp, hum), flame_detected, shock_detected, alcohol_detected, button_pressed]
    data_list = data.split(',')
    document = {
        "id": str(uuid.uuid4()),
        "location": {
            "type": "Point",
            "coordinates": [float(data_list[0][0]), float(data_list[0][1]), float(data_list[0][2])]
        },
        "temperature": float(data_list[1][0]),
        "humidity": float(data_list[1][1]),
        "flame_detected": bool(data_list[2]),
        "shock_detected": bool(data_list[3]),
        "alcohol_detected": bool(data_list[4]),
        "button_pressed": bool(data_list[5])
    }

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

    return document

# def send_data_to_cosmos_db(document:dict):
#     try:
#         container.upsert_item(document)
#         print("Data added to the Cosmos DB")
#     except Exception as e:
#         print("Failed to add data to the Cosmos DB")
#         print(e)


@app.function_name(name="QueueFunc")
@app.queue_trigger(arg_name="msg", queue_name=storage_account_name, connection=queue_connection_string)
@app.cosmos_db_output(arg_name="documents", 
                    database_name="iotsensorbackup",
                    collection_name="sensordata",
                    create_if_not_exists=True,
                    connection_string_setting=cosmos_connection_string)
def main(msg: func.QueueMessage, outputDocument: func.Out[func.Document])->None:
    msg = msg.get_body().decode('utf-8')
    print(f"Message: {msg}")
    document = prepare_document_for_cosmos_db(msg)
    outputDocument.set(func.Document.from_json(document))




    
