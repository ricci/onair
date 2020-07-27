#!/usr/bin/env python3

"""
onair - simple daemon to interface with onair sign

Accepts inputs via http, mqtt, and button presses. Sends updates out via
mqtt
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import atexit
import threading
from gpiozero import LED, Button
import paho.mqtt.client as mqtt

MQTT_ROOT = "onair"
MQTT_STATE = "{}/state".format(MQTT_ROOT)
MQTT_COMMAND = "{}/state/set".format(MQTT_ROOT)
MQTT_AVAILABLE = "{}/state/available".format(MQTT_ROOT)

MQTT_ON = "ON"
MQTT_OFF = "OFF"

led = LED(17)
led.off()

button = Button(4)#,bounce_time=0.1)

class MyHandlerForHTTP(BaseHTTPRequestHandler):
    """
    Handler for HTTP messages
    """
    def do_GET(self):
        # pylint: disable=invalid-name
        """
        Called when a GET request is made
        """
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
            json_str = json.dumps({"led": led.is_lit})
            self.wfile.write(json_str.encode(encoding='utf_8'))

class HTTPThread(threading.Thread):
    """
    Thread that manages HTTP connections
    """
    def run(self):
        """
        Run the http serve funtion, never exit
        """
        print("Starting http thread")
        httpd.serve_forever()
        print("Exiting http thread")

class MQTTThread(threading.Thread):
    """
    Thread that proccesses commands from MQTT
    """
    def run(self):
        """
        Run the mqtt event loop, never exit
        """
        print("Starting mqtt thread")
        mqttc.loop_forever()
        print("Exiting mqtt thread")

class ButtonThread(threading.Thread):
    """
    Thread that handles button presses
    """
    def run(self):
        """
        Infinite loop waiting on button presses
        """
        print("Starting button thread")
        while True:
            button.wait_for_press()
            print("Button Pressed")
            led.toggle()
            mqttc.publish(MQTT_STATE, payload=(MQTT_ON if led.is_lit else MQTT_OFF))
            button.wait_for_release()
            print("Button Released")
        print("Exiting button thread")

server_address = ('', 8000)

mqttc = mqtt.Client()

def mqtt_on_connect(client, userdata, flags, rc):
    """
    We subscribe in a callback so that if we disconnect and reconnect,
    re-subscriptions happen properly.
    """
    # pylint: disable=unused-argument, invalid-name
    print("Connected to MQTT with result code "+str(rc))
    client.subscribe(MQTT_COMMAND)
    print("Subscribed to " + MQTT_COMMAND)
    client.publish(MQTT_AVAILABLE, payload=MQTT_ON)
    print("Published availability messages")

def mqtt_on_message(client, userdata, msg):
    """
    Handle commands coming in through MQTT
    """
    # pylint: disable=unused-argument
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
def mqtt_signoff():
    """
    When this process dies, let home-assistant know that we're not available
    anymore.
    """
    mqttc.publish(MQTT_AVAILABLE, payload=MQTT_OFF)

print("About to create server")
httpd = HTTPServer(server_address, MyHandlerForHTTP)
print("About to serve forever")
httpThread = HTTPThread()
httpThread.start()

mqttThread = MQTTThread()
mqttThread.start()

buttonThread = ButtonThread()
buttonThread.start()

mqttThread.join()
httpThread.join()
buttonThread.join()
