import RPi.GPIO as GPIO
import time

#11 = relay
#23 = screen
#24 = fan
GPIO.setmode(GPIO.BCM)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.output(11, GPIO.HIGH)
GPIO.output(23, GPIO.HIGH)

