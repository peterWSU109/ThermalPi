
import threading
import math
import numpy as np
import time
import board
import busio
import adafruit_mlx90640
import cv2
#Touch Screen display is 800x480
frame_count = 0
seconds = 0
rel_temp = 31



debug = True

h_res = 320 #320,640,1024
v_res = 240 #240,480,768


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

#basic font settings from openCV
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

#Possible Fever D(103,50) RGB(255,127,39)
#Move Closer D(94,19) RGB(0,0,255)
#Fever Free D(82,14) RGB(0,0,255)
#Too Close D(72,14) RGB(255,242,0)
#Possible Forehead Obstruction D(87,52) RGB(163,73,164)
#Calculating D(101,18) RGB(127,127,127)
#Face Screen D(87,16) RGB(63,72,204)

img = cv2.imread("800x480background.jpg")
img2 = cv2.imread("800x480 owl on limb.jpg")
fever_message = cv2.imread("Fever Message.jpg")
possible_fever = cv2.imread("Possible fever.jpg")
move_closer = cv2.imread("Move Closer.jpg")
no_fever = cv2.imread("Fever Free.jpg")
too_close = cv2.imread("Too Close.jpg")
calculating = cv2.imread("Calculating.jpg")
possible_forehead_obstruction = cv2.imread("Possible Forehead Obstruction.jpg")
face_screen = cv2.imread("Face Screen.jpg")


frame = [0] * 768
people = []


def draw_stick_figure(bckgrd, top_right_corner , scale, thickness):
    #head
    x , y = top_right_corner
    x = int(x + 15)
    y = int(y + 15)
    y = y - 115 # funtion will draw stick figure from bottom right corner 
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

def gather_data( temps):
    area_ratio = 0
    average_temp = 0
    average_area_ratio = 0
    average_average_temp = 0
    average_area = 0
    
    
    
    for i in range(0, len(temps)):
        #print(temps[i])
        area_ratio = ((temps[i][1])**0.5)/((temps[i][0])**0.5)
        average_area_ratio = average_area_ratio + area_ratio
        average_area = average_area + temps[i][0]
        #print(temps[i][2])
        #print(temps[i][0], temps[i][1])
        for j in range(2,len(temps[i])):
            average_temp = average_temp + temps[i][j]
        average_temp = average_temp/((len(temps[i]))-2)
        average_average_temp = average_average_temp + average_temp
        #print(temps[i][0],"area_ratio ", area_ratio, " average temp ", average_temp)
        average_temp = 0
    average_average_temp = average_average_temp/len(temps)
    average_area_ratio = average_area_ratio/len(temps)
    average_area = average_area/len(temps)
    print("ave area ", average_area, " ave ratio ", average_area_ratio, "ave temp ", average_average_temp, "frame", max(frame),"\n\n")
   
                
def def_temp_calc( temps ):
    ratio = 0
    area = 0
    def_temp = 0
    
    if len(temps) > 0:
        for i in range(0, len(temps)):
            correction = 0
            temp = 0
            temp_x = 0

            #print("area",temps[i][0],"t_pixels", temps[i][1] ,"ratio", temps[i][1]/temps[i][0],end = "")
            for j in range(2,len(temps[i])):
                #print(" temps ",temps[i][j], end = "")
                temp = temp + temps[i][j]
            temp = temp/((len(temps[i]))-2)
            if temps[i][1] <= 100:
                temp_x = 1 - math.sqrt(temps[i][1])/19
            elif 100 < temps[i][1]<= 160:
                temp_x = 1 - math.sqrt(temps[i][1])/13.5
            elif 160 < temps[i][1]<= 225:
                temp_x = 1 - math.sqrt(temps[i][1])/15.5
            elif 225 < temps[i][1] <= 275:
                temp_x = 1 - math.sqrt(temps[i][1])/17
            elif 275 < temps[i][1] <= 325:
                temp_x = 1 - math.sqrt(temps[i][1])/19
            elif 325 < temps[i][1] <= 375:
                temp_x = 1 - math.sqrt(temps[i][1])/21

            correction = 1.6 + ((3*temp_x) - 1.25)**3
            
             
            #print("  correction ", correction, " def_temp", temp + correction, "max", max(frame))
            def_temp = def_temp + temp + correction
    else:
        return 32.5
              

    def_temp = def_temp/len(temps)
    #print("def_temp", def_temp, "\n")
    

    return def_temp
        
                                    
    
    
            
    

class person:
    def __init__(self, x_cor=0, y_cor= 0, lastx = 0, lasty = 0, ttl = 15, frams = 0, t = 0):
        self.x = x_cor
        self.y = y_cor
        self.time_to_live = ttl
        self.temps = []
        self.frames = frams
        self.def_temp = t
        self.alive = False
        self.last_x = lastx
        self.last_y = lasty
        self.move_retry = 0
        
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
    num_rel_temps = 0
    if(leng_temps < 30):
        n = 1
    count = n
    
    if n < leng_temps:
        max_temps = []
        for i in range(0,leng_temps):
            if temps[i] > rel_temp and count > 0:
                max_temps.append(temps[i])
                count = count - 1
        
        if not max_temps:
            max_temps.append(0)
            
        max_temps.sort()
        for i in range(0,leng_temps):
            if temps[i] > rel_temp:
                num_rel_temps = num_rel_temps + 1
                if temps[i] > max_temps[0]:
                    max_temps[0] = temps[i]
                    max_temps.sort()
        
        max_temps.sort()
        max_temps.insert(0,num_rel_temps)
        max_temps.insert(0,leng_temps)
        return max_temps
    else:
        temps.insert(0,num_rel_temps)
        temps.insert(0,leng_temps)
        return temps
            
        
        



        
    

def refresh_thermalCamera():
    while True:
        try:
            mlx.getFrame(frame)
        except ValueError:
            continue

t_camera = threading.Thread(target = refresh_thermalCamera, daemon = True )
t_camera.start()
    

while True:
    
    if frame_count == 300000:
         frame_count = 0
    elif frame_count%5000 == 0:
        bkrg = img2
    elif frame_count%11000 == 0:
        bkrg = img


    
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
                elif 32 <= t < 32.5:
                    r[y_offset: y_end, x_offset: x_end] = (0)
                elif 32.5 <= t < 34:
                    r[y_offset: y_end, x_offset: x_end] = (160)
                elif 34 <= t < 35:
                    r[y_offset: y_end, x_offset: x_end] = (200)
                elif 35 <= t < 300:
                    r[y_offset: y_end, x_offset: x_end] = (255)
                x_offset = x_offset + tc_horz_scale
    
    
    
    y_offset = int(v_res*(y_offset_factor/2)) - y_axis
    x_offset = int(h_res*(x_offset_factor/2))
    

    fram = cv2.merge([b,g,r])
    
    number_of_max_temps = 4
    total_temps = 0
    

     #def__init__(self, x_cor=0, y_cor= 0, lastx = 0, lasty = 0, ttl = 15, frams = 0, temp = 32.5)
    
    #update the faces list
    for(a, b, c, d) in faces:
        if debug == True:
            cv2.rectangle(fram, (a,b), (a+c, b+d), (255,0,0),2)
            temperatures = (get_n_max_temps( (a,b-tc_vert_scale), (a+c, b+d+tc_vert_scale), number_of_max_temps))
        
        if people:
            new_face = True
            for i in range(0,len(people)):
                #Checks if face Coordinates in updated faces array are close to any other previous face
                #if coordinates are close -> updates that face/person in people array; otherwise creates new person
                if a -18 < people[i].x < a + 18 and b-18 < people[i].y < b + 18:
                    new_face = False
                    #frames is a person attribute that cycles from 1 to 30 -> increments each frame
                    people[i].frames = people[i].frames + 1
                    #Every person has 15 frames before they are deleted, UNLESS, they are found and udpated
                    people[i].time_to_live = 15
                    
                    #if a peron is present for 16 frames they will be drawn
                    if people[i].frames > 15 and people[i].alive == False:
                        people[i].alive = True
                    #temp of -1 = Too close; temp 0 = move closer; temp 1 = calculating; temp 2 possible obustruction
                    if people[i].frames%3 == 0 and people[i].def_temp < 35:
                        if people[i].move_retry == 0 and (((a/32)/d_scale) * ((b/24)/d_scale)) < 150: 
                            new_def_temp = 0
                        elif people[i].move_retry == 0 and (((a/32)/d_scale) * ((b/24)/d_scale)) > 150:
                            new_def_temp = 3
                        else:
                            people[i].move_retry = people[i].move_retry - 1
                            new_def_temp = 1
                        
                        #move closer
                        if temperatures[0] != 0 and temperatures[1] > 20:
                            #possible obstruction
                            if temperatures[1]/temperatures[0] < 0.45 and temperatures[0] > 300:
                                new_def_temp = 2
                            #calculating
                            elif temperatures[1]/temperatures[0] > 0.40 and temperatures[0] < 450:
                                people[i].temps.append(temperatures)
                                new_def_temp = 1
                                people[i].move_retry = 3
                                if len(people[i].temps) > 10:
                                    people[i].temps.pop(0)
                            #too close
                            elif temperatures[0] > 425:
                                new_def_temp = -1
                        #face screen
                            elif not (a -6 < people[i].x < a + 6 and b-6 < people[i].y < b + 6) and new_def_temp == 0:
                                new_def_temp = 3
                            
                        #definitive temperature
                        if len(people[i].temps) == 10:
                            new_def_temp = def_temp_calc(people[i].temps)   
                        people[i].def_temp = new_def_temp
                        #reset frame
                        if people[i].frames == 30:
                            people[i].frames = 0
                        
                    #This reduces jitter, Last_x and Last_y will be used to draw the stick figure but are only
                    #udpated if x, y, of person has changed significantly
                    if not (a -3 < people[i].x < a + 3 and b-3 < people[i].y < b + 3):
                        people[i].last_x = a
                        people[i].last_y = b
                    people[i].x = a
                    people[i].y = b
                        

            if new_face == True:
                people.append(person(a,b,a,b,15,1,0))
                    
        else:
            people.append(person(a,b,a,b,15,1,0))
                
                


    #udpate people list/ deletes person when ttl is 0
    dead_faces = True
    while(dead_faces == True):
        for i in range(0, len(people)):
            if people[i].time_to_live <= 0:
                people.pop(i)
                dead_faces = True
                break
        dead_faces = False
            

    
    
    
    #Possible Fever D(103,50) RGB(255,127,39)
    #Move Closer D(94,19) RGB(0,0,255) code == 0
    #Fever Free D(82,14) RGB(0,255,0)
    #Too Close D(72,14) RGB(255,242,0) code == -1
    #Possible Forehead Obstruction D(87,52) RGB(163,73,164) code == 2
    #Calculating D(101,18) RGB(127,127,127) code == 1
    #Face Screen D(87,16) RGB(63,72,204) code == 3
    if people:
        for i in range(0,len(people)):
            people[i].time_to_live = people[i].time_to_live - 1
            if people[i].alive == True:
                a = people[i].last_x
                b = people[i].last_y
                bckgrd_coord = fram_to_background((a,b))
                x, y = bckgrd_coord
                bgr = (0,0,0)
                width = 0
                height = 0
                
                if people[i].def_temp == -1:
                    bgr = (0,242,255)
                    width = 72
                    height = 14
                    banner = too_close
                elif people[i].def_temp == 0:
                    bgr = (255,0,0)
                    width = 94
                    height = 19
                    banner = move_closer
                elif people[i].def_temp == 1:
                    bgr = (127,127,127)
                    width = 101
                    height = 18
                    banner = calculating
                elif people[i].def_temp == 2:
                    bgr = (164,73,163)
                    width = 87
                    height = 52
                    banner = possible_forehead_obstruction
                elif people[i].def_temp == 3:
                    bgr = (204,72,63)
                    width = 87
                    height = 16
                    banner = face_screen
                elif rel_temp < people[i].def_temp < 37.5:
                    bgr = (0,255,0)
                    width = 82
                    height = 14
                    banner = no_fever
                elif 37.4 < people[i].def_temp:
                    bgr = (255,127,39)
                    width = 103
                    height = 50
                    banner = possible_fever
                
                cv2.rectangle(bkrg, (x+10,y-110), (x+113, y+15), bgr,2)
                if y - 110 + height < 480 and x + 103 < 800:
                    bkrg[y-110:y-110+height,x+10:x+width+10] = banner
                draw_stick_figure(bkrg, bckgrd_coord, 1, 2)
                
                if debug == True:
                    string = "Temp" + str(int(people[i].def_temp*10)/10)
                    fram = cv2.putText(fram, string, (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
            





               
            

    
    
    cv2.imshow('bckgrd', bkrg)
    cv2.imshow('fram', fram)
    bkrg = cv2.imread("800x480 owl on limb.jpg")

    if frame_count == 300000:
         frame_count = 0
    else:
        frame_count = frame_count + 1
    if cv2.waitKey(1) == ord('q'):
                   break
                
                

cap.release()
cv2.destroyAllWindows()
exit(0)

