import main_functions as mf
import threading
import time
import cv2
import numpy as np
import math
from sklearn.linear_model import LinearRegression

debug = True
my_temp = 36.5

#basic font settings from openCV
font = cv2.FONT_HERSHEY_SIMPLEX
color = (0,255,0)
thickness = 1
fontScale = 0.6


face_cascade = cv2.CascadeClassifier('opencv_haarcascade_frontalface_alt.xml')




#video capture settings
cap = cv2.VideoCapture(0)
cap.set(3,mf.h_res)
cap.set(4,mf.v_res)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

#Possible Fever D(103,50) RGB(255,127,39)
#Move Closer D(94,19) RGB(0,0,255)
#Fever Free D(82,14) RGB(0,0,255)
#Too Close D(72,14) RGB(255,242,0)
#Possible Forehead Obstruction D(87,52) RGB(163,73,164)
#qCalculating D(101,18) RGB(127,127,127)
#Face Screen D(87,16) RGB(63,72,204)

img = cv2.imread("assets/800x480background.jpg")
img2 = cv2.imread("assets/800x480 owl on limb.jpg")
fever_message = cv2.imread("assets/Fever Message.jpg")
possible_fever = cv2.imread("assets/Possible Fever.jpg")
move_closer = cv2.imread("assets/Move Closer.jpg")
no_fever = cv2.imread("assets/Fever Free.jpg")
too_close = cv2.imread("assets/Too Close.jpg")
calculating = cv2.imread("assets/Calculating.jpg")
possible_forehead_obstruction = cv2.imread("assets/Possible Forehead Obstruction.jpg")
face_screen = cv2.imread("assets/Face Screen.jpg")
obstruction_message = cv2.imread("assets/obstruction message.jpg")
calibraton = cv2.imread("assets/calibraton.jpg")
graphic = cv2.imread("assets/graph_800x480.jpg")

#calibration and debug
if debug == True:
    string = "My temp 36.5"
    temp = my_temp
    cv2.putText(graphic, string, (100,35), font, fontScale, color, thickness, cv2.LINE_AA, False)
    cv2.line(graphic, (0,480 - int((temp-30)*50)), (800,480 - int((temp-30)*50)), (0,255,0), thickness)
    cv2.line(graphic, (0,480 - int((temp-29.5)*50)), (800,480 - int((temp-29.5)*50)), (255,0,255), thickness)
    cv2.line(graphic, (0,480 - int((temp-30.5)*50)), (800,480 - int((temp-30.5)*50)), (255,0,255), thickness)
    cv2.imshow('graph', graphic)

values = []
residuals = []
def_temps = []

#keeps track of faces
eyes = []
faces = []
people = []



def draw_stick_figure(bckgrd, top_right_corner , scale, thickness):
    #head
    x , y = top_right_corner
    #modified for banners and rectangle
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

def draw_coffee_cup(bckgrd, x, y, scale, thickness):
    #draws outline of coffee mug
    cv2.ellipse(bckgrd,(x,y),(int(15*scale),int(10*scale)),0,0,360,(0,0,0),thickness)
    cv2.ellipse(bckgrd,(x,y+int(23*scale)),(int(15*scale),int(10*scale)),0,0,360,(0,0,0),thickness)
    cv2.rectangle(bckgrd,(x-int(15*scale),y+int(3*scale)),(x+int(15*scale),y+int(26*scale)),(0,0,0),thickness)
    
    #fills in the above outlines with color
    cv2.rectangle(bckgrd,(x-int(15*scale),y+int(3*scale)),(x+int(15*scale),y+int(26*scale)),(255,236,221),-1)
    cv2.ellipse(bckgrd,(x,y),(int(15*scale),int(10*scale)),0,0,360,(0,64,96),-1)
    cv2.ellipse(bckgrd,(x,y+int(23*scale)),(int(15*scale),int(10*scale)),0,0,360,(255,236,221),-1)
    
    #Draws a handle
    handle = np.array([[x + int(15*scale), y + int(3*scale)], [x + int(22*scale), y + int(9*scale)], [ x + int(22*scale), y + int(17*scale)],
                       [x +int(15*scale), y + int(24*scale)]], np.int32)
    handle.reshape(-1,1,2)
    cv2.polylines(bckgrd, [handle], False, (0,0,0), thickness)
    
    


#Thermal camera function and thread - works in background continously


t_camera = threading.Thread(target = mf.refresh_thermalCamera, daemon = True )
t_camera.start()

    

while True:
    
    #changes background image - needs work
    if mf.frame_count == 300000:
         mf.frame_count = 0
    elif mf.frame_count%5000 == 0:
        bkrg = img2
    elif mf.frame_count%11000 == 0:
        bkrg = img

    ret, fram = cap.read()
    fram = cv2.flip(fram, 180)
    gray_p = cv2.cvtColor(fram, cv2.COLOR_BGR2GRAY)
    gray_p = cv2.equalizeHist(gray_p)
    gray_p = cv2.convertScaleAbs(gray_p, alpha = 1.25, beta = 0)
    

    faces = face_cascade.detectMultiScale(gray_p, 1.2, 2)


    if len(faces) > 0:
        mf.face_is_present = True      
                

    if debug == True:
        b, g, r = cv2.split(fram)
        r = mf.create_thermal_image( r )
        fram = cv2.merge([b,g,r])
        
    

    #def__init__(self, x_cor=0, y_cor= 0, lastx = 0, lasty = 0, ttl = 15, frams = 0, temp = 32.5)
    #update the faces list

    
    for (a, b, c, d) in faces:
        if debug == True:
            cv2.rectangle(fram, (a,b), (a+c, b+d), (255,0,0),2)
        
     
        distance = mf.distance(c)
        number_of_max_temps = int(mf.num_max_temps(distance))
        #print(number_of_max_temps)
        if mf.frame:
            temperatures = (mf.get_n_max_temps( (a,b), (a+c, b+d+mf.tc_vert_scale), number_of_max_temps))
            temperatures.insert(0,distance)
        else:
            temperatures = []
            mf.frame = []
        
        #stores value for maximum face temp - never below 35
        mf.max_face_temp = 35
        if len(temperatures) > 2:
            if temperatures[-1] > mf.max_face_temp:
                mf.max_face_temp = temperatures[-1]
                  #print("max_face_temp", mf.max_face_temp)
        
        if people:
            new_face = True
            for i in range(0,len(people)):
                #Checks if face Coordinates in updated faces array are close to any other previous face
                #if coordinates are close -> updates that face/person in people array; otherwise creates new person
                if a -18 < people[i].x < a + 18 and b-18 < people[i].y < b + 18:
                    new_face = False
                    #frames is a person attribute that cycles from 1 to 30 -> increments each frame
                    people[i].frames = people[i].frames + 1
                    people[i].sizes.append(c)  
                    if len(people[i].sizes) > 4:
                        people[i].sizes.pop(0)
                        
                        
                    people[i].distance = mf.distance(people[i].size)
                    
                    #print(number_of_max_temps)
                    #Every person has 15 frames before they are deleted, UNLESS, they are found and udpated
                    people[i].time_to_live = 15
                    
                    #if a peron is present for 10 frames and they have living ratio they will be drawn
                    if temperatures and people[i].frames > 10 and people[i].alive == False:
                        if temperatures[1] > 0 and temperatures[-1] > 32.5:
                            temperatures[2]/temperatures[1] > 0.15
                            people[i].alive = True
                    
                        
                    #For the coffee Detector
                    if people[i].coffee_ttl > 0:
                        people[i].coffee_ttl = people[i].coffee_ttl -1
                    else:
                        people[i].has_coffee = False
                        
                        
                    #temp of -1 = Too close; temp 0 = move closer; temp 1 = calculating; temp 2 = possible obstruction
                    if temperatures and people[i].frames%3 == 0 and people[i].def_temp < 35.0 and people[i].obstruction_count > 0:
                        #move retry incrementer 
                        if people[i].move_retry == 0 and (((a/32)/mf.d_scale) * ((b/24)/mf.d_scale)) <= 200: 
                            new_def_temp = 0
                        else:
                            people[i].move_retry = people[i].move_retry - 1
                            new_def_temp = 1
                        #motion between thermal camera frames - "face screen"
                        if not (a - mf.tc_horz_scale < people[i].last_therm_x < a + mf.tc_horz_scale and b - mf.tc_vert_scale < people[i].last_therm_y < b  + mf.tc_vert_scale):
                            new_def_temp = -2
                        people[i].last_therm_x = a
                        people[i].last_therm_y = b
                        #move towards face towards center of screen
                        if temperatures[1] == -1:
                            people[i].def_temp = -3
                        #needs at least  pixels to be considered for calculation
                        if temperatures[2] >= 1 and new_def_temp > -2:
                            #possible obstruction
                            if (temperatures[2]/temperatures[1] <= 0.15 and 200 < temperatures[1] <= 500 and people[i].obstruction_count > 0) or people[i].def_temp == 3:
                                new_def_temp = 2
                                people[i].obstruction_count = people[i].obstruction_count - 1
                            #calculating
                            elif temperatures[2]/temperatures[1] > 0.15 and temperatures[1] <= 500:
                                people[i].temps.append(temperatures)
                                people[i].total_temps = people[i].total_temps + len(temperatures) - 3
                                #print("person", i , "total", people[i].total_temps, "max", number_of_max_temps)
                                new_def_temp = 1
                                people[i].move_retry = 3
                            #too close
                        if temperatures[1] > 500:
                            new_def_temp = -1
                        #definitive temperature
                        if people[i].total_temps >= 16:
                            new_def_temp = mf.def_temp_calc(people[i].temps)
                            if debug == True:
                                people[i].w_distance = mf.weighted_average(people[i].temps, 0)
                                people[i].w_area = mf.weighted_average(people[i].temps,1 )
                                people[i].w_t_pixels = mf.weighted_average(people[i].temps,2 )
                            people[i].temps = []
                            people[i].total_temps = 0
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
                    if not people[i].size -2 < np.average(people[i].sizes) < people[i].size + 2:
                            people[i].size = int(np.average(people[i].sizes))
                    

            if new_face == True:
                people.append(mf.person(a,b,a,b,15,1,0,c,a,b))
                
        else:
            people.append(mf.person(a,b,a,b,15,1,0,c,a,b))
    
    #coffee detector code
    #Finds object that are not in a face, and are at least 2C hotter than
    #any other than the hottest face
    coffee = []
    if mf.face_is_present == True:
        for i in range(0,768):
            if mf.max_face_temp + 2 < mf.frame[i] < 45:
                coffee.append(mf.thermal_to_image((i%32,(i-i%32)/32)))
    #print("coffee_temps", coffee)
    real_coffee = []
    if coffee:
        real_coffee.append(coffee[0])
        a,b = coffee[0]
        a = int(a)
        b = int(b)
        #print("coffee a b", a, b)
        cv2.rectangle(fram, (a,b), (a+25,b+25), (0,255,0),2)
        for (x,y) in coffee:
            new_coffee = True
            for (a,b) in real_coffee:
                if a-30 < x < a+30 and b - 20 < y < b + 80:
                    new_coffee = False
            if new_coffee == True:
                real_coffee.append((x,y))
                x = int(x)
                y = int(y)
                #print("coffee a b", a, b)
                #print("coffee x y", x, y,)
                cv2.rectangle(fram, (x,y), (x+25,y+25), (0,255,0),2)
    
    if real_coffee:
        distance = 0
        person_num = 0
        for (x,y) in real_coffee:
            for j in range(0, len(people)):
                if people[j].y + people[j].size < y:
                    magnitude = (y - people[j].y + people[j].size)**2 + (people[j].x - x)**2
                    magnitude = magnitude**0.5
                    distance = magnitude
                    if distance > magnitude:
                        person_num = j   
            people[person_num].has_coffee = True
            people[person_num].coffee_ttl = 10
                
                
       
        
        

    #udpate people list/ deletes person when ttl is 0
    dead_faces = True
    while(dead_faces == True):
        for i in range(0,len(people)):
            if people[i].time_to_live <= 0:
                people.pop(i)
                dead_faces = True
                break
        dead_faces = False
            
    #obstruction message D(800,212)
    #fever message D(799,100)
    #Possible Fever D(103,50) RGB(255,127,39)
    #Move Closer D(94,19) RGB(0,0,255) code == 0
    #Fever Free D(82,14) RGB(0,255,0)
    #Too Close D(72,14) RGB(255,242,0) code == -1
    #Possible Forehead Obstruction D(87,52) RGB(163,73,164) code == 2
    #Calculating D(101,18) RGB(127,127,127) code == 1
    #Face Screen D(87,16) RGB(63,72,204) code == 3 - removed
    if people:
        mf.face_is_present = True
        for i in range(0,len(people)):
            people[i].time_to_live = people[i].time_to_live - 1
            if people[i].alive == True and mf.ambient > 0:
                a = people[i].last_x
                b = people[i].last_y
                bckgrd_coord = mf.fram_to_background((a,b))
                x, y = bckgrd_coord
                #inverts y placment on background image floorspace with room for stick figure
                #y = 580 - y
                #print(people[i].size)
                bckgrd_coord = x, y
                font = cv2.FONT_HERSHEY_SIMPLEX
                thickness = 2
                fontScale = 0.8
                bgr = (0,0,0)
                if people[i].def_temp <= -2:
                    color = (255,255,255)
                    bgr = (255,0,0)
                    string = "Face Screen"
                elif people[i].def_temp == -1:
                    color = (0,0,0)
                    bgr = (0,242,255)
                    string = "Too Close"
                elif people[i].def_temp == 0:
                    color = (255,255,255)
                    bgr = (255,0,0)
                    string = "Move Closer"
                elif people[i].def_temp == 1:
                    color = (255,255,255)
                    bgr = (127,127,127)
                    string = "Calculating"
                elif people[i].def_temp == 2 or people[i].def_temp == 3:
                    color = (255,255,255)
                    bgr = (164,73,163)
                    fontScale = 0.7
                    string = "Possible obstruction"
                    if people[i].obstruction_count == 0:
                        mf.obstruction_message_timer = 210
                elif mf.rel_temp < people[i].def_temp < 37.3:
                    color = (255,255,255)
                    bgr = (0,255,0)
                    string = "Fever Free"
                elif 37.2 < people[i].def_temp:
                    color = (0,0,0)
                    bgr = (39,127,255)
                    fontScale = 0.7
                    string = "Possible Fever"
                    mf.fever_message_timer = 210
                               
                
                #print(y)
                scale_factor = .5 + (people[i].size-40)/75
                length = len(string)*14 
                #print("scale_factor", scale_factor)
                cv2.rectangle(bkrg, (x,y-110), (x+80+int(35*(scale_factor)), y-40+int(35*(scale_factor))), bgr,2)
                cv2.rectangle(bkrg, (x,y-130), (x+length, y-107), bgr,-1)
                bkrg = cv2.putText(bkrg, string, (x,y-110), font, fontScale, (255,255,255), thickness, cv2.LINE_AA, False)
                if people[i].has_coffee == True:
                    draw_coffee_cup(bkrg, x+5, y-40+int(35*scale_factor) , 0.5 + scale_factor, 2)
                #if y - 110 - height < 480 and x + 103 < 800:
                    #try:
                       # bkrg[y-110-height:y-110,x:x+width] = banner
                    #except ValueError:
                        #continue
                
                #Draw animations
                if 40 <= people[i].size:
                    draw_stick_figure(bkrg, (x,y),(1+scale_factor), 2)
                elif people[i].size < 40:
                    draw_stick_figure(bkrg, (x,y),1.5 , 2)
                    

                if debug == True:
                    string = "Temp" + str(int(people[i].def_temp*10)/10)
                    mf.fram = cv2.putText(fram, string, (a, b), font, fontScale, color, thickness, cv2.LINE_AA, False)
                    
                    if people[i].def_temp > 30:
                        #print(people[i].def_temp)
                        x_cor = 25 + int(people[i].w_distance*3)
                        y_cor = 480 - int(((people[i].def_temp-30)*50))
                        cv2.circle(graphic, (x_cor,y_cor), 3, (0,0,255), -1)
                        cv2.imshow('graph', graphic)
                        
                        print("temp ",round(people[i].def_temp,1), "distance ", people[i].w_distance, "area ", people[i].w_area, "t_pixels ", people[i].w_t_pixels, "ratio ",people[i].w_t_pixels/people[i].w_area)
                        def_temps.append(people[i].def_temp)
                        values.append((people[i].w_distance, people[i].w_t_pixels/people[i].w_area))
                        residuals.append(my_temp - people[i].def_temp)
                        
                        people[i].def_temp = 0
                        people[i].temps = []
                        people[i].total_temps = 0      
    else:
        mf.face_is_present = False


    #Display Messages   
    if mf.fever_message_timer > 0:
        mf.fever_message_timer = mf.fever_message_timer - 1
        bkrg[380:480,0:799] = fever_message      
    elif mf.obstruction_message_timer > 0:
        mf.obstruction_message_timer = mf.obstruction_message_timer - 1
        bkrg[268:480,0:800] = obstruction_message
    
    if mf.ambient == 0:
        bkrg = calibraton
        
    if debug == True:
        cv2.imshow('bckgrd', bkrg)
        bkrg = cv2.imread("assets/800x480 owl on limb.jpg")  

        cv2.imshow('fram', fram)

    else:
        cv2.namedWindow("bckgrd",cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("bckgrd", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow('bckgrd', bkrg)
    bkrg = cv2.imread("assets/800x480 owl on limb.jpg")
    
     
    #Global Frame reset after a million frames
    if mf.frame_count == 1000000:
         mf.frame_count = 0
    else:
        mf.frame_count = mf.frame_count + 1
    
    
    
    if cv2.waitKey(1) == ord('q'):
        break


if debug == True:
    x = np.array(values)
    y = np.array(residuals)
    reg = LinearRegression().fit(x,y)
    print("r^2 = ", reg.score(x,y))
    print("coeffecients", reg.coef_)
    print("y-intercept", reg.intercept_)
    temp_y = reg.coef_[0]
    ratio_y =  reg.coef_[1]
    y_intercept = reg.intercept_
    for i in range(0,len(values)):
        y = 480 - int((def_temps[i] + temp_y*values[i][0] + ratio_y*values[i][1] - 30 + y_intercept)*50)
        if my_temp - y > .5:
            print("480 - ", def_temps[i], " + ", temp_y, "*",values[i][0], " + ", ratio_y, "*", values[i][1])
        x = 25 + int(values[i][0]*3)
        cv2.circle(graphic, (x,y), 3, (255,0,0), -1)
        temp_y = round(temp_y,4)
        ratio_y = round(ratio_y,4)
        y_intercept = round(y_intercept,4)
    string = "def_temp = raw_temp + distance*" + str(temp_y) + " + ratio*" + str(ratio_y) + " + " + str(y_intercept)  
    cv2.putText(graphic, string, (100,70), font, 0.5, (0,0,0), 1, cv2.LINE_AA, False)
    cv2.imwrite('data/regression_graph.jpg', graphic)
    cv2.imshow('graph', graphic)
    cv2.waitKey(0)
    
                

cap.release()
cv2.destroyAllWindows()

exit(0)

