#!/usr/bin/env python3

import pulsectl
import paho.mqtt.client as mqtt

MQTT_ROOT = "onair"
MQTT_STATE = "{}/state".format(MQTT_ROOT)
MQTT_COMMAND = "{}/state/set".format(MQTT_ROOT)
MQTT_AVAILABLE = "{}/state/available".format(MQTT_ROOT)

MQTT_ON = "ON"
MQTT_OFF = "OFF"

pulse = pulsectl.Pulse('onair-client')
mqttc = mqtt.Client()

def mic_on():
    global pulse
    for e in pulse.source_output_list():
        # Not sure what this is, but it seems to always be there, so it doesn't
        # count
        if e.name != "parec":
            return True
    return False

currentState = None

# This lets us treat the event listening loop as a simple blocking call - we aren't
# allowed to do the listing calls from the callback
def handle_pa_event(ev):
    raise pulsectl.PulseLoopStop

pulse.event_mask_set('source_output')
pulse.event_callback_set(handle_pa_event)
while True:
    listening = mic_on()
    if currentState is None or currentState != listening:
        if listening:
            print("Now listening")
            mqttc.connect("10.0.0.66")
            mqttc.publish(MQTT_COMMAND, payload=MQTT_ON)
            mqttc.disconnect()
        else:
            print("No longer listening")
            mqttc.connect("10.0.0.66")
            mqttc.publish(MQTT_COMMAND, payload=MQTT_OFF)
            mqttc.disconnect()
    currentState = listening
    pulse.event_listen()
