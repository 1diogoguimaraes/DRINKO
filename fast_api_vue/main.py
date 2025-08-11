from fastapi import FastAPI, Depends,WebSocket,WebSocketDisconnect
from fastapi_mqtt import FastMQTT, MQTTConfig
import asyncio
from typing import Any
import json


# Configure MQTT settings
mqtt_config = MQTTConfig(
    host="192.168.0.100",  # Replace with your broker address
    port=1883,                       # Default MQTT port
    keepalive=60,                    # Keep alive time in seconds
    username="userdio",        # Optional username
    password="legomosquitto8109",        # Optional password
    client_id="fastapi_client",      # Unique client ID
    # Add other configurations like ssl, will, etc. as needed
)

# Initialize FastAPI app
app = FastAPI()
fast_mqtt = FastMQTT(config=mqtt_config)
fast_mqtt.init_app(app)

# WebSocket Client
clients = []

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Optional: Keep connection alive
    except WebSocketDisconnect:
        clients.remove(websocket)


# Define MQTT topics and corresponding handler functions
@fast_mqtt.on_connect()
def connect(client, flags, rc, properties: Any):
    """
    Callback function for when the client connects to the MQTT broker.
    """
    print("Connected: ", client, flags, rc, properties)
    # Subscribe to topics here if needed
    fast_mqtt.client.subscribe("esp32/test") # Replace with your topic
    fast_mqtt.client.subscribe("esp32/+/status"); 

@fast_mqtt.on_disconnect()
def disconnect(client, packet, exc=None):
    """
    Callback function for when the client disconnects from the MQTT broker.
    """
    print("Disconnected")

@fast_mqtt.on_subscribe()
def subscribe(client, mid, qos, properties: Any):
    """
    Callback function for when the client subscribes to a topic.
    """
    print("Subscribed", client, mid, qos, properties)

@fast_mqtt.on_message()
async def message(client, topic, payload, qos, properties: Any):
    message_text = payload.decode()
    print(f"Topic: {topic} | Payload: {message_text}")

    try:
        data = json.loads(message_text)  # Parse JSON

    except json.JSONDecodeError:
        print("Failed to decode JSON payload.")

    # Split topic to extract device ID
    parts = topic.split("/")
    if len(parts) == 3 and parts[2] == "status":
        device_id = parts[1]  # Get the device ID (e.g., 'device1')
        state = data.get("state")        # Get the "state" field
        mode=data.get("mode")
        team=data.get("team")
        relay_pos=data.get("relay_pos")
        print(f"State: {state}")
        print(device_id)
        print(state)
        await handle_device_status(device_id, state,mode,team,relay_pos)
    elif len(parts) == 3 and parts[2] == "results":
        device_id = parts[1]
        start_weight = data.get("start_weight")        # Get the "state" field
        drink_time=data.get("drink_time")
        end_weight=data.get("end_weight")
        handle_device_results(device_id,start_weight,drink_time,end_weight)
    else:
        print("Unrecognized topic structure.")

    """
    Callback function for when a message is received on a subscribed topic.
    """
    print("Received message:", topic, payload.decode(), qos, properties)
    # Process the received message here
    # Example: Save to database, trigger an event, etc.

async def handle_device_status(device_id: str, status: str,mode:str,team:str,relay_pos:int):
    print(f"Received status from {device_id}: {status},{mode},{team},{relay_pos}")
    
    # Example: Forward to frontend if live
    for ws in clients:
        await ws.send_text(json.dumps({
            "type": "status",
            "device_id": device_id,
            "status": status,
            "mode": mode,
            "team": team,
            "relay_pos": relay_pos
        }))


async def handle_device_results(device_id:str,start_weight:float,drink_time:float,end_weight:float):
    print(f"Received results from {device_id}: {start_weight},{drink_time},{end_weight}")
    for ws in clients:
        await ws.send_text(json.dumps({
            "type": "result",
            "device_id": device_id,
            "start_weight": start_weight,
            "drink_time": drink_time,
            "end_weight": end_weight

        }))



# FastAPI endpoint for publishing messages
@app.get("/publish/{message}")
async def publish_message(message: str):
    """
    Endpoint to publish a message to a specified MQTT topic.
    """
    fast_mqtt.publish("esp32/3/status", message) # Replace with your topic
    return {"result": True, "message": "Published"}

# FastAPI endpoint to subscribe to a topic
@app.get("/subscribe/{topic}")
async def subscribe_to_topic(topic: str):
  """
  Endpoint to subscribe to a topic dynamically.
  """
  fast_mqtt.subscribe(topic)
  return {"result": True, "message": f"Subscribed to {topic}"}

# Example usage:  Starting the MQTT client in a background task
async def run_mqtt():
    await fast_mqtt.start()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_mqtt())

@app.on_event("shutdown")
async def shutdown_event():
    await fast_mqtt.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)