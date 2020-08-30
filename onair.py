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
import R64.GPIO as GPIO
import paho.mqtt.client as mqtt
import time

MQTT_ROOT = "onair"
MQTT_STATE = "{}/state".format(MQTT_ROOT)
MQTT_COMMAND = "{}/state/set".format(MQTT_ROOT)
MQTT_AVAILABLE = "{}/state/available".format(MQTT_ROOT)

MQTT_ON = "ON"
MQTT_OFF = "OFF"
MQTT_TOGGLE = "TOGGLE"

# The RockPro version of the library seems to return strings not ints - is this
# intended behavior?
HIGH = "1"
LOW = "0"

#LED_PIN = 27
#BUTTON_PIN = 4
LED_PIN = 16
BUTTON_PIN = 13

GPIO.setmode(GPIO.BOARD)
GPIO.setrock('ROCKPRO64')
GPIO.setwarnings(False);

GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)
led_state = False

time.sleep(1)

GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

class MyHandlerForHTTP(BaseHTTPRequestHandler):
    """
    Handler for HTTP messages
    """
    def do_GET(self):
        global led_state
        # pylint: disable=invalid-name
        """
        Called when a GET request is made
        """
        if self.path == "/on":
            GPIO.output(LED_PIN, GPIO.HIGH)
            led_state = True
            self.send_response(200)
            self.end_headers()
            mqttc.publish(MQTT_STATE, payload=MQTT_ON, retain=True)
        elif self.path == "/off":
            GPIO.output(LED_PIN, GPIO.LOW)
            led_state = False
            self.send_response(200)
            self.end_headers()
            mqttc.publish(MQTT_STATE, payload=MQTT_OFF, retain=True)
        elif self.path == "/toggle":
            if led_state:
                GPIO.output(LED_PIN, GPIO.LOW)
                led_state = False
            else:
                GPIO.output(LED_PIN, GPIO.HIGH)
                led_state = True
            self.send_response(200)
            self.end_headers()
            mqttc.publish(MQTT_STATE, payload=(MQTT_ON if led_state else MQTT_OFF), retain=True)
        elif self.path == "/status":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            json_str = json.dumps({"led": led_state})
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
        global led_state
        """
        Infinite loop waiting on button presses
        """
        print("Starting button thread")
        while True:
            while GPIO.input(BUTTON_PIN) == HIGH:
                time.sleep(0.01)  # wait 10 ms to give CPU chance to do other things
            print("Button Pressed")
            if led_state:
                GPIO.output(LED_PIN, GPIO.LOW)
                led_state = False
            else:
                GPIO.output(LED_PIN, GPIO.HIGH)
                led_state = True
            mqttc.publish(MQTT_STATE, payload=(MQTT_ON if led_state else MQTT_OFF), retain=True)
            while GPIO.input(BUTTON_PIN) == LOW:
                time.sleep(0.01)  # wait 10 ms to give CPU chance to do other things
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
    global led_state
    # pylint: disable=unused-argument
    print("MQTT Command Received")
    print("MQTT Command:" +msg.topic+" "+msg.payload.decode())
    if msg.payload.decode() == MQTT_ON:
        GPIO.output(LED_PIN, GPIO.HIGH)
        led_state = True
        mqttc.publish(MQTT_STATE, payload=MQTT_ON, retain=True)
    elif msg.payload.decode() == MQTT_OFF:
        GPIO.output(LED_PIN, GPIO.LOW)
        led_state = False
        mqttc.publish(MQTT_STATE, payload=MQTT_OFF, retain=True)
    elif msg.payload.decode() == MQTT_TOGGLE:
        if led_state:
            GPIO.output(LED_PIN, GPIO.LOW)
            led_state = False
        else:
            GPIO.output(LED_PIN, GPIO.HIGH)
            led_state = True
        mqttc.publish(MQTT_STATE, payload=(MQTT_ON if led_state else MQTT_OFF), retain=True)

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
