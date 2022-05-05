import RPi.GPIO as GPIO
from subprocess import call
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN)
time.sleep(10)

while True:
    time.sleep(0.5)
    input = GPIO.input(4)
    if input == 0:
        call("sudo shutdown -h now", shell= True)
    
    