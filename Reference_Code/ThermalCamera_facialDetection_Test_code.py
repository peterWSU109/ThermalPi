# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import cv2
import time
import board
import busio
import adafruit_mlx90640


i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

frame = [0] * 768

for i in range(2):
    try:
        mlx.getFrame(frame)
    except ValueError:
        continue


p = cv2.imread('image0.jpg')

face_cascade = cv2.CascadeClassifier('opencv_haarcascade_frontalface_alt.xml')
eye_cascade = cv2.CascadeClassifier('opencv_haarcascade_eye.xml')

gray_p = cv2.cvtColor(p, cv2.COLOR_BGR2GRAY)

faces = face_cascade.detectMultiScale(gray_p, 1.1, 4)
eyes = eye_cascade.detectMultiScale(gray_p, 1.1, 4)

for(a, b, c, d) in faces:
    for(x, y, w, h) in eyes:
        if(a < x and b < y and a+c > x+w and b+d > y+h):
            print('face found')
            cv2.rectangle(p, (a,b), (a+c, b+d), (255,0,0),2)
            cv2.rectangle(p, (x,y), (x+w, y+h), (0,255,0),2)

img = cv2.imread('image0.jpg', cv2.IMREAD_COLOR)
b, g, r = cv2.split(img)

dimensions = r.shape
print(dimensions)

        
for h in range(24):
    for w in range(32):
        if frame[h * 32 + w] < 26:
            r[32*h:32+32*h,40*w:40+40*w] = (0)
        if 30 < frame[h * 32 + w] < 32:
            r[32*h:32+32*h,40*w:40+40*w] = (50)
        if 32 < frame[h * 32 + w] < 34:
            r[32*h:32+32*h,40*w:40+40*w] = (100)
        if 34 < frame[h * 32 + w] < 40:
            r[32*h:32+32*h,40*w:40+40*w] = (150)
        if 36 < frame[h * 32 + w] < 300:
            r[32*h:32+32*h,40*w:40+40*w] = (255)

            
            
p = cv2.merge([b,g,r])      
        

cv2.imshow('p', p)
cv2.waitKey()
