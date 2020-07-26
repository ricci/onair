#!/usr/bin/env python3

from gpiozero import LED
from time import sleep
from http.server import HTTPServer, BaseHTTPRequestHandler
import json 
import paho.mqtt.client as mqtt
import threading
import atexit

MQTT_ROOT = "onair"
MQTT_STATE = "{}/state".format(MQTT_ROOT)
MQTT_COMMAND = "{}/state/set".format(MQTT_ROOT)
MQTT_AVAILABLE = "{}/state/available".format(MQTT_ROOT)

MQTT_ON = "ON"
MQTT_OFF = "OFF"

led = LED(17)
led.off()


class MyHandlerForHTTP(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/on":
            led.on()
            self.send_response(200)
            self.end_headers()
            mqttc.publish(MQTT_STATE, payload=MQTT_ON)
        elif self.path == "/off":
            led.off()
            self.send_response(200)
            self.end_headers()
            mqttc.publish(MQTT_STATE, payload=MQTT_OFF)
        elif self.path == "/toggle":
            led.toggle()
            self.send_response(200)
            self.end_headers()
            mqttc.publish(MQTT_STATE, payload=(MQTT_ON if led.is_lit else MQTT_OFF))
        elif self.path == "/status":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            json_str = json.dumps({ "led" : led.is_lit })
            self.wfile.write(json_str.encode(encoding='utf_8'))

class HTTPThread (threading.Thread):
   def run(self):
      print ("Starting http thread")
      httpd.serve_forever()
      print ("Exiting http thread")

class MQTTThread (threading.Thread):
   def run(self):
      print ("Starting mqtt thread")
      mqttc.loop_forever()
      print ("Exiting mqtt thread")


server_address = ('', 8000)

mqttc = mqtt.Client()

def mqtt_on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with result code "+str(rc))
    client.subscribe(MQTT_COMMAND)
    print("Subscribed to " + MQTT_COMMAND)
    client.publish(MQTT_AVAILABLE, payload=MQTT_ON)
    print("Published availability messages")

def mqtt_on_message(client, userdata, msg):
    print("MQTT Command Received")
    print("MQTT Command:" +msg.topic+" "+msg.payload.decode())
    if msg.payload.decode() == MQTT_ON:
        led.on()
        mqttc.publish(MQTT_STATE, payload=MQTT_ON)
    elif msg.payload.decode() == MQTT_OFF:
        led.off()
        mqttc.publish(MQTT_STATE, payload=MQTT_OFF)

mqttc.on_connect = mqtt_on_connect
mqttc.on_message = mqtt_on_message
mqttc.connect("10.0.0.66")

@atexit.register
def mqttSignoff():
    mqttc.publish(MQTT_AVAILABLE, payload=MQTT_OFF)

print("About to create server")
httpd = HTTPServer(server_address, MyHandlerForHTTP)
print("About to serve forever")
httpThread = HTTPThread()
httpThread.start()

mqttThread = MQTTThread()
mqttThread.start()

mqttThread.join()
httpThread.join()
