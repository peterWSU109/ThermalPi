import cv2
p = cv2.imread('image0.jpg')
num_eyes = 0

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
            
    
cv2.imshow('p', p)
cv2.waitKey()

