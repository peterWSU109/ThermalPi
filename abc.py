import threading
import numpy
import time
import board
import busio
import adafruit_mlx90640
import cv2


debug = True

h_res = 320 #320,640,1280
v_res = 240 #240,480,720

#Example: 0.30 will shrink the thermal projection onto the camera image by 30%
x_offset_factor = 0.30 
y_offset_factor = 0.30
tc_horz_scale = int((h_res//32)*(1-x_offset_factor))
tc_vert_scale = int((v_res//24)*(1-y_offset_factor))

#moves the entire thermal projection on camera image up or down, by an integer number of thermal pixels
#moving axis without shrinking may cause a segmentation fault
y_axis = tc_vert_scale*5

x_offset = int(h_res*(x_offset_factor/2))
y_offset = int(v_res*(y_offset_factor/2)) - y_axis



#d_scale or distance scale gives a factor for how area changes with increased pixel resolution, 320x240 is default (=1)
d_scale = h_res*v_res//(320*240)
tc_horz_scale = int((h_res//32)*(1-x_offset_factor))
tc_vert_scale = int((v_res//24)*(1-y_offset_factor))

#basic font settings
font = cv2.FONT_HERSHEY_SIMPLEX
color = (0,255,0)
thickness = 1
fontScale = 1

#video capture settings
cap = cv2.VideoCapture(0)
cap.set(3,h_res)
cap.set(4,v_res)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

guy = cv2.imread('guy.jpg')
bckgrd = cv2.imread('800x600background.jpg')
bckgrd2 = cv2.imread('800x600background.jpg')


i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

face_cascade = cv2.CascadeClassifier('opencv_haarcascade_frontalface_alt.xml')


frame = [0] * 768

def thermal_to_image( t_pixel ):
    x, y = t_pixel
    x = (x*tc_horz_scale) + x_offset
    y = (y*tc_vert_scale) + y_offset
    return[x,y]

#if flag is sent as 1 will only return zeros for thermal array values out of range
def image_to_thermal( i_pixel , flag ):
    x, y = i_pixel
    x = (x - x_offset)/tc_horz_scale
    y = (y - y_offset)/tc_vert_scale
    if 0 <= x <= 32 and 0 <= y <=24 and flag == 1:
        x = 0
        y = 0
    return [x,y]

def get_temps( top_left , bottom_right):
    temps = []
    top_left = image_to_thermal(top_left, 0)
    bottom_right = image_to_thermal(bottom_right, 0)
    x, y = top_left
    a, b = bottom_right
    
    x = int(round(x))
    m = int(round(x)) #baseline position of x
    y = int(round(y)) - 1
    a = int(round(a))
    b = int(round(b))
    
    rx = int(a - x)
    ry = int(b - y - 1)
    
    for i in range(0,ry):
        y = y + 1
        x = m
        for j in range(0,rx):
            if 0 <= x < 32 and 0 <= y < 24:
                temps.append(round(frame[x + y*32],1))
            x = x + 1
    print(len(temps))
    return temps
        

def blend_images( x_point, y_point):
    x_point = x_point*3
    y_point = y_point*3
    y = (y_point - 3)
    for i in range(228):
        y = y + 1
        x = x_point 
        for j in range(92):
            a, b, c = guy[i,j]
            x = x+1
            
            m = int(a)
            l = int(b)
            k = int(c)
            if (m + l + k) < 765 and x < 600 and y < 800:
                bckgrd2[x,y] = guy[i,j]

        
    

def refresh_thermalCamera():
    while True:
        try:
            mlx.getFrame(frame)
        except ValueError:
            continue

t_camera = threading.Thread(target = refresh_thermalCamera, daemon = True)
t_camera.start()
    

while True:


    
    ret, fram = cap.read()
    fram = cv2.flip(fram, 180)
    gray_p = cv2.cvtColor(fram, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(gray_p, 1.2, 2)
        
                
                
    b, g, r = cv2.split(fram)


    if debug == True:
        y_offset = y_offset - tc_vert_scale
        for h in range(24):
            x_offset = int(h_res*(x_offset_factor/2))
            y_offset = y_offset + tc_vert_scale
            y_end = y_offset + tc_vert_scale
            for w in range(32):
                x_end = x_offset + tc_horz_scale
                t = frame[h * 32 + w]
                if t < 30:
                    r[y_offset: y_end, x_offset: x_end] = (0)
                elif 30 <= t < 31:
                    r[y_offset: y_end, x_offset: x_end] = (0)
                elif 31 <= t < 32:
                    r[y_offset: y_end, x_offset: x_end] = (0)
                elif 32 <= t < 33:
                    r[y_offset: y_end, x_offset: x_end] = (0)
                elif 33 <= t < 34:
                    r[y_offset: y_end, x_offset: x_end] = (0)
                elif 34 <= t < 35:
                    r[y_offset: y_end, x_offset: x_end] = (255)
                elif 35 <= t < 300:
                    r[y_offset: y_end, x_offset: x_end] = (255)
                x_offset = x_offset + tc_horz_scale
    
    
    
    
    
    y_offset = int(v_res*(y_offset_factor/2)) - y_axis
    x_offset = int(h_res*(x_offset_factor/2))
    

    fram = cv2.merge([b,g,r])
    
    
    for(a, b, c, d) in faces:
        cv2.rectangle(fram, (a,b), (a+c, b+d), (255,0,0),2)
        blend_images(a, b)
        if c*d > 30000*d_scale:
            fram = cv2.putText(fram, "1 foot", (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
        if 10000*d_scale < c*d <= 30000*d_scale:
            fram = cv2.putText(fram, "2 foot", (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
        if 4500*d_scale < c*d <= 10000*d_scale:
            fram = cv2.putText(fram, "3 foot", (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
        if 2000*d_scale < c*d <= 4500*d_scale:
            fram = cv2.putText(fram, "4 foot", (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
        if 1100*d_scale < c*d <= 2000*d_scale:
            fram = cv2.putText(fram, "5 foot", (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
    
    
    
    cv2.imshow('bckgrd2', bckgrd2)
    bckgrd2 = cv2.imread('800x600background.jpg')
    
        
    if cv2.waitKey(1) == ord('q'):
                   break

cap.release()
cv2.destroyAllWindows()
exit(0)