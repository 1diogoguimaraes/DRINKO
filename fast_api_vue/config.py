# config.py
from fastapi_mqtt import MQTTConfig

mqtt_config = MQTTConfig(
    host="192.168.0.100",
    port=1883,
    keepalive=60,
    username="userdio",
    password="legomosquitto8109",
    client_id="fastapi_client"
)
