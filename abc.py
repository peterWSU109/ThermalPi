import threading
import numpy as np
import time
import board
import busio
import adafruit_mlx90640
import cv2
#Touch Screen display is 800x480
count = 0


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



i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

face_cascade = cv2.CascadeClassifier('opencv_haarcascade_frontalface_alt.xml')

img = cv2.imread("800x480background.jpg")
fever = cv2.imread("Possible fever.jpg")
closer = cv2.imread("Move Closer.jpg")
no_fever = cv2.imread("Fever Free.jpg")


frame = [0] * 768
people = []
person_serial = 0

def draw_stick_figure(bckgrd, top_right_corner , scale, thickness):
    #head
    x , y = top_right_corner
    x = int(x + 15)
    y = int(y + 15)
    y = y - 115 # funtion will draw stick figure from bottom right corner -- comment out for top right

    cv2.circle(bckgrd, (x + int(20*scale), y + int(20*scale)), int(15*scale), (0,255,255), -1)
    cv2.circle(bckgrd, (x + int(20*scale), y + int(20*scale)), int(15*scale), (0,0,0), thickness)
    #eyes
    cv2.line(bckgrd, (x + int(15*scale), y + int(13*scale)), (x + int(15*scale), y + int(20*scale)), (0,0,0), thickness)
    cv2.line(bckgrd, (x + int(25*scale), y + int(13*scale)), (x + int(25*scale), y + int(20*scale)), (0,0,0), thickness)
    #mouth
    mouth = np.array([[x + int(11*scale), y + int(22*scale)], [x + int(17*scale), y + int(27*scale)], [ x + int(23*scale), y + int(27*scale)], [x +int(29*scale), y + int(22*scale)]], np.int32)
    mouth.reshape(-1,1,2)
    cv2.polylines(bckgrd, [mouth], False, (0,0,0), thickness)
    #torso
    cv2.line(bckgrd, (x + int(20*scale), y + int(35*scale)), (x + int(20*scale), y + int(95*scale)), (0,0,0), thickness)
    #arms
    cv2.line(bckgrd, (x + int(5*scale), y + int(65*scale)), (x + int(35*scale), y + int(65*scale)), (0,0,0), thickness)
    
    #legs
    cv2.line(bckgrd, (x + int(20*scale), y + int(95*scale)), (x + int(5*scale), y + int(110*scale)), (0,0,0), thickness)
    cv2.line(bckgrd, (x + int(20*scale), y + int(95*scale)), (x + int(35*scale), y + int(110*scale)), (0,0,0), thickness)

#floor of background
# lower x range from 0 to 800 but 0 to 500 at y = 210
# y range = 210 to 480
#y_transform = ((top_right_y/v_res)*270) + 210
#stick figure is 115 pixels tall at one scale
#x coordinate transform  x_adjust = (top_right_x/h_res)*(500 + (y_transform-210/270)*300) for strgith to 800x480
#above will get us 'squeezed' but still need x_offset
#x_transform = x_adjust - 150*(y_transform - 480/270)
#y_transform - 115

def fram_to_background( top_right_corner ):
    top_right_x, top_right_y = top_right_corner
    y_transform = ((top_right_y/v_res)*270) + 210
    pos_y_slope = ((y_transform - 210)/270) # y 0 to positive 1 as y increases
    neg_y_slope = ((y_transform - 480)/270) # y -1 to 0 as y increases
    
    x_transform = (top_right_x/h_res)*500 + (pos_y_slope*300) - 150 * (neg_y_slope)
    
    x_transform = int(x_transform)
    y_transform = int(y_transform)
    return ([x_transform, y_transform])
    
    


def cel_to_far( t ):
    t = ((t*9)/5)+32
    return t

def temp_corr ( t , a, farenheight):
    a = a/d_scale
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
    
    return t
    

class person:
    def __init__(self, x_cor=0, y_cor= 0, lastx = 0, lasty = 0, ttl = 15, frams = 0, t = 32.5):
        self.x = x_cor
        self.y = y_cor
        self.time_to_live = ttl
        self.temps = []
        self.frames = frams
        self.def_temp = t
        self.alive = False
        self.last_x = lastx
        self.last_y = lasty
        
    def print_stuff():
        print("x_cor", x)
        print("y_cor", y)
        print("frames", frames)
        


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
                    r[y_offset: y_end, x_offset: x_end] = (40)
                elif 31 <= t < 32:
                    r[y_offset: y_end, x_offset: x_end] = (80)
                elif 32 <= t < 33:
                    r[y_offset: y_end, x_offset: x_end] = (120)
                elif 33 <= t < 34:
                    r[y_offset: y_end, x_offset: x_end] = (160)
                elif 34 <= t < 35:
                    r[y_offset: y_end, x_offset: x_end] = (200)
                elif 35 <= t < 300:
                    r[y_offset: y_end, x_offset: x_end] = (255)
                x_offset = x_offset + tc_horz_scale
    
    
    
    y_offset = int(v_res*(y_offset_factor/2)) - y_axis
    x_offset = int(h_res*(x_offset_factor/2))
    

    fram = cv2.merge([b,g,r])
    
    number_of_max_temps = 3
    total_temps = 0
    

     #def__init__(self, x_cor=0, y_cor= 0, lastx = 0, lasty = 0, ttl = 15, frams = 0, temp = 32.5)
    
    #update the faces list
    for(a, b, c, d) in faces:

        cv2.rectangle(fram, (a,b), (a+c, b+d), (255,0,0),2)
        temperatures = (get_n_max_temps( (a,b-tc_vert_scale), (a+c, b+0.5*d), number_of_max_temps))
        
        if people:
            new_face = True
            for i in range(0,len(people)): 
                if a -18 < people[i].x < a + 18 and b-18 < people[i].y < b + 18:
                    new_face = False
                    people[i].frames = people[i].frames + 1
                    people[i].time_to_live = 15
                    if not (a -3 < people[i].x < a + 3 and b-3 < people[i].y < b + 3):
                        #print(people[i].x - a, people[i].y - b)
                        people[i].last_x = a
                        people[i].last_y = b
                    people[i].x = a
                    people[i].y = b
                    people[i].def_temp = 32.6
                    people[i].temps.append(temperatures)
                    if people[i].frames > 5:
                        people[i].alive = True
            if new_face == True:
                people.append(person(a,b,a,b,15,1,32.6))
                    
        else:
            people.append(person(a,b,a,b,15,1,32.6))
                
                


    #udpate people list
    for i in range(0, len(people)):
        if people[i].time_to_live <= 0:
            people.pop(i)
            break
            

    
    if people:
        for i in range(0,len(people)):
            people[i].time_to_live = people[i].time_to_live - 1
            if people[i].def_temp > 32.5 and people[i].alive == True:
                a = people[i].last_x
                b = people[i].last_y
                bckgrd_coord = fram_to_background((a,b))
                x, y = bckgrd_coord
                #print("actual", people[i].x, people[i].y)
                #print(x, y)
                cv2.rectangle(img, (x+10,y-110), (x+60, y+15), (0,255,0),2)
                img[y-123:y-100,x:x+150] = no_fever
                draw_stick_figure(img, bckgrd_coord, 1, 2)


            #else:
                #string = "Move Closer"
                #cv2.rectangle(img, (x+10,y-110), (x+60, y+15), (255,0,0),2)
                #img[y-123:y-100,x:x+150] = closer
                #fram = cv2.putText(fram, string, (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
               
            

    
    
    cv2.imshow('bckgrd', img)
    cv2.imshow('fram', fram)
    img = cv2.imread("800x480background.jpg")

    
        
    if cv2.waitKey(1) == ord('q'):
                   break

cap.release()
cv2.destroyAllWindows()
exit(0)
