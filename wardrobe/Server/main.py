import paho.mqtt.client as mqtt
import json
from datetime import datetime
from collections import deque
import numpy as np
import os
from dotenv import load_dotenv
import time
import requests

load_dotenv()

BASE_TOPIC = os.getenv("BASE_TOPIC")
BROKER = "broker.emqx.io"
PORT = 6543

TOPIC = BASE_TOPIC + "/#"

API_URL = f"http://localhost:{PORT}/api/temperature"

client = mqtt.Client()

last_post_time = 0
POST_INTERVAL_SECONDS = 5


def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker."""
    if rc == 0:
        print("Successfully connected to MQTT broker")
        client.subscribe(TOPIC)
        print(f"Subscribed to {TOPIC}")
    else:
        print(f"Failed to connect with result code {rc}")

def on_message(client, userdata, msg):
    """Callback for when a message is received."""
    global last_post_time
    try:
        # Parse JSON message
        payload = json.loads(msg.payload.decode())

        if msg.topic == BASE_TOPIC + "/readings":
            temperature = payload.get("temp")
            device_id = payload.get("device_id", "unknown_device")
            # pressure = payload.get("pressure")
            if temperature is not None:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if time.time() - last_post_time >= 5:
                    data = {
                        "temp": temperature,
                        "unit": "°F",
                        "timestamp": current_time,
                        "device_id": device_id
                    }
                    response = requests.post(API_URL, json=data)

                    if response.status_code == 200:
                        print(f"Temp. data sent successfully: {data}")
                    else:
                        print(f"Failed to send data: {response.status_code} - {response.text}")

                    last_post_time = time.time()

    except json.JSONDecodeError:
        print(f"\nReceived non-JSON message on {msg.topic}: {msg.payload.decode()}")
            
    except json.JSONDecodeError:
        print(f"\nReceived non-JSON message on {msg.topic}:")
        print(f"Payload: {msg.payload.decode()}")



def main():
    # Create MQTT client
    print("Creating MQTT client...")
    client.on_connect = on_connect

    # Set the callback functions onConnect and onMessage
    print("Setting callback functions...")
    client.on_message = on_message
    
    try:
        # Connect to broker
        print("Connecting to broker...")
        client.connect(BROKER, 1883, 60)
        
        # Start the MQTT loop
        print("Starting MQTT loop...")
        client.loop_forever()

        print()
        
    except KeyboardInterrupt:
        print("\nDisconnecting from broker...")
        # make sure to stop the loop and disconnect from the broker
        client.disconnect()
        print("Exited successfully")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()