import threading
import numpy
import time
import board
import busio
import adafruit_mlx90640
import cv2

count = 0


debug = True

h_res = 640 #320,640,1280
v_res = 480 #240,480,720

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



i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

face_cascade = cv2.CascadeClassifier('opencv_haarcascade_frontalface_alt.xml')


frame = [0] * 768

def cel_to_far( t ):
    t = ((t*9)/5)+32
    return t

def temp_corr ( t , a, farenheight):
    a = a/d_scale
    print(a)
    #per 100 pixel area
    one_to_two = 0.002025
    two_to_three = 0.01118
    three_to_four =0.0208
    #per 10 pixel area
    four_to_five = 0.00836
    
    
    
    
    if a > 30000:
        t = t + 0.92
    if 10000 < a <= 30000:
        t = t + ((30000 - a)/100)*one_to_two + 0.92
    if 4500 < a <= 10000:
        t = t + ((10000 - a)/100)*two_to_three + 1.325
    if 2000 < a <= 4500:
        t = t + ((4500 - a)/100)*three_to_four + 1.94
    if 600 < a <= 2000:
        t = t + ((600 - a)/10)*four_to_five + 2.46
    
    if farenheight == True:
        t = ((t*9)/5)+32
    
    t = int(t*10)
    t = t/10  
    string = "Temp " + str(t)
    
    return string
        
        
    
        


def thermal_to_image( t_pixel ):
    x, y = t_pixel
    x = (x*tc_horz_scale) + x_offset
    y = (y*tc_vert_scale) + y_offset
    return[x,y]


def image_to_thermal( i_pixel):
    x, y = i_pixel
    x = (x - x_offset)/tc_horz_scale
    y = (y - y_offset)/tc_vert_scale
    return [x,y]

def get_temps( top_left , bottom_right):
    temps = []
    top_left = image_to_thermal(top_left)
    bottom_right = image_to_thermal(bottom_right)
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
    return temps

def get_n_max_temps( top_left , bottom_right, n):
    temps = get_temps(top_left , bottom_right)
    leng_temps = len(temps)
    count = n
    
    if n < leng_temps:
        max_temps = []
        for i in range(0,leng_temps):
            if temps[i] > 32 and count > 0:
                max_temps.append(temps[i])
                count = count - 1
        
        
        
        if not max_temps:
            max_temps.append(0)
            
        max_temps.sort()
        for n in range(n,leng_temps):
            if temps[n] > max_temps[0] and temps[n] > 32:      
                max_temps[0] = temps[n]
                max_temps.sort()
        
        max_temps.sort()
        max_temps.append(leng_temps)
        return max_temps
    else:
        return temps
            
        
        



        
    

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
    
    count = count + 1
    
    
    
    y_offset = int(v_res*(y_offset_factor/2)) - y_axis
    x_offset = int(h_res*(x_offset_factor/2))
    

    fram = cv2.merge([b,g,r])
    
    number_of_max_temps = 3
    total_temps = 0
    

    
    for(a, b, c, d) in faces:
        cv2.rectangle(fram, (a,b), (a+c, b+d), (255,0,0),2)
        temperatures = (get_n_max_temps( (a,b-tc_vert_scale), (a+c, b+0.75*d), number_of_max_temps))
        print(temperatures)
        box_area = c*d
        ti = 0
        
        if  len(temperatures) == (number_of_max_temps + 1) and box_area > 600*d_scale:
            for i in range(0,number_of_max_temps):
                ti = ti + temperatures[i]
            
            ti = ti/number_of_max_temps
            print(cel_to_far(ti))
            string = temp_corr( ti, box_area, True)
            print(string)
        else:
            string = "Move Closer"
        
        fram = cv2.putText(fram, string, (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
               
            

    
    
    cv2.imshow('fram', fram)

    
        
    if cv2.waitKey(1) == ord('q'):
                   break

cap.release()
cv2.destroyAllWindows()
exit(0)
