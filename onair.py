#!/usr/bin/env python3

from gpiozero import LED
from time import sleep
from http.server import HTTPServer, BaseHTTPRequestHandler
import json 
import paho.mqtt.client as mqtt

led = LED(17)
led.off()

class MyHandlerForHTTP(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/on":
            led.on()
            self.send_response(200)
            self.end_headers()
            mqttc.publish("onair/event", payload="on")
        elif self.path == "/off":
            led.off()
            self.send_response(200)
            self.end_headers()
            mqttc.publish("onair/event", payload="off")
        elif self.path == "/toggle":
            led.toggle()
            self.send_response(200)
            self.end_headers()
        elif self.path == "/status":
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            json_str = json.dumps({ "led" : led.is_lit })
            self.wfile.write(json_str.encode(encoding='utf_8'))
        #self.send_response(200)
        #self.send_header('Content-Type', 'text/plain')
        #self.wfile.write(bytes('Hello World\n', 'UTF-8'))
        #self.wfile.write(bytes('You have requested '+self.path+'\n', 'UTF-8'))

server_address = ('', 8000)

mqttc = mqtt.Client()
mqttc.connect("10.0.0.66")
mqttc.publish("onair/daemon", payload="start")

print("About to create server")
httpd = HTTPServer(server_address, MyHandlerForHTTP)
print("About to serve forever")
httpd.serve_forever()
